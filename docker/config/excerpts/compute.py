"""
Contains the tools required to perform a pipeline computation.  The main object
is Computation, which takes a runner and subject and runs them against each
other

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import os
import sys
import signal
import subprocess
import shutil
import json
import traceback
import time
from contextlib import contextmanager

import kim_edn
import kim_property

import pty
import select
import errno

from . import util
from . import kimunits
from . import kimobjects
from . import config as cf


def job_id(runner, subject):
    """Format a runner and subject into a Test Result ID"""
    return "{}-and-{}-{}".format(
        runner.kim_code_id, subject.kim_code_id, str(int(time.time()))
    )


# ================================================================
# a class to be able to timeout on a command
# ================================================================
class Command:
    """
    A class to run subprocesses and be able to flush their stdout/stderr to the
    terminal in real-time.  Also properly handles the case where the process is
    killed by a KeyboardInterrupt.
    """

    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, verbose=False):
        """
        Accepts a command as an array (similar to check_output) and file handles
        with which to communicate on stdin, stdout, stderr
        """
        self.cmd = cmd
        self.process = None
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.verbose = verbose
        self.this_worker = "@".join(("worker", cf.UUID))  # pylint: disable=E1101

    def run(self):
        """
        Run the command. For the user stack, we do not impose a timeout.
        We are grateful to Tobias Brink for the code used for handling the
        verbose output case (where the stdout and stderr of the job is printed
        to the terminal while simultaneously being written to pipeline.stdout
        and pipeline.stderr); this code was taken from the following blog
        (accessed 2019-03-21):

          http://tbrink.science/blog/2017/04/30/processing-the-output-of-a-subprocess-with-python-in-realtime/

        and is explicitly licensed there under CC0 (public domain),
        <http://creativecommons.org/publicdomain/zero/1.0/>.
        """

        class OutStream:
            def __init__(self, fileno):
                self._fileno = fileno
                self._buffer = b""

            def read_lines(self):
                try:
                    output = os.read(self._fileno, 1000)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    output = b""
                lines = output.split(b"\n")
                lines[0] = self._buffer + lines[0]  # prepend previous
                # non-finished line.
                if output:
                    self._buffer = lines[-1]
                    finished_lines = lines[:-1]
                    readable = True
                else:
                    self._buffer = b""
                    if len(lines) == 1 and not lines[0]:
                        # We did not have buffer left, so no output at all.
                        lines = []
                    finished_lines = lines
                    readable = False
                finished_lines = [
                    line.rstrip(b"\r").decode() + "\n" for line in finished_lines
                ]
                return finished_lines, readable

            def fileno(self):
                return self._fileno

        # Spawn subprocess in its own session. This means that the actual job
        # and all of the threads that it spawns will share a process group ID
        # which differs from that of the Cworker process. When we want to abort
        # a task, we just kill the entire (newly generated) process group.
        if self.verbose:
            out_r, out_w = pty.openpty()
            err_r, err_w = pty.openpty()

            self.process = subprocess.Popen(
                self.cmd,
                stdin=self.stdin,
                stdout=out_w,
                stderr=err_w,
                shell=True,
                start_new_session=True,
            )
            os.close(out_w)
            os.close(err_w)

            # Define a cache for determining whether the file descriptor
            # marked as ready is for stdout or stderr
            output_stdout = OutStream(out_r)
            output_stderr = OutStream(err_r)

            file_descriptors = {output_stdout, output_stderr}
            while file_descriptors:
                # Call select(), anticipating interruption by signals.
                while True:
                    rlist, _, _ = select.select(file_descriptors, [], [])
                    break
                # Handle all file descriptors that are ready
                for file_desc in rlist:
                    lines, readable = file_desc.read_lines()
                    if file_desc == output_stdout:
                        for line in lines:
                            sys.stdout.write(line)
                            self.stdout.write(line)
                    elif file_desc == output_stderr:
                        for line in lines:
                            sys.stderr.write(line)
                            self.stderr.write(line)

                    if not readable:
                        # This OutStream is finished
                        os.close(file_desc.fileno())
                        file_descriptors.remove(file_desc)

        else:
            self.process = subprocess.Popen(
                self.cmd,
                stdin=self.stdin,
                stdout=self.stdout,
                stderr=self.stderr,
                shell=True,
                start_new_session=True,
                encoding="utf-8",
            )

        self.process.communicate()

        return self.process.returncode

    def terminate(self):
        """Send a SIGTERM to the job. This occurs when a revoke request has
        been sent for this job"""
        pid = self.process.pid
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        raise cf.PipelineAbort


# ================================================================
# the actual computation class
# ================================================================
class Computation:
    def __init__(
        self,
        runner=None,
        subject=None,
        result_code="",
        verbose=False,
        verify=True,
    ):
        """
        A pipeline computation object that utilizes all of the pipeline
        machinery to calculate a result (test or verification or otherwise).

        Parameters:
            * runner : A Test or Verification Check object
            * subject : A Model
            * result_code : if provided, the result will be moved
                to the appropriate location
            * verify : If True, the contents of results.edn will be verified to contain
                valid KIM property instances when the output of the computation is
                processed. 
        """
        self.runner = runner
        self.subject = subject
        self.runner_temp = runner
        self.runtime = -1
        self.result_code = result_code
        self.verbose = verbose
        self.verify = verify
        self.info_dict = None
        self.uuid = None
        self.retcode = None

        self.result_type = ""
        self.result_path = ""
        self.full_result_path = ""

    def _create_tempdir(self):
        """Create a temporary running directory and copy over the test contents"""
        worker_running_path = cf.WORKER_RUNNING_PATH  # pylint: disable=E1101
        if not os.path.exists(worker_running_path):
            os.makedirs(worker_running_path)

        tdir = "{name}_running{result_code}__{id}".format(
            name=self.runner.kim_code_name,
            result_code=self.result_code,
            id=self.runner.kim_code_id,
        )
        tempname = os.path.join(cf.WORKER_RUNNING_PATH, tdir)  # pylint: disable=E1101
        self.runner_temp = kimobjects.kim_obj(self.runner.kim_code, abspath=tempname)
        shutil.copytree(self.runner.path, self.runner_temp.path)

    def _create_output_dir(self):
        """Make sure that the ``output`` directory exists for results"""
        outputdir = os.path.join(
            self.runner_temp.path, cf.OUTPUT_DIR  # pylint: disable=E1101
        )
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)

    @staticmethod
    def _clean_old_run():
        """Delete old temporary files if they exist"""
        for flname in cf.INTERMEDIATE_FILES:  # pylint: disable=E1101
            try:
                os.remove(os.path.join(cf.OUTPUT_DIR, flname))  # pylint: disable=E1101
            except OSError:
                pass

    def _delete_tempdir(self):
        shutil.rmtree(self.runner_temp.path)

    @contextmanager
    def tempdir(self):
        """
        Create a temporary directory and copy all objects over so that
        they can run independently of other processes on a single machine.

        A context manager so that you can say:

            with self.tempdir():
                ... do something ...
        """
        if self.result_code:
            self._create_tempdir()

            cwd = os.getcwd()
            os.chdir(self.runner_temp.path)

        try:
            self._create_output_dir()
            self._clean_old_run()
            yield
        except Exception as exc:
            raise exc
        finally:
            if self.result_code:
                os.chdir(cwd)
                self._delete_tempdir()

    def execute_in_place(self):
        """
        Execute the runner with the subject as set in the object.  Do this in
        the current directory, wherever that may be.  In the process, also
        collect runtime information using /usr/bin/time profilling
        """
        executable = self.runner_temp.executable
        libc_redirect = "LIBC_FATAL_STDERR_=1 "
        timeblock = (
            r"/usr/bin/time --format={\"usertime\":%U,\"memmax\":%M,\"memavg\":%K} "
        )

        _stdout_file = os.path.join(
            cf.OUTPUT_DIR, cf.STDOUT_FILE  # pylint: disable=E1101
        )
        _stderr_file = os.path.join(
            cf.OUTPUT_DIR, cf.STDERR_FILE  # pylint: disable=E1101
        )
        _kimlog_file = os.path.join(
            cf.OUTPUT_DIR, cf.KIMLOG_FILE  # pylint: disable=E1101
        )

        # run the runner in its own directory
        with self.runner_temp.in_dir():
            with self.runner_temp.processed_infile(self.subject) as stdin_file, open(
                _stdout_file, "w", encoding="utf-8"
            ) as stdout_file, open(_stderr_file, "w", encoding="utf-8") as stderr_file:
                start_time = time.time()

                process = Command(
                    libc_redirect + timeblock + executable,
                    stdin=stdin_file,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    verbose=self.verbose,
                )

                try:
                    self.retcode = process.run()
                except KeyboardInterrupt:
                    end_time = time.time()
                    self.runtime = end_time - start_time
                    # Attempt to copy kim.log over to output dir
                    with self.runner_temp.in_dir():
                        if os.path.exists("./kim.log"):
                            shutil.copy2("./kim.log", _kimlog_file)
                    process.terminate()

                end_time = time.time()

        self.runtime = end_time - start_time

        # Attempt to copy kim.log over to output dir, even if we errored out
        with self.runner_temp.in_dir():
            if os.path.exists("./kim.log"):
                shutil.copy2("./kim.log", _kimlog_file)

        if self.retcode != 0:
            raise cf.KIMRuntimeError(
                "Executable {} returned error code "
                "{}".format(self.runner_temp, self.retcode)
            )

    def process_output(self):
        """
        In the current directory, make sure that the results are ready to
        go by checking that ``RESULT_FILE`` exists and conforms to the
        property definitions that it promises.  Also append SI units
        """
        _result_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.RESULT_FILE  # pylint: disable=E1101
        )
        # Short-circuit if we already have a results.edn
        with self.runner_temp.in_dir():
            if not os.path.isfile(_result_file_path):
                raise cf.KIMRuntimeError(
                    "The Test or Verification Check did not produce a {} "
                    "results file.".format(_result_file_path)
                )

        # now, let's check whether this was actually a valid test result
        with self.runner_temp.in_dir(), open(
            _result_file_path, "r", encoding="utf-8"
        ) as result_file:
            try:
                result = util.loadedn(result_file)
                result = kimunits.add_si_units(result)
                # While we have the results file loaded, also record what
                # properties are reported in it so we can add them to
                # pipelinespec
                if isinstance(result, dict):
                    properties_reported = list(result["property-id"])
                elif isinstance(result, (list, tuple)):
                    properties_reported = list({x["property-id"] for x in result})
                    properties_reported.sort()
                    self.info_dict = {"properties": properties_reported}
            except Exception:
                raise cf.PipelineResultsError(
                    "The results file produced by "
                    "the Test or Verification Check ({}) is not valid "
                    "EDN".format(_result_file_path)
                )
            
            if self.verify:
                # Check whether the entries in results file are valid
                # property instances
                valid, msg = test_result_valid(_result_file_path)
                if not valid:
                    raise cf.PipelineResultsError(
                        "Test Result or Verification Result did not conform "
                        "to property definition\n{}".format(msg)
                    )

        with self.runner_temp.in_dir(), open(
            _result_file_path, "w", encoding="utf-8"
        ) as result_file:
            util.dumpedn(result, result_file)

    def gather_profiling_info(self, extrainfo=None):
        """
        Append the profiling information obtained in ``execute_in_place``
        to the information metadata.  This will saved during the ``write_result``
        method later on.
        """
        # Add metadata
        info_dict = {}
        info_dict["runtime"] = round(self.runtime, 2)
        info_dict["created-at"] = int(round(time.time()))
        if extrainfo:
            info_dict.update(extrainfo)

        _stderr_file = os.path.join(
            cf.OUTPUT_DIR, cf.STDERR_FILE  # pylint: disable=E1101
        )
        # get the information from the timing script
        with self.runner_temp.in_dir():
            if os.path.exists(_stderr_file):
                with open(_stderr_file, encoding="utf-8") as stderr_file:
                    stderr = stderr_file.read()
                try:
                    time_str = stderr.splitlines()[-1]
                    time_dat = json.loads(time_str)
                    info_dict.update(time_dat)
                except ValueError:
                    print("No timing information recovered from child process")
                except IndexError:
                    pass

        if self.info_dict:
            self.info_dict.update(info_dict)
        else:
            self.info_dict = info_dict

    def write_result(self, error=False, exc=None, create_mismatch=False):
        """
        Write the remaining information to make the final test result
        object.  This includes:

            * Checking for errors in the previous steps.  If there are any skip
              and move directory to the error directory

            * Creating ``CONFIG_FILE`` and ``PIPELINESPEC_FILE`` for result
              metadata

            * Moving the ``output`` directory to its final resting place

        Although we have introduced the create_mismatch argument here in case
        we decide we want to generate mismatch Errors on the User VM, this
        is only currently only used in production.
        """
        # Set the result path to 'er' if there was an error, or 'tr' or 'vr' for
        # Test Result and Verification Result, resp., if there was no error.
        # Also note that one of the suffixes '-tr', '-vr', or '-er' will be appended
        # to the UUID for any result or error so that its type can be discerned
        # solely from its name (a general philosophy we've tried to maintain).
        if error:
            self.result_type = "er"
        else:
            self.result_type = self.runner_temp.result_leader.lower()
        if self.result_code:
            self.result_code = "{}-{}".format(self.result_code, self.result_type)
        self.uuid = self.result_code
        self.result_path = os.path.join(
            cf.item_subdir_names[self.result_type], self.result_code
        )
        self.full_result_path = os.path.join(
            cf.LOCAL_REPOSITORY_PATH, self.result_path  # pylint: disable=E1101
        )

        # If there was an error, write the traceback to file, as well
        _exception_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.EXCEPTION_FILE  # pylint: disable=E1101
        )
        if error:
            with self.runner_temp.in_dir(), open(
                _exception_file_path, "w", encoding="utf-8"
            ) as exception_file:
                exception_file.write(str(exc or ""))

        # create the kimspec.edn file for the test results
        kimspec = {}
        kimspec[self.runner.runner_name] = self.runner.kim_code
        kimspec[self.subject.subject_name] = self.subject.kim_code
        kimspec["domain"] = "openkim.org"

        pipelinespec = {}
        if self.info_dict:
            pipelinespec["profiling"] = self.info_dict
        if self.result_code:
            if error:
                kimspec["error-result-id"] = self.result_code
                pipelinespec["error-result-id"] = self.result_code
            else:
                if self.result_type == "tr":
                    kimspec["test-result-id"] = self.result_code
                    pipelinespec["test-result-id"] = self.result_code
                elif self.result_type == "vr":
                    kimspec["verification-result-id"] = self.result_code
                    pipelinespec["verification-result-id"] = self.result_code

        # Append the reason for the Error to pipelinespec.edn
        if error:
            if create_mismatch:
                pipelinespec["error-category"] = ["mismatch"]
            else:
                pipelinespec["error-category"] = ["other"]

        _config_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.CONFIG_FILE  # pylint: disable=E1101
        )
        _pipelinespec_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.PIPELINESPEC_FILE  # pylint: disable=E1101
        )
        with self.runner_temp.in_dir(), open(
            _config_file_path, "w", encoding="utf-8"
        ) as config_file:
            util.dumpedn(kimspec, config_file, allow_nils=False)
        with self.runner_temp.in_dir(), open(
            _pipelinespec_file_path, "w", encoding="utf-8"
        ) as pipelinespec_file:
            util.dumpedn(pipelinespec, pipelinespec_file, allow_nils=False)

        outputdir = os.path.join(
            self.runner_temp.path, cf.OUTPUT_DIR  # pylint: disable=E1101
        )

        # short circuit moving over the result tree if we have no result code
        if not self.result_code:
            self.full_result_path = outputdir
            return

        # copy over the entire tree if it is done
        try:
            shutil.rmtree(self.full_result_path)
        except OSError:
            pass
        finally:
            shutil.copytree(outputdir, self.full_result_path)

    def format_exception(self, exc):
        trace = traceback.format_exc()

        _stdout_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.STDOUT_FILE  # pylint: disable=E1101
        )
        _stderr_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.STDERR_FILE  # pylint: disable=E1101
        )
        _kimlog_file_path = os.path.join(
            cf.OUTPUT_DIR, cf.KIMLOG_FILE  # pylint: disable=E1101
        )

        file_paths = [_stdout_file_path, _stderr_file_path, _kimlog_file_path]
        tails = last_output_lines(self.runner_temp, file_paths)

        outs = trace + "\n"
        for file, _tail in zip(file_paths, tails):
            outs += file + ":\n"
            outs += "".join(["-"] * (len(file) + 1)) + "\n"
            outs += append_newline(_tail) + "\n"
        return cf.PipelineRuntimeError(exc, outs)

    def run(self, extrainfo=None):
        """
        Run a runner with the corresponding subject, with /usr/bin/time
        profiling, capture the output as a dict, and return or run a V{T,M}
        with the corresponding {TE,MO}

        If result_code is set, then run in a temporary directory, otherwise
        run in place in the test folder.

        If errors occur, print the last lines of all output files and
        report the error back while moving the result into the errors
        directory.
        """
        with self.tempdir():
            try:
                self.execute_in_place()
                self.process_output()
                self.gather_profiling_info(extrainfo)
                self.write_result(error=False)
            except (KeyboardInterrupt, SystemExit) as exc:
                raise exc
            except Exception as exc:  # pylint: disable=W0703
                exc = self.format_exception(exc)
                self.gather_profiling_info(extrainfo)
                self.write_result(error=True, exc=exc)
                # Don't reraise e here

    def package_for_build_error(self, exception, extrainfo=None):
        """
        To be used if the runner or subject fails to build for a given job. This
        function will create an '-er' directory for the job with empty STDIN and
        STDOUT files, while the STDERR and EXCEPTION files will have the relevant
        build exception placed inside of them.  The runtime will remain the default
        value of -1.

        The resulting error directory can then be sync'd back to the Gateway and
        eventually to shared repo.
        """
        with self.tempdir():
            exc = self.format_exception(exception)
            self.gather_profiling_info(extrainfo)
            self.write_result(error=True, exc=exc)


# ================================================================
# helper functions
# ================================================================
def tail(file_path, num_lines=5):
    """
    Return the last ``num_lines`` lines of a file by making a shell call to the
    unix `tail` utility.

    Parameters
    ----------
    file_path : str
        The path (relative or absolute) of the desired file.
    n : int, optional
        The number of lines of output at the end of the file to return. If this
        parameter exceeds the number of lines in the entire file, all lines in
        the file will be returned. (Default: 5)

    Returns
    -------
    list
        Contains the requested n lines of trailing output of the file.
    """
    try:
        if os.path.exists(file_path):
            # Blocking call to command line 'tail' util
            tail_stdout = subprocess.check_output(
                ["tail", "-n", str(num_lines), file_path], encoding="utf-8"
            )
            lines = tail_stdout.splitlines()
        else:
            lines = [""]
    except subprocess.CalledProcessError:
        lines = [""]

    return "".join(lines)


def last_output_lines(kimobj, file_paths, num_lines=50):
    """Return the last lines of all output files"""
    with kimobj.in_dir():
        tails = [tail(file, num_lines) for file in file_paths]
    return tails


def append_newline(string):
    """Append a newline is there isn't one present"""
    if len(string) > 0 and string[-1] != "\n":
        string += "\n"
    return string


def test_result_valid(flname):
    """
    Uses the kim_property module to check whether all property instances
    contained in file are valid w.r.t. the current KIM property
    definitions.  See

        https://github.com/openkim/kim-property
    """
    try:
        kim_property.check_property_instances(fi=flname, fp_path=kim_property.get_properties())
    except (kim_property.KIMPropertyError, kim_edn.KIMEDNDecodeError):
        valid = False
        msg = traceback.format_exc()
    else:
        valid = True
        msg = None

    return valid, msg
