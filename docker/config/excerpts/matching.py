"""
Methods for determining whether a Test or Verification Check can run against a
Model or Simulator Model.

Copyright (c) 2014-2021, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import packaging.specifiers, packaging.version
from . import config as cf


def version_match(runner, subject):
    """
    Here, we first check once more that the kim-api-version listed in the kimspecs of a
    runner and a subject are compatible with the KIM API version currently installed in
    the pipeline.  This is relevant because we may (rarely) have cases where backwards
    compatibility-breaking revisions are made to the KIM API, and we currently only
    install the latest version of it.

    This function also defines which KIM API versions are compatible with which other KIM
    API versions in the sense of running a runner and a subject together.
    Now that KIM API v2 is upon us, this just consists of checking that both the
    runner and subject list that they are compatible with it.
    """
    ver = packaging.version.Version
    kim_api_supported_versions = packaging.specifiers.SpecifierSet(
        cf.__kim_api_version_support_spec__
    )

    runner_kim_api_ver = ver(runner.kim_api_version)
    subject_kim_api_ver = ver(subject.kim_api_version)

    # First, check if the KIM API versions listed for the runner and subject are compatible
    # with one another
    #
    runner_cat1 = ">= " + cf.tostr(cf.__kim_api_version_support_clauses__[2])

    # Form nice version specifier objects from these strings
    runner_cat1 = packaging.specifiers.SpecifierSet(runner_cat1)

    subject_leader = subject.kim_code_leader.lower()
    if subject_leader == "mo":
        subject_cat1 = ">= " + cf.tostr(cf.__kim_api_version_support_clauses__[2])

        # Form nice version specifier objects from these strings
        subject_cat1 = packaging.specifiers.SpecifierSet(subject_cat1)

        if subject_kim_api_ver in subject_cat1:
            if runner_kim_api_ver in runner_cat1:
                match = True
                mismatch_info = None
            else:
                match = False
        else:
            match = False

    elif subject_leader == "sm":
        subject_cat1 = ">= " + cf.tostr(cf.__kim_api_version_support_clauses__[2])

        # Form nice version specifier objects from these strings
        subject_cat1 = packaging.specifiers.SpecifierSet(subject_cat1)

        if subject_kim_api_ver in subject_cat1:
            if runner_kim_api_ver in runner_cat1:
                match = True
            else:
                match = False
        else:
            match = False

    # If the runner and subject KIM API versions were compatible, go ahead and check if they are compatible
    # with the installed version of the KIM API
    if match:
        mismatch_info = None

        # Now, check if the KIM API version listed for the runner and subject are compatible with the currently
        # installed KIM API in the pipeline
        if runner_kim_api_ver not in kim_api_supported_versions:
            match = False
            mismatch_info = (
                "KIM API version {} of {} is not currently supported".format(
                    runner_kim_api_ver, runner
                )
            )

        elif subject_kim_api_ver not in kim_api_supported_versions:
            # No need to raise UnsupportedKIMAPIversion here. Just indicate a mismatch to keep these items from running
            match = False
            mismatch_info = (
                "KIM API version {} of {} is not currently supported".format(
                    subject_kim_api_ver, subject
                )
            )

    else:
        mismatch_info = (
            "KIM API version {} of {} is incompatible with KIM "
            "API version {} of {}".format(
                runner_kim_api_ver, runner, subject_kim_api_ver, subject
            )
        )

    return (match, mismatch_info)


def simulator_match(runner, model):
    """
    Check if the simulator-name listed for a Test or VC is compatible with
    that listed in a Simulator Model.
    """
    runnersim = runner.simulator
    modelsim = model.simulator
    if runnersim is None:
        match = False
        mismatch_info = (
            "Simulator {} of {} is incompatible with simulator "
            "{} of {}".format(runnersim, runner, modelsim, model)
        )
    else:
        runnersim = runnersim.lower()
        modelsim = modelsim.lower()

        if runnersim == "ase":
            if modelsim in cf.ASE_SUPPORTED_SIMULATORS:
                match = True
                mismatch_info = None
            else:
                match = False
                mismatch_info = (
                    "Simulator {} of {} is incompatible with "
                    "simulator {} of {}. Simulators currently compatible "
                    "with ASE: {}.".format(
                        runnersim, runner, modelsim, model, cf.ASE_SUPPORTED_SIMULATORS
                    )
                )
        elif runnersim == modelsim:
            match = True
            mismatch_info = None
        else:
            match = False
            mismatch_info = (
                "Simulator {} of {} is incompatible with "
                "simulator {} of {}".format(runnersim, runner, modelsim, model)
            )

    return (match, mismatch_info)


def run_compatibility_matching_models_match(runner, subject):
    """
    Some SMs require some sort of special simulation setup to occur on the part
    of the Test or Verification Check, e.g. those that correspond to bonded
    potentials require that the bonding topology be explicitly defined by the
    Test or VC. Accordingly, Tests and VCs are now required to contain a key
    called "matching-models" in their kimspec file. This field is always
    array-valued and can either contain ["standard-models"] or a list of
    strings that define an SM subclass, e.g. ["iff/cvff", "iff/pcff"].
    The logic for this type of matching is as follows:

    (a) If the value of "matching-models" of the runner is the array
        ["standard-models"], the runner will match with all PMs as well as
        any SM that lists the value "portable-models" in the
        "run-compatibility" key of their kimspec (note that the
        "run-compatibility" key is required for all MOs and SMs).

    (b) If the value of "matching-models" of the runner is not
        ["standard-models"] but rather a list of special-purpose SM strings,
        then the runner will not run against PMs. Instead, it will match
        against any SM whose 'simulator-potential' kimspec value is contained
        in the "matching-models" array of the runner in the sense of a
        slash-delimited hierarchical scheme which is implemented in the
        simulator_potential_hierarchy_match function below.

    and is summarized in the following table:

    |----------------------------------------------------------------------------|
    |           Test/VC         |     |                                          |
    |  matching-models list "A" | PM  |                 SM                       |
    |===========================|=====|==========================================|
    |  A=["standard-models"]    | yes |  run-compatibility == "portable-models"  |
    |  A=[...]                  |  no |  simulator-potential in A                |
    |---------------------------|-----|------------------------------------------|
    """

    def simulator_potential_hierarchy_match(runner_matching_models, subject_sp):
        """
        This compatibility is based on truncation patterns that use slashes (/)
        to denote a hierarchy.  For example, if the runner has

          "matching-models" ["iff/"]

        it can (only) run against all SMs under the "iff/" hierarchy (and
        **not** against an SM that has 'simulator-potential' 'iff' with no
        trailing slash), whereas if it lists

          "matching-models" ["iff/cvff" "iff/pcff"]

        it can only run with SMs that list these specific strings in their
        kimspec.edn "simulator-potential" field (and nothing below these
        strings in the hierarchy, e.g. 'iff/cvff/long').
        """
        if subject_sp in runner_matching_models:
            match = True
            mismatch_info = None
        else:
            # Check if SM simulator-potential falls under a pattern in the
            # runner
            match = False
            mismatch_info = (
                "SM simulator-potential '%s' not found under any "
                "patterns in %s" % (subject_sp, runner_matching_models)
            )
            for sp in runner_matching_models:
                if sp.endswith("/"):
                    if subject_sp.startswith(sp):
                        match = True
                        mismatch_info = None

        return match, mismatch_info

    subject_leader = subject.kim_code_leader.lower()

    if runner.matching_models == ["standard-models"]:
        if subject_leader == "mo":
            match = True
            mismatch_info = None

        else:
            if subject.run_compatibility == "portable-models":
                match = True
                mismatch_info = None
            else:
                match = False
                mismatch_info = (
                    "Runner %s lists 'matching-models ['standard-models'] "
                    "but subject %s lists 'run-compatibility' 'special-purpose-models'"
                    % (runner, subject)
                )

    else:
        if subject_leader == "mo":
            match = False
            mismatch_info = (
                "Subject %s is portable model and 'matching-models' of "
                "runner %s field is not set to ['portable-models']." % (subject, runner)
            )

        else:
            # Only run with SMs whose "simulator-potential" field is compatible
            # with the runner's "matching-models" list.  Note that
            # 'run-compatibility' is completely ignored in this case
            match, mismatch_info = simulator_potential_hierarchy_match(
                runner.simulator_potential, subject.simulator_potential
            )

    return match, mismatch_info


def species_match(runner, subject):
    """
    Ensure that all species listed for a Test are present in the Model's
    species list.  The species are compared through literal comparison
    after converting to all lower case.  This means that if a Test lists
    "Argon" and a Model lists "Ar", they will not match. This function
    automatically returns True in the case that the runner is a Verification
    Check, i.e. it's currently required that all VCs support all species.
    """
    mismatch_info = None

    # For now, we will assume that all VCs must support all species, and
    # not even look for a 'species' key in its kimspec (which will obviously
    # not be required right now, either)
    if runner.kim_code_leader.lower() == "vc":
        match = True
    else:
        match = True

        runner_species = runner.species
        if isinstance(runner_species, str):
            runner_species = [runner_species]
        subject_species = subject.species
        if isinstance(subject_species, str):
            subject_species = [subject_species]

        runner_species = [x.lower() for x in runner_species]
        subject_species = [x.lower() for x in subject_species]

        for spec in runner_species:
            if spec not in subject_species:
                match = False
                mismatch_info = (
                    "Species {} listed in kimspec.edn file of {} could not be found "
                    "in the kimspec.edn file of {}".format(
                        spec.capitalize(), runner, subject
                    )
                )
                # Stop as soon as we have found a single unsupported species (there could be others)
                break

    return (match, mismatch_info)


def valid_match(runner, subject):
    """
    Check whether a runner and subject match.  This function returns a tuple whose first
    element is a boolean indicating whether the pair is a match and whose second element
    indicates the reason for a mismatch (in the event that the runner-subject pair is a
    match, the second entry takes the value None).  This involves checking the following:
    (1) If the runner is a Test, we first check to see if all of its species are supported
        by the subject.  If they are not, we exit, and the mismatch information is
        basically discarded because we decided that when creating bone fide Errors for
        mismatches, we would skip this case.
    (2) The kim-api-version of the runner and subject are compatible with one another
    (3) The kim-api-version listed in the kimspec of the runner and subject are compatible
        with the currently installed version of the KIM API
    (4) Next, we check for compatibility between the "matching-models" key of the runner
        and the subject.
    (5) Finally, if all of the above criteria indicate a match, we check that the runner's
        "simulator" key, if it exists, matches with the subject.  This is relevant only if
        if the subject is an SM.
    """

    runner_leader = runner.kim_code_leader.lower()
    subject_leader = subject.kim_code_leader.lower()

    if runner_leader == "te":
        match, mismatch_info = species_match(runner, subject)

        if match:
            match, mismatch_info = version_match(runner, subject)

            if match:
                match, mismatch_info = run_compatibility_matching_models_match(
                    runner, subject
                )

                if match and subject_leader == "sm":
                    match, mismatch_info = simulator_match(runner, subject)

    elif runner_leader == "vc":
        # Verification Checks must support all species, by definition, so proceed to version checks
        match, mismatch_info = version_match(runner, subject)

        if match:
            match, mismatch_info = run_compatibility_matching_models_match(
                runner, subject
            )

            if match:
                if subject_leader == "mo":
                    # Nothing to check beyond version matching for a Verification Check-Model pair
                    pass

                elif subject_leader == "sm":
                    match, mismatch_info = simulator_match(runner, subject)

    return (match, mismatch_info)
