"""
config.py holds all of the constants that are used throughout the pipeline scripts.

Mostly folders and a preliminary list of all of the available tests and models, as well
as the exceptions that will be used throughtout.

By convention the constants are all in UPPER_CASE_WITH_UNDERSCORES,
and this module is imported in star from at the top of all of the scripts::

    import config as cf

Copyright (c) 2014-2021, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import os
import re
import uuid


def tostr(cls):
    return ".".join(map(str, cls))


# First, record the current version of the pipeline and KIM API installed
__pipeline_api_version__ = "3.1.0"
__kim_api_version__ = "2.2.1"

# Note: We've stopped bothering with pipeline-api-version. It has been removed
#       from all fresh items.  Therefore, there are no associated support clauses
#       listed below.

# The following clauses specify what kim-api-versions that the KIM API currently installed
#
__kim_api_version_support_clauses__ = [(1, 6, 0), (1, 9, 0), (2, 0, 0)]

__kim_api_version_support_spec__ = ">= " + tostr(__kim_api_version_support_clauses__[2])

# =============================================================================
# the environment parsing equipment
# =============================================================================
ENVIRONMENT_FILE_NAME = "pipeline-env"
ENVIRONMENT_LOCATIONS = [
    os.environ.get("PIPELINE_ENVIRONMENT_FILE", ""),
    os.path.join("./", ENVIRONMENT_FILE_NAME),
    os.path.join(os.path.expanduser("~"), ENVIRONMENT_FILE_NAME),
    os.path.join("/pipeline", ENVIRONMENT_FILE_NAME),
]


def transform(val):
    # try to interpret the value as an int or float as well
    try:
        val = int(val)
    except ValueError:
        try:
            val = float(val)
        except ValueError:
            pass
    if val == "False":
        val = False
    if val == "True":
        val = True
    return val


def read_environment_file(filename):
    """
    Return a dictionary of key, value pairs from an environment file of the form:

        # comments begin like Python comments
        # no spaces in the preceding lines
        SOMETHING=value1
        SOMETHING_ELSE=12
        BOOLEAN_VALUE=True

        # can also reference other values with $VARIABLE
        NEW_VARIABLE=/path/to/$FILENAME
    """
    conf = {}
    lines = open(filename, encoding="utf-8").readlines()
    for line in lines:
        if not re.match(r"^[A-Za-z0-9\_]+\=.", line):
            continue

        # if we have a good line, grab the values
        var, val = line.strip().split("=")
        search = re.search(r"(\$[A-Za-z0-9\_]+)", val)
        if search:
            for rpl in search.groups():
                val = val.replace(rpl, conf[rpl[1:]])

        conf[var] = transform(val)
    return conf


def write_environment_file(conf, filename, overwrite=False):
    """
    Given a dict of pipeline environment variables, write them to the location
    specified by filename.  If the file already exists, an exception is raised
    unless overwrite=True.
    """
    PIPELINE_ENV_HEADER = """#!/bin/bash
#==============================================
# this file has a specific format since it is
# also read by python.  only FOO=bar and
# the use of $BAZ can be substituted. comments
# start in column 0
#==============================================

"""
    contents = PIPELINE_ENV_HEADER
    for key, val in list(conf.items()):
        contents += "{}={}\n".format(key, val)

    mode = "w" if overwrite else "x"
    with open(filename, mode) as f:
        f.write(contents)


def update_environment_file(conf, filename):
    if os.path.isfile(filename):
        new_conf = read_environment_file(filename)
        new_conf.update(conf)
    else:
        new_conf = conf

    write_environment_file(new_conf, filename, overwrite=True)


def machine_id():
    """Get a UUID for this particular machine"""
    s = ""
    files = ["/var/lib/dbus/machine-id", "/etc/machine-id"]
    for f in files:
        if os.path.isfile(f):
            s = open(f).read()

    if not s:
        s = str(uuid.uuid4())
    else:
        # transform the big string into a uuid-looking thing
        q = (0, 8, 12, 16, 20, None)
        s = "-".join([s[q[i] : q[i + 1]] for i in range(5)])
    return s.strip()


class Configuration(object):
    def __init__(self):
        """
        Load the environment for this pipeline instance.  First, load the default
        values from the Python package and then modify then using any local
        variables found in standard locations (see ENVIRONMENT_LOCATIONS)
        """
        # read in the default environment
        here = os.path.dirname(os.path.realpath(__file__))
        envf = os.path.join(here, "default-environment")
        conf = read_environment_file(envf)

        # supplement it with the default locations' extra file
        for loc in ENVIRONMENT_LOCATIONS:
            if os.path.isfile(loc):
                conf.update(read_environment_file(loc))
                break

        # then take variables from the shell environment
        for k in conf.keys():
            tempval = os.environ.get(k, None)
            if tempval is not None:
                conf.update({k: tempval})

        # add any supplemental variables that should exist internally
        # in the pipeline code

        # Simulators that we support through ASE
        # ** NB: These should all be in lower case **
        conf.update({"ASE_SUPPORTED_SIMULATORS": ["lammps", "asap"]})

        self.conf = conf
        self._transform_vars()
        if self.conf.get("KIM_REPOSITORY_DIR", None):
            raise RuntimeError(
                "KIM_REPOSITORY_DIR found in configuration, use "
                "LOCAL_REPOSITORY_PATH instead of KIM_REPOSITORY_DIR"
            )

    def _transform_vars(self):
        self.conf["INTERMEDIATE_FILES"] = [
            self.conf.get(i)
            for i in [
                "TEMP_INPUT_FILE",
                "STDOUT_FILE",
                "STDERR_FILE",
                "KIMLOG_FILE",
                "RESULT_FILE",
            ]
        ]

        if not self.conf.get("UUID"):
            self.conf["UUID"] = machine_id()

    def get(self, var, default=None):
        return self.conf.get(var, default)

    def variables(self):
        o = list(self.conf.keys())
        o.sort()
        return o

    def verify_ssh_configuration(self):
        pass


conf = Configuration()
globals().update(conf.conf)

item_subdir_names = {}
if conf.get("USE_FULL_ITEM_NAMES_IN_REPO"):
    item_subdir_names["md"] = "model-drivers"
    item_subdir_names["mo"] = "models"
    item_subdir_names["sm"] = "simulator-models"
    item_subdir_names["td"] = "test-drivers"
    item_subdir_names["te"] = "tests"
    item_subdir_names["vc"] = "verification-checks"

    item_subdir_names["er"] = "errors"
    item_subdir_names["tr"] = "test-results"
    item_subdir_names["vr"] = "verification-results"
else:
    item_subdir_names["md"] = "md"
    item_subdir_names["mo"] = "mo"
    item_subdir_names["sm"] = "sm"
    item_subdir_names["td"] = "td"
    item_subdir_names["te"] = "te"
    item_subdir_names["vc"] = "vc"

    item_subdir_names["er"] = "er"
    item_subdir_names["tr"] = "tr"
    item_subdir_names["vr"] = "vr"

globals().update({"item_subdir_names": item_subdir_names})

# Dir names used by KIM API
kim_api_collection_subdir_names = {}
kim_api_collection_subdir_names["md"] = "model-drivers-dir"
kim_api_collection_subdir_names["mo"] = "portable-models-dir"
kim_api_collection_subdir_names["sm"] = "simulator-models-dir"

# ====================================
# KIM ERRORS
# ====================================
class PipelineInvalidConfiguration(Exception):
    """If pipeline environment configuration variables conflict with one another"""


class InvalidKIMCode(Exception):
    """Used for invalid KIM IDS"""


class PipelineResultsError(Exception):
    """Used when the results are not of an understood type, i.e. not a valid JSON string"""


class KIMRuntimeError(Exception):
    """General purpose KIM API Error, used if an invocation of the KIM API doesn't behave"""


class UnsupportedKIMAPIversion(Exception):
    """Used in kimapi.make_object to indicate that an item's KIM API version listed in its kimspec
    is not compatible with the installed version of the KIM API"""


class KIMBuildError(Exception):
    """Error to throw when a build command fails"""


class RsyncRuntimeError(Exception):
    """Generic error to throw when rsync fails"""


class RsyncDriverError(Exception):
    """If a Model or Test is submitted but its Model Driver or Test Driver cannot be found"""


class PipelineFileMissing(Exception):
    """If a file we rely on is missing"""


class MetadataKeyMissing(Exception):
    """If a necessary kimspec.edn key, e.g. 'species' for a Test, is not found"""


class KIMItemMissing(Exception):
    """If the directory of a KIM Item does not exist in the local repository"""


class PipelineTimeout(Exception):
    """If a Runner time outs"""


class PipelineAbort(Exception):
    """If a job is aborted, for example, by a deletion request"""


class PipelineDataMissing(Exception):
    """If requested data doesn't exist"""


class PipelineInvalidDepsFile(Exception):
    """If the dependencies file of a Test is not properly formatted as a list of strings"""


class PipelineInvalidEDN(Exception):
    """If we attempt to load an EDN file or string that does not contain a list or dict"""


class PipelineInsertError(Exception):
    """There was a problem inserting the item into the Director's internal database"""


class PipelineSearchError(Exception):
    """If a search turns up bad, e.g. someone asks for a kim_code that we can't match against"""


class PipelineTemplateError(Exception):
    """some kind of templating format is wrong, doesn't conform to our templating directives"""


class PipelineQueryError(Exception):
    """there was an error while attempting a remote query"""


class PipelineRecursionDepthExceeded(Exception):
    """attempted to take more than MAX_DEPENDENCY_RECURSION_DEPTH steps during upward dependency resolution"""


class PipelineRuntimeError(Exception):
    """we had any number of errors while running"""

    def __init__(self, e, extra=""):
        self._e = e
        self.extra = extra
        super(PipelineRuntimeError, self).__init__(e, extra)

    def __getattr__(self, name):
        return getattr(self._e, name)

    def __str__(self):
        if isinstance(self._e, PipelineRuntimeError):
            return str(self._e)
        else:
            return "{}: {}\n\n{}".format(
                self._e.__class__.__name__, str(self._e), self.extra
            )

    # Uncommenting the override below means that no exception is itself passed with the Celery task
    # def __repr__(self):
    #    return str(self)


class KIMMismatchError(Exception):
    """Blanket error used when two fresh, complementary items cannot run with one another for any
    reason other than a species mismatch"""

    def __init__(self, e):
        self._e = e
        super(KIMMismatchError, self).__init__(e)

    def __getattr__(self, name):
        return getattr(self._e, name)

    def __str__(self):
        if isinstance(self._e, KIMMismatchError):
            return str(self._e)
        else:
            return "{}: {}".format(self.__class__.__name__, str(self._e))


# For ASE's LAMMPS calculator
os.environ["ASE_LAMMPSRUN_COMMAND"] = conf.get("ASE_LAMMPSRUN_COMMAND")

# For ASAP
os.environ["KIM_HOME"] = conf.get("KIM_HOME")
# os.environ['ASAP_KIM_DIR'] = conf.get('ASAP_KIM_DIR')
# os.environ['ASAP_KIM_INC'] = conf.get('ASAP_KIM_INC')
# os.environ['ASAP_KIM_LIB'] = conf.get('ASAP_KIM_LIB')

# For montydb. Required because our `pipeline-database` tool uses pymongo
os.environ["MONTY_ENABLE_BSON"] = "1"
