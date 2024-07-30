"""
Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import shutil
import subprocess
import os
from contextlib import contextmanager
import traceback

import packaging.specifiers, packaging.version
from . import util
from . import kimcodes
from . import template
from . import config as cf

# ------------------------------------------------
# Base KIMObject
# ------------------------------------------------
class KIMObject:
    """The base KIMObject that all things inherit from

    Attributes:
        required_leader
            the required two letter leader for all kim codes, meant to be overridden
            by subclassers
        makeable
            marks the type of kimobject as makeable or not, to be overriden by subclassers
        path
            the full path to the directory associated with the kim object
        kim_code
            the full kim_code
        kim_code_name
            the name at the front of the kim_code or None
        kim_code_leader
            the two digit prefix
        kim_code_number
            the 12 digit number as string
        kim_code_version
            the version number as string
        parent_dir
            the parent directory of the object, i.e. the ``te`` directory for a test object

    """

    # the required leader to this classes kim_codes
    required_leader = None
    # whether or not objects of this type are makeable
    makeable = False

    def __init__(self, kim_code, subdir=None, abspath=None, approved=True):
        """Initialize a KIMObject given the kim_code

        Args:
            kim_code (str)
                A full or partial kim_code, i.e. one like:
                 * "Full_Name_of_thing__TE_000000000000_000"
                 * "TE_000000000000_000"
                 * "TE_000000000000"
                 * "Full_Name_of_thing__TE_000000000000"
            subdir (str)
                In order to point to a directory that does not follow that pattern
                LOCAL_REPOSITORY_PATH/{model-drivers,models,tests...}/KIM_CODE/KIM_CODE
                can provide the folder of
                LOCAL_REPOSITORY_PATH/{models,model-drivers,tests...}/SUBDIR/KIM_CODE
        """
        name, leader, num, version = kimcodes.parse_kim_code(kim_code)

        # check to see if we have the right leader
        if self.required_leader:
            assert (
                leader == self.required_leader
            ), "{} not a valid KIM code for {}".format(
                kim_code, self.__class__.__name__
            )

        # grab the attributes
        self.kim_code_name = name
        self.kim_code_leader = leader
        self.kim_code_number = num
        self.kim_code_version = version
        self.kim_code = kim_code
        self.kim_code_id = kimcodes.strip_name(self.kim_code)
        self.kim_code_short = kimcodes.strip_version(self.kim_code)

        # Determine where this KIMObject sits in the local repository
        if approved:
            self.parent_dir = os.path.join(
                cf.LOCAL_REPOSITORY_PATH,
                cf.item_subdir_names[self.kim_code_leader.lower()],
            )
        else:
            self.parent_dir = os.path.join(
                os.path.join(cf.LOCAL_REPOSITORY_PATH, "pending"),
                cf.item_subdir_names[self.kim_code_leader.lower()],
            )

        if subdir is not None:
            path = os.path.join(self.parent_dir, subdir)
            # Check that the directory exists
            if os.path.isdir(path):
                self.path = path
            else:
                raise IOError("Directory {} not found".format(path))
        else:
            path = os.path.join(self.parent_dir, self.kim_code)
            # Check that the directory exists
            if os.path.isdir(path):
                self.path = path
            else:
                raise IOError("Directory {} not found".format(path))

        if abspath is not None:
            self.path = abspath

        # assume the object is not built by default
        self.built = False

    def __str__(self):
        """the string representation is the full kim_code"""
        return self.kim_code

    def __repr__(self):
        """The repr is of the form <KIMObject(kim_code)>"""
        return "<{}({})>".format(self.__class__.__name__, self.kim_code)

    def __hash__(self):
        """The hash is the full kim_code"""
        return hash(self.kim_code)

    def __eq__(self, other):
        """Two KIMObjects are equivalent if their full kim_code is equivalent"""
        if other:
            return str(self) == str(other)
        return False

    @contextmanager
    def in_dir(self):
        """a context manager to do things inside this objects path
        Usage::

            foo = KIMObject(some_code)
            with foo.in_dir():
                # < code block >

        cd into the path of the kim object before executing the actual
        code block.  Then return back to the directory you were at
        """
        cwd = os.getcwd()
        os.chdir(self.path)

        try:
            yield
        except Exception as e:
            raise e
        finally:
            os.chdir(cwd)

    @property
    def driver(self):
        """Default to having no driver"""
        return None

    @classmethod
    def all_on_disk(cls):
        """
        Return a generator for all items of this KIMObject type that can be found on disk
        in the local repository. If approved_only=True, only approved items are included;
        otherwise, both approved and pending items on disk are included (currently not used).
        """
        type_dir = os.path.join(
            cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[cls.required_leader.lower()]
        )
        kim_codes = (
            subpath
            for subpath in os.listdir(type_dir)
            if (
                os.path.isdir(os.path.join(type_dir, subpath))
                and kimcodes.iskimid(subpath)
                and not os.path.islink(os.path.join(type_dir, subpath))
            )
        )

        for kim_code in kim_codes:
            try:
                yield cls(kim_code)
            except Exception as exc:  # FIXME: Need more specific handling
                print(
                    "Failed to instantiate KIMObject for {}:\n{}".format(
                        kim_code, traceback.format_exc(exc)
                    )
                )

    @classmethod
    def all_fresh_on_disk(cls):
        """
        Return a generator for all fresh items of this KIMObject type that can be found on disk
        in the local repository.
        """
        # First, get a generator for all KIM Items of this type and convert it to a list
        all_items = list(cls.all_on_disk())

        # Separate the shortnames from the short-ids
        short_names = {}
        short_ids = []

        for item in all_items:
            name, num, leader, version = kimcodes.parse_kim_code(item.kim_code)
            short_id = ("_").join((num, leader, version))
            short_names[short_id] = name
            short_ids.append(short_id)

        # Sort the short-ids descendingly
        short_ids.sort(reverse=True)

        # Iterate through short-ids. Every time a new shortcode is encountered
        # record the item as being fresh
        fresh_items = []

        prev_short_code = ""
        for _, item in enumerate(short_ids):
            short_code = item.split("_")[0:2]
            if short_code != prev_short_code:
                short_name = short_names[item]
                fresh_items.append(short_name + "__" + item)
                prev_short_code = short_code

        return (kim_obj(x) for x in fresh_items)

    @property
    def kimspec(self):
        specfile = os.path.join(self.path, cf.CONFIG_FILE)
        if not os.path.exists(specfile):
            raise cf.PipelineFileMissing(
                "Could not locate file 'kimspec.edn' for {}".format(self.kim_code)
            )

        spec = {}
        with open(specfile, encoding="utf-8") as f:
            spec = util.loadedn(f)
        return spec

    @property
    def kim_api_version(self):
        if not self.kimspec.get("kim-api-version"):
            raise cf.MetadataKeyMissing(
                "Required key 'kim-api-version' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        return self.kimspec["kim-api-version"]

    def make(self, approved=True, num_make_procs=1, verbose=False):
        """For Models, Model Drivers, and Simulator Models, check if their
        item directory has a 'build' subdir; if it does not, create it.  Next,
        descend into 'build' and invoke cmake. Finally, do `make` and `make
        install`.  Note that we leave the build directory around to cut
        down on unnecessary recompilation.  For Tests, Test Drivers, and
        Verification Checks, simply go into their item directory and do
        `make` and `make install`.  If the item is a Test or Model which
        uses a driver, attempt to compile the driver first and then compile
        the item itself."""
        if packaging.version.Version(
            self.kim_api_version
        ) not in packaging.specifiers.SpecifierSet(cf.__kim_api_version_support_spec__):
            errmsg = (
                "Currently installed KIM API version ({}) is not "
                "compatible with object's ({})".format(
                    cf.__kim_api_version__, self.kim_api_version
                )
            )
            raise cf.UnsupportedKIMAPIversion(errmsg)

        # Attempt to build driver first, if this item has one
        driver = self.driver
        if driver:
            try:
                driver_kimobj = kim_obj(driver)
                driver_kimobj.make(verbose=verbose)
            except IOError:
                print(
                    "Cannot build driver {} of {}. Skipping build of "
                    "driver and continuing with build of item...\n".format(
                        driver, self.kim_code
                    )
                )

        if verbose:
            stdout = stderr = None
        else:
            stdout = stderr = subprocess.DEVNULL

        with self.in_dir():
            try:
                leader = self.kim_code_leader.lower()
                if leader in ["md", "mo", "sm"]:

                    build_dir = os.path.join(self.path, "build")
                    if not os.path.isdir(build_dir):
                        os.mkdir(build_dir)

                    # NOTE: We abstain from using
                    #   `kim-api-collections-management install`
                    # here because that will sometimes try to download tarballs
                    # of the items, whereas we want to be certain we always use
                    # the local copies for making/installing/cleaning.  All
                    # remote copies of items should be retrieved by `kimitems
                    # install`
                    subprocess.check_call(
                        [
                            "cmake",
                            self.path,
                            "-DCMAKE_BUILD_TYPE=" + cf.CMAKE_BUILD_TYPE,
                            "-DKIM_API_INSTALL_COLLECTION=USER",
                        ],
                        cwd=build_dir,
                        stdout=stdout,
                        stderr=stderr,
                    )
                    subprocess.check_call(
                        ["make", "-j", str(num_make_procs)],
                        cwd=build_dir,
                        stdout=stdout,
                        stderr=stderr,
                    )
                    subprocess.check_call(
                        ["make", "install"], cwd=build_dir, stdout=stdout, stderr=stderr
                    )

                elif leader in ["td", "te", "vc"]:

                    # First, check for a makefile
                    possible_makefile_names = [
                        "GNUmakefile",
                        "makefile",
                        "Makefile",
                    ]

                    found_makefile = False
                    for makefile_name in possible_makefile_names:
                        if os.path.isfile(os.path.join(self.path, makefile_name)):
                            found_makefile = True
                            break

                    if found_makefile:
                        subprocess.check_call(
                            ["make", "-j", str(num_make_procs)],
                            stdout=stdout,
                            stderr=stderr,
                        )

                    else:
                        # Try to build with cmake in test directory (since
                        # nothing from runners gets installed anywhere
                        # specifically)

                        subprocess.check_call(
                            [
                                "cmake",
                                self.path,
                                "-DCMAKE_BUILD_TYPE=" + cf.CMAKE_BUILD_TYPE,
                            ],
                            cwd=self.path,
                            stdout=stdout,
                            stderr=stderr,
                        )
                        subprocess.check_call(
                            ["make", "-j", str(num_make_procs)],
                            cwd=self.path,
                            stdout=stdout,
                            stderr=stderr,
                        )

            except:
                raise cf.KIMBuildError("Could not build {}".format(self.kim_code))

        self.built = True

    def make_clean(self, approved=True):
        """For Models, Model Drivers, and Simulator Models, remove them from
        KIM API user collection and delete the 'build' subdirectory inside
        of their directory. For Tests, Test Drivers, and Verification
        Checks, issue a ``make clean`` in an object's directory. Note that
        this does not clean the directory of the item's driver, if it has
        one."""
        with self.in_dir():
            try:
                if self.kim_code_leader.lower() in ["md", "mo", "sm"]:
                    # Remove shared library from user collection
                    with open(os.devnull, "w") as devnull:
                        p = subprocess.Popen(
                            ["kim-api-collections-management", "remove", self.kim_code],
                            stdin=subprocess.PIPE,
                            stdout=devnull,
                            stderr=devnull,
                        )
                        p.communicate(input=b"y")

                    # Remove build directory
                    build_dir = os.path.join(self.path, "build")
                    if os.path.isdir(build_dir):
                        shutil.rmtree(build_dir)

                elif self.kim_code_leader in ["td", "te", "vc"]:
                    subprocess.check_call(["make", "clean"])

            except:
                raise cf.KIMBuildError("Could not clean {}".format(self.kim_code))

        self.built = False

    def delete(self):
        """Delete the folder for this object
        .. note::
            Not to be used lightly!
        """
        shutil.rmtree(self.path)


# =============================================
# Actual KIM Models
# =============================================

# --------------------------------------------
# Meta Guys
# --------------------------------------------


class Runner(KIMObject):
    """
    An executable KIM Item.  This may be a Test or Verification Check.  The
    corresponding subject will be a Model.
    """

    makeable = True
    result_leader = "TR"

    def __init__(self, kim_code, *args, **kwargs):
        super(Runner, self).__init__(kim_code, *args, **kwargs)
        self.executable = os.path.join(self.path, cf.TEST_EXECUTABLE)
        self.infile_path = os.path.join(self.path, cf.INPUT_FILE)
        self.depfile_path = os.path.join(self.path, cf.DEPENDENCY_FILE)

    def __call__(self, *args, **kwargs):
        """Calling a runner object executes its executable in its own
        directory.  args and kwargs are passed to ``subprocess.check_call``.
        """
        with self.in_dir():
            subprocess.check_call(self.executable, *args, **kwargs)

    @property
    def infile(self):
        """return a file object for the INPUT_FILE"""
        return open(self.infile_path, encoding="utf-8")

    @property
    def depfile(self):
        """return a file object for DEPENDENCY_FILE"""
        if os.path.isfile(self.depfile_path):
            return open(self.depfile_path, encoding="utf-8")
        return None

    def processed_infile(self, subject):
        """Process the input file, with template, and return a file object to
        the result"""
        template.process(self.infile_path, subject, self)
        return open(
            os.path.join(self.path, cf.OUTPUT_DIR, cf.TEMP_INPUT_FILE), encoding="utf-8"
        )

    @property
    def template(self):
        return template.template_environment.get_template(
            os.path.join(self.path, cf.TEMPLATE_FILE)
        )

    @property
    def children_on_disk(self):
        return None

    @property
    def fresh_children_on_disk(self):
        return None

    @property
    def matching_models(self):
        """
        Specifies what types of subjects the runner can match with, as a list of strings.  Required to be present.
        """
        if not self.kimspec.get("matching-models"):
            raise cf.MetadataKeyMissing(
                "Required key 'matching-models' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        else:
            return self.kimspec["matching-models"]


class Subject(KIMObject):
    """
    Something that is run against.  Since we no longer have Test Verifications,
    a subject is always going to be a Model or a Simulator Model.
    """

    makeable = True

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the Model, with a kim_code"""
        super(Subject, self).__init__(kim_code, *args, **kwargs)

    @property
    def children_on_disk(self):
        return None

    @property
    def fresh_children_on_disk(self):
        return None

    def delete(self):
        """
        Remove the subject using the KIM API collections management utility
        """
        shutil.rmtree(self.path)

    @property
    def kimspec(self):
        specfile = os.path.join(self.path, cf.CONFIG_FILE)
        if not os.path.exists(specfile):
            raise cf.PipelineFileMissing(
                "Could not locate file 'kimspec.edn' for {}".format(self.kim_code)
            )

        spec = {}
        with open(specfile, encoding="utf-8") as f:
            spec = util.loadedn(f)
        return spec


# ===============================================
# Subject Objs
# ==============================================

# --------------------------------------
# Model
# -------------------------------------
class Model(Subject):
    """A KIM Model, KIMObject with

    Settings:
        required_leader = "MO"
        makeable = True
    """

    required_leader = "MO"
    makeable = True
    subject_name = "model"

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the Model, with a kim_code"""
        super(Model, self).__init__(kim_code, *args, **kwargs)

    @property
    def model_driver(self):
        """Return the model driver if there is one, otherwise None, currently,
        this tries to parse the kim file for the MODEL_DRIVER_NAME line"""
        return self.kimspec.get("model-driver")

    @property
    def driver(self):
        return self.model_driver

    @property
    def species(self):
        if not self.kimspec.get("species"):
            raise cf.MetadataKeyMissing(
                "Required key 'species' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        return self.kimspec["species"]


# --------------------------------------
# Simulator Model
# -------------------------------------
class SimulatorModel(Subject):
    """A KIM Model, KIMObject with

    Settings:
        required_leader = "SM"
        makeable = True
    """

    required_leader = "SM"
    makeable = True
    subject_name = "simulator-model"

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the Simulator Model, with a kim_code"""
        super(SimulatorModel, self).__init__(kim_code, *args, **kwargs)

    @property
    def species(self):
        if not self.kimspec.get("species"):
            raise cf.MetadataKeyMissing(
                "Required key 'species' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        return self.kimspec["species"]

    @property
    def simulator(self):
        if not self.kimspec.get("simulator-name"):
            raise cf.MetadataKeyMissing(
                "Required key 'simulator-name' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        return self.kimspec["simulator-name"]

    @property
    def simulator_potential(self):
        if not self.kimspec.get("simulator-potential"):
            raise cf.MetadataKeyMissing(
                "Required key 'simulator-potential' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        return self.kimspec["simulator-potential"]
    
    @property
    def run_compatibility(self):
        """
        Whether the SM can run against regular Tests (that are designed to run
        against portable models) as opposed to Tests that are specifically
        constructed to run against a particular subclass of SMs.
        """
        if not self.kimspec.get("run-compatibility"):
            raise cf.MetadataKeyMissing(
                "Required key 'run-compatibility' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )
        else:
            return self.kimspec["run-compatibility"]



# =============================================
# Runner Objs
# =============================================

# ---------------------------------------------
# Test
# ---------------------------------------------
class Test(Runner):
    """A kim test, it is a KIMObject, plus

    Settings:
        required_leader = "TE"
        makeable = True

    Attributes:
        executable
            a path to its executable
        outfile_path
            path to its INPUT_FILE
        infile_path
            path to its OUTPUT_FILE
        out_dict
            a dictionary of its output file, mapping strings to
            Property objects
    """

    required_leader = "TE"
    makeable = True
    subject_type = Model
    result_leader = "TR"
    runner_name = "test"

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the Test, with a kim_code"""
        super(Test, self).__init__(kim_code, *args, **kwargs)

    @property
    def test_driver(self):
        """Return the Test Driver listed in this Test's kimspec file"""
        return self.kimspec.get("test-driver")

    @property
    def driver(self):
        return self.test_driver

    @property
    def species(self):
        if not self.kimspec.get("species"):
            raise cf.MetadataKeyMissing(
                "Required key 'species' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )

        return self.kimspec["species"]

    @property
    def simulator(self):
        drv = self.driver
        if drv:
            return kim_obj(drv).simulator

        if not self.kimspec.get("simulator-name"):
            raise cf.MetadataKeyMissing(
                "Required key 'simulator-name' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )

        return self.kimspec["simulator-name"]

    def runtime_dependencies(self):
        """
        Read the DEPENDENCY_FILE (currently dependencies.edn) for the runner
        item.  Note that these will usually be specified without a version
        number, and also that the list returned by this function only contains
        the Tests listed in the dependency file, not tuples containing those
        Tests with any Models.
        """
        # FIXME: Verify that each item listed in dependencies.edn is at least a
        #        partial kimcode for a Test, i.e. only Tests should be listed in
        #        dependencies.edn.
        if self.depfile:
            deps = util.loadedn(self.depfile)
            if not isinstance(deps, list):
                print(
                    "Dependencies file of item {} has invalid format (must be "
                    "a list)".format(self.kim_code)
                )
                raise cf.PipelineInvalidDepsFile(
                    "Dependencies file of item {} has invalid format (must "
                    "be a list)".format(self.kim_code)
                )
            for dep in deps:
                if not isinstance(dep, str):
                    print(
                        "Dependencies file entry {} of item {} has invalid "
                        "format (must be a string)".format(dep, self.kim_code)
                    )
                    raise cf.PipelineInvalidDepsFile(
                        "Dependencies file entry {} of item {} has invalid "
                        "format (must be a string)".format(dep, self.kim_code)
                    )
            # Cast each entry of deps to str to get rid of any unicode.
            deps = [str(dep) for dep in deps]
            return deps
        return []


# ------------------------------------------
# Verification Check
# ------------------------------------------
class VerificationCheck(Test):
    """A kim test, it is a KIMObject, plus

    Settings:
        required_leader = "VC"
        makeable = True

    Attributes:
        executable
            a path to its executable
        outfile_path
            path to its INPUT_FILE
        infile_path
            path to its OUTPUT_FILE
        out_dict
            a dictionary of its output file, mapping strings to
            Property objects
    """

    required_leader = "VC"
    makeable = True
    subject_type = Model
    result_leader = "VR"
    runner_name = "verification-check"

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the Test, with a kim_code"""
        super().__init__(kim_code, *args, **kwargs)

    @property
    def simulator(self):
        if not self.kimspec.get("simulator-name"):
            raise cf.MetadataKeyMissing(
                "Required key 'simulator-name' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )

        return self.kimspec["simulator-name"]


# ==========================================
# Drivers
# ===========================================

# ------------------------------------------
# Test Driver
# ------------------------------------------
class TestDriver(KIMObject):
    """A test driver, a KIMObject with,

    Settings:
        required_leader = "TD"
        makeable = True

    Attributes:
        executable
            the executable for the TestDriver
    """

    required_leader = "TD"
    makeable = True

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the TestDriver, with a kim_code"""
        super().__init__(kim_code, *args, **kwargs)
        self.executable = os.path.join(self.path, cf.TEST_EXECUTABLE)

    def __call__(self, *args, **kwargs):
        """Make the TestDriver callable, executing its executable in its own
        directory, passing args and kwargs to ``subprocess.check_call``
        """
        with self.in_dir():
            subprocess.check_call(self.executable, *args, **kwargs)

    @property
    def children_on_disk(self):
        """
        Return a generator of all of the Tests in the local repository which
        use this Test Driver.  In production, this function is only used as a
        secondary precaution when deleting a Test Driver from the system in
        order to ensure all of their children are indeed deleted. The
        Director's delete() function should already ensure that this secondary
        deletion step is unnecessary.

        This function is also used by the user VM command line utilities.
        """
        return (test for test in Test.all_on_disk() if self.kim_code == test.driver)

    @property
    def fresh_children_on_disk(self):
        """
        Same as children_on_disk, but only returns non-stale Tests which use
        this Test Driver.  Also used by the user VM command line utilities.
        """
        return (
            test for test in Test.all_fresh_on_disk() if self.kim_code == test.driver
        )

    @property
    def simulator(self):
        if not self.kimspec.get("simulator-name"):
            raise cf.MetadataKeyMissing(
                "Required key 'simulator-name' not found in "
                "kimspec.edn file of {}".format(self.kim_code)
            )

        return self.kimspec["simulator-name"]


# ------------------------------------------
# Model Driver
# ------------------------------------------
class ModelDriver(KIMObject):
    """A model driver, a KIMObject with,

    Settings:
        required_leader = "MD"
        makeable = True
    """

    required_leader = "MD"
    makeable = True

    def __init__(self, kim_code, *args, **kwargs):
        """Initialize the ModelDriver, with a kim_code"""
        super(ModelDriver, self).__init__(kim_code, *args, **kwargs)

    @property
    def children_on_disk(self):
        """
        Return a generator of all of the Models in the local repository which
        use this Model Driver.  In production, this function is only used as a
        secondary precaution when deleting a Model Driver from the system in
        order to ensure all of their children are indeed deleted. The
        Director's delete() function should already ensure that this secondary
        deletion step is unnecessary.

        This function is also used by the user VM command line utilities.
        """
        return (model for model in Model.all_on_disk() if self.kim_code == model.driver)

    @property
    def fresh_children_on_disk(self):
        """
        Same as children_on_disk, but only returns non-stale Models which use
        this Model Driver.  Also used by the user VM command line utilities.
        """
        return (
            model
            for model in Model.all_fresh_on_disk()
            if self.kim_code == model.driver
        )

    @property
    def kimspec(self):
        specfile = os.path.join(self.path, cf.CONFIG_FILE)
        if not os.path.exists(specfile):
            raise cf.PipelineFileMissing(
                "Could not locate file 'kimspec.edn' for {}".format(self.kim_code)
            )

        spec = {}
        with open(specfile, encoding="utf-8") as f:
            spec = util.loadedn(f)
        return spec


# --------------------------------------------
# Helper code
# --------------------------------------------
# two letter codes to the associated class
code_to_model = {
    "TE": Test,
    "MO": Model,
    "TD": TestDriver,
    "MD": ModelDriver,
    "SM": SimulatorModel,
    "VC": VerificationCheck,
}


def kim_obj(kim_code, *args, **kwargs):
    """Just given a kim_code try to make the right object, i.e. try to make a
    Test object for a TE code, etc."""
    if kimcodes.iskimid(kim_code):
        _, leader, _, _ = kimcodes.parse_kim_code(kim_code)
    else:
        raise cf.InvalidKIMCode(
            "Could not initialize KIMObject for {}: KIMObjects can only be "
            "instantiated for Tests, Models, Test Drivers, Model Drivers, "
            "Simulator Models, and Verification Checks.".format(kim_code)
        )
    try:
        cls = code_to_model.get(leader, KIMObject)
        kobj = cls(kim_code, *args, **kwargs)
    except IOError as e:
        raise IOError(
            "Could not initialize KIMObject for {}: {}".format(kim_code, str(e))
        )
    return kobj


def leaders():
    return [i.lower() for i in list(code_to_model.keys())]
