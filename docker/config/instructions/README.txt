Welcome to the KIM Developer Platform

Your sudo password is the same as your user name: "openkim"

Comments/questions/bug reports are appreciated and can be sent to support@openkim.org.

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This file may be distributed as-is, without modification.

-----------------------------------------------------------------------------------------

Summary of this document:

  Section I   - Installing additional packages
  Section II  - Docker basics
                  A. Terminology
                  B. Sharing files with the host
                  C. Allocating system resources
  Section III - Adding your KIM content to the container
  Section IV  - Running your content
                  A. General methodology
                  B. Where do results and errors end up?
                  C. How can I iteratively develop a KIM Item and rerun it?
                  D. What about dependencies between Tests?
  Section V   - Automatic generation of KIM Tests and Reference Data from templates
  Section VI  - Command-line utilities
                  A. kimitems
                       Used for searching through the official repository of
                       KIM Items and installing them onto the container
                  B. pipeline-database
                       Used for toggling the use of a local database for the
                       queries performed by Tests in their pipeline.stdin.tpl
                       files
                  C. pipeline-find-matches
                       Used for locating valid matches for a given item that
                       exist on the container, i.e. items which it can be run against
                  D. pipeline-run-matches
                       Used to run a given item against all matching items that
                       exist on the container
                  E. pipeline-run-pair
                       Used to run a specific pair of items on the container against
                       one another
                  F. pipeline-run-tests
                       Used to run all KIM Tests on the container against
                       a given KIM Model or Simulator Model on the container
                  G. pipeline-run-verification-checks
                       Used to run all KIM Verification Checks on the container against
                       a given KIM Model or Simulator Model on the container
                  H. kimgenie
                       Tool used to autogenerate KIM Tests and Reference Data using Jinja
                       templates

-----------------------------------------------------------------------------------------

Section I. Installing additional packages

  This container is based on ubuntu, and thus external packages such as text
  editors can conveniently be installed using apt-get.  For example, if you
  prefer not to use the vi editor bundled on the container, you can install
  emacs via:

    $ apt-get update
    $ apt-get install emacs

  Be sure to execute apt-get update first in order to build the apt cache,
  which is not included in this image.


Section II. Docker basics

  A. Terminology

    The two main concepts of docker are "images" and "containers".  An image is
    essentially nothing more than a file system, and can either be
    constructed locally or retrieved from a remote registry such as DockerHub
    by doing `docker pull`.  Containers, on the other hand, should be thought of
    as specific instantiations of images.  They amount to taking the file
    system comprising the image and adding another layer on top of it in which
    new files can be created or existing files edited, then running a process
    within that layer.  Containers are typically created from images using the
    `docker run` command and passing the name of a a specific image and command
    to run as arguments.

    Note that the images in your local docker repository can be viewed by
    issuing `docker images`, while all of the containers created from your
    local images can be viewed with `docker ps -a` (the -a flag means to list
    all containers, even those which are not currently running).  You can view
    the size of the containers you've created by doing `docker ps -as`.

  B. Sharing files with the host

    As mentioned above, docker containers have an extra writeable layer on top
    of the image from which they are created.  If you create a new file inside
    of a running container (or edit a file that was in the original image), it
    is stored in this layer.  Stopping a container, e.g. by exiting the original
    shell session attached to it, will still retain all of the files in its
    writeable layer.  However, deleting a container using `docker rm` will
    completely and irreversibly annihilate them (!).  Therefore, one should
    use the `docker cp` command (from the host, i.e. your laptop or desktop)
    to copy any important files onto the host before actually destroying the
    container.

    Because docker containers are designed to be ephemeral, using `docker cp`
    to transfer files to and from a container from the host can be tedious.
    Therefore, two additional mechanisms for sharing files between a host and a
    container exist in docker: "bind mounts" and "volumes".  Both of these
    exist independently of any container and, thus, even if a container they
    are attached to is deleted, their contents are safe.  A bind mount is an
    explicit mounting of a directory on the host machine to a directory inside
    of a container, and must be done at the time a container is first created
    from an image using `docker run`.  For example, to mount the directory at
    /home/user/Documents/my_kim_stuff on the host to a directory called
    /home/openkim/kim-dev inside of a container, one could instantiate it via

      docker run -it --name kim_dev --mount \
        type=bind,source=/home/user/Documents/my_kim_stuff,target=/home/openkim/kim-dev \
        ghcr.io/openkim/developer-platform bash

    Unlike bind mounts, docker volumes are managed internally by docker, and
    thus aren't readily visible on the host.  The syntax for mounting a
    directory in a volume to a directory inside a container is the same as for
    bind mounts, only with "type=bind" omitted.

    Finally, note that on Windows hosts, where the host file system is very
    different from that of linux, volumes are far preferred to bind mounts.

    For more information, see:

      https://docs.docker.com/storage/bind-mounts/
      https://docs.docker.com/storage/volumes/

  C. Allocating system resources

    On macOS and windows, if you start Docker Desktop and open its settings
    page, there's a "Resources" tab that allows you to specify how many CPU
    cores, memory, swap space, and disk you want to reserve for Docker to use.
    Options for controlling resource allocation on a container-by-container
    basis can be found at
    https://docs.docker.com/config/containers/resource_constraints/.  In linux,
    resource control must be done on a container-by-container basis.

Section III. Adding your KIM content to the container

  Aside from this README file, the following directories can be found in your
  home directory (~):

  ~
  |-- model-drivers
  |-- models
  |-- simulator-models
  |-- test-drivers
  |-- tests
  |-- verification-checks
  |-- test-results
  |-- verification-results
  `-- errors

  The first six of these contain the corresponding KIM Items, while the latter
  three are used to store the output of any jobs that you run inside the
  container (more on this in the next section).  To begin developing KIM
  content, you can either download and install items from the official OpenKIM
  Repository using the `kimitems` utility (Section VI.A) or use any of the
  three methods outlined in Section II.B (`docker cp`, bind mounts, or docker
  volumes) to share files/directories on your host machine with a container.


Section IV. Running your content

  A. General methodology

    Once an item has been placed in the appropriate directory, e.g. ~/tests/,
    there are several ways in which it can be run.  First is the
    `pipeline-run-matches` utility, which can be used to run an item against
    all compatible matching items found in the KIM Items directories on your
    container (in ~).  For example, if a Test is passed to this command, it
    will run against all Models found in ~/models/ which support the same
    species as the Test and have a compatible KIM API version; it will also
    attempt to run against any Simulator Models in ~/simulator-models/ if these
    conditions are met and the 'simulator-name' listed in the kimspec.edn files
    of the Test and the Simulator Model are compatible.  Another method is
    the `pipeline-run-pair` utility, which allows a specific item pair
    (Test-Model, Test-Simulator Model, Verification Check-Model, or
    Verification Check-Simulator Model) to be run.  See also the
    `pipeline-run-tests` and `pipeline-run-verification-checks` utilities.

    NOTE: Currently, whether the 'simulator-name' listed in the kimspec of a
          Test or Verification Check is compatible with that listed in the
          kimspec of a Simulator Model amounts to testing whether the two
          corresponding string values are a case-insensitive literal match,
          except for the case where the Test or Verification Check lists
          'ase' (also case-insensitive).  In this latter case, the Simulator
          Model is considered compatible, at least as far as 'simulator-name'
          is concerned, if it lists either 'lammps' or 'asap'
          (case-insensitive).  This set may expand in the future as we write
          additional interface code between ASE and other simulators.

  B. Where do results and errors end up?

    As shown in the directory tree in Section III, Test Results produced by a
    Test coupled with a Model or Simulator Model are written to
    ~/test-results/.  Verification Results, which are produced by
    running a Verification Check with a Model or Simulator Model, are written
    to ~/verification-results/.  All Errors, whether produced from Tests or
    Verification Checks, are written to ~/errors/.

  C. How can I iteratively develop a KIM Item and rerun it?

    When `pipeline-run-matches` or `pipeline-run-pair` are called, they
    automatically attempt to rebuild the specified item(s).  In the case of a
    Model, this amounts to going into its directory under ~/models/ and
    performing the following:

      cd build && cmake .. -DCMAKE_BUILD_TYPE=Release -DKIM_API_INSTALL_COLLECTION=USER

    followed by `make` and `make install`; if it uses a driver, this is
    performed for its driver automatically before compiling the Model itself.
    The same procedure is followed by Simulator Models.  For Tests, Test
    Drivers, and Verification Checks, if a CMakeLists.txt files exists, a
    `cmake -DCMAKE_BUILD_TYPE=Release` is issued directly in their directory,
    followed by a `make`; if not, only a `make` is issued.

  D. What about dependencies between Tests?

    Generally speaking, the only dependencies that exist between KIM Items are
    those between Tests which are manifested as queries in their
    pipeline.stdin.tpl files.  These dependencies exist to reduce redundant
    computational expense as well as reduce the complexity of each individual
    Test.  For example, the current version of the elastic constants Test for
    fcc Al in KIM, ElasticConstantsCubic_fcc_Al__TE_944469580177_006, requires
    the lattice constant of fcc Al predicted by whichever model it is running
    against.  Rather than compute this value itself, it performs a query in its
    pipeline.stdin.tpl when it is run that retrieves it from the Test that
    specifically computes this, LatticeConstantCubicEnergy_fcc_Al__TE_156715955670_007.
    This means that when Tests are being paired with Models and run in the
    OpenKIM processing pipeline, the order in which they are run is important:
    for a given model, the fcc lattice constant Test must be run against it
    before the elastic constants Test.  To facilitate this type of job
    scheduling, each Test is required to explicitly record the other Tests it
    depends upon in a file named dependencies.edn.

    As it pertains to this container, dependencies between Tests are primarily
    important when developing a Model or Simulator Model that you have not
    actually uploaded to OpenKIM.  Recalling the example above, suppose you
    were developing a model for Al and wanted to run the fcc lattice constant
    and elastic constants Tests against it using one of the `pipeline-run-*`
    utilities.  The fcc Al lattice constant Test has no dependencies, and will
    thus generate a Test Result folder under ~/test-results/.  However, this
    result obviously won't be inserted into the official OpenKIM database
    hosted at query.openkim.org.  So, when you attempt to run the fcc Al
    elastic constants Test against your Model in the container, the query for
    the lattice constant in its pipeline.stdin.tpl file will return an empty
    array.

    To address this problem, it is possible to use a local database in the
    container by using the `pipeline-database` utility (see Section VI.B).
    Whereas by default all of the queries in the pipeline.stdin.tpl files of
    the Tests are directed to query.openkim.org, if you issue
    `pipeline-database set local`, they will all be directed to a local
    database that is stored on disk at /pipeline/db/ by default. Assuming this 
    has been done (the selection persists between starts/stops of the container), 
    you can then proceed to run all of the Tests in a dependency hierarchy in
    order.  In the example above, you would use `pipeline-run-pair` to run your
    Model or Simulator Model against the fcc Al lattice constant Test and then
    use it to run against the fcc Al elastic constants Test.^

    ^ Automatically scheduling jobs involving Tests based on the dependencies
    between them is complicated and currently this capability is not
    implemented with the container.  The `pipeline-run-tests` will simply run
    the Tests in alphabetical order.  This means that you must manually specify
    which Tests you want to run against your model and in what order using
    successive `pipeline-run-pair` calls.  Our development team is currently
    hashing out a way to avoid this nuisance for you by adding scheduling logic
    to `pipeline-run-tests`.


Section V. Automatic generation of KIM Tests and Reference Data from templates

  When developing a Test Driver, it is common to want to create a large number
  of Tests which make use of it.  For example, when creating a Test Driver
  which computes a property of a bulk crystal, each of its corresponding Tests
  typically corresponds to a different specific crystal lattice structure and
  atomic species.  The `kimgenie` utility is designed to facilitate the process
  of generating these Tests, and can also be used to similarly generate
  Reference Data from templates.  This utility requires that you supply a set
  of template files that ought to be created for each Test along with a json
  file containing dictionaries of keyword-value pairs, which each dictionary
  corresponding to a Test that is to be created.  See the description of
  `kimgenie` in the following section for more details.


Section VI. Command-line utilities

  The primary user interface for the container consists of command-line
  utilities.  These utilities are on the global system path and can thus be
  used from any directory.  Aside from the utilities themselves featuring tab
  completion, the arguments (at least, for those utilities which have
  arguments) also tab-complete based on the content currently in the KIM Items
  subdirectories of ~.  In fact, the option flags also tab-complete: typing '-'
  and tabbing will list available flags.  The '-h' or '--help' flags may be
  passed to any of the included utilities to view its description and a list of
  applicable arguments.  Finally, note that wildcard (*) completion for the
  utilities other than `kimitems` are standard globbing, whereas the argument
  to `kimitems` is interpreted as a Perl-compatible regular expression.

  NOTE: The names of these utilities may change in future releases of the KIM
  Developer Platform.

  A. kimitems

    This utility is intended to help manage all of the KIM Items under the
    different item subdirectories of ~.  It can be used to download, build, and
    install new items, as well as remove existing items.

    Usage:

      kimitems [-h] [-v] {build,download,install,search,remove} <search-term>

      Here, <search-term> can be either a full KIM ID (of a Test, Test Driver,
      Model, Model Driver, Simulator Model, or Verification Check) or any
      Perl-compatible regular expression.

      NOTE: Perl-compatible regular expressions (pcre) differ from globbing.
      In particular, one would implement a glob-style wildcard in pcre by using
      the pattern .* rather than a * alone.

    Examples:

      kimitems install EDIP_BOP_Bazant_Kaxiras_Si__MO_958932894036_002
      kimitems remove -h
      kimitems build all
      kimitems search --all --type md Pair.*
      kimitems search -t mo -s Al .*
      kimitems search -t mo .* -se Al
      kimitems search -t mo .* --species-exclusive Al Cu -vv

    Options
    =======

      The following options can be used with any `kimitems` subcommand, and all
      pertain to the search criteria being used to select items:

      -i, --ignore-case

        Perform case-insensitive matching against the specified search term

      -t TYPE, --type TYPE

        Match only KIM Items of the specified type: te (Test), td (Test Driver), mo
        (Model), md (Model Driver), sm (Simulator Model), or vc (Verification Check).
        Case-insensitive.

    Subcommands
    ===========

    + build

      Usage:

        kimitems build [-h] [-i] [-t TYPE] [-c] [-j J] [-v] search-term
        kimitems build all

      Searches the local repository for KIM Items and recompiles them.

      In the case of a Model or Simulator Model, this amounts to going into its
      directory under ~, creating a subdirectory called 'build' if it does not
      already exist and descending into it, and performing the following:

        cmake .. -DCMAKE_BUILD_TYPE=Release -DKIM_API_INSTALL_COLLECTION=USER

      followed by `make` and `make install`.  For Tests, Test Drivers, and
      Verification Checks, a `make` is issued inside of their directories.  If
      a Test or Model is specified which makes use of a Test Driver or Model
      Driver, respectively, this command will attempt to build the driver first
      before building the Test or Model itself.  If the special keyword 'all'
      is given as the argument, everything in ~/[tests, test-drivers, models,
      model-drivers, verification-checks] will attempt to build.

      Options
      -------

        -c, --clean

          For Models, Model-Drivers, and Simulator Models, remove their library
          binaries from the KIM API user collection and delete the 'build'
          subdirectory in their directories before rebuilding.  For Tests, Test
          Drivers, and Verification Checks, execute a `make clean` in their
          directory before rebuilding.  If the specified item is a Test or Model
          which uses a driver, the driver is also cleaned before being rebuilt
          itself.

        -j J

          Number of `make` processes to use when building the item

        -v, --verbose

          Print all cmake/make output while building

    + download

      Usage:

        kimitems download [-h] [-i] [-t TYPE] [-a] [-D] [-x] [-z] search-term

      Retrieves a KIM Item from the official OpenKIM Repository and places the
      archive (.txz format by default) in the current working directory.  Each
      time tab completion is attempted, a query will be performed to
      query.openkim.org to retrieve the list of all fresh Models, Model
      Drivers, Simulator Models, Tests, Test Drivers, and Verification Checks.

      NOTE: In general, the 'install' subcommand of kimitems outlined below is
      preferred over 'download' for retrieving KIM Items, as it automatically
      decompresses them, places them in the appropriate subdirectory of
      ~, and builds them.

      Options
      -------

        -a, --all

          Apply the search criteria to stale items (items which are not the latest
          version in their lineage), as well as fresh items

        -D, --driver

          If given, and if a Test or Model is being downloaded which uses a Test Driver
          or Model Driver, download the driver as well without asking for confirmation.

        -x, --extract

          Decompress the downloaded archive into the current working directory and
          remove the archive itself

        -z, --zip

          Download a .zip archive instead of a .txz

    + install

      Usage:

        kimitems install [-h] [-i] [-t TYPE] [-a] [-D] [-f] [-j J] search-term

      Downloads, builds and installs a KIM Item into the relevant item subdirectory
      of ~.  In the case of Model Drivers, Models, or Simulator Models, this
      will create a 'build' subdirectory inside of the item's directory and
      install the compiled library file to the KIM API user collection.
      Note that each time tab completion is attempted, a query will be performed
      to query.openkim.org to retrieve the list of all fresh Models, Model
      Drivers, Simulator Models, Tests, Test Drivers, and Verification Checks.

      Options
      -------

        -a, --all

          Apply the search criteria to stale items (items which are not the latest
          version in their lineage), as well as fresh items

        -D, --driver

          If the specified item is a Test or Model which uses a driver, also download,
          install, and build it without asking for confirmation.

        -f, --force

          Download, uncompress, and install the specified item into the
          relevant item subdirectory of ~, even if it already exists.  Use with
          caution, as this will obviously overwrite any local changes to the
          item you had! Note that if the specified item is a Test or Model
          which uses a driver and this flag has been given, it does *not*
          forcefully overwrite the driver; if this is desired, either delete
          the driver manually beforehand or call this utility again on the
          driver itself using this flag.

        -j J

          Number of `make` processes to use when building the item

    + search

      Usage:

        kimitems search [-h] [-i] [-t TYPE] [-a] [-d] [-f] [-s] [-v] [-vv] [-vvv] search-term [-se]

      Queries openkim.org for KIM Items matching the search term and prints them to
      the console.

      Options
      -------

        -a, --all

          Apply the search criteria to stale items (items which are not the latest
          version in their lineage), as well as fresh items

        -d, --desc

          Apply the search criteria to the description of KIM Items instead of
          the IDs of the items themselves.  The 'description' of a KIM Item is a
          key stored in its kimspec.edn metadata file.

        -f, --force

          Print all matches for the query without prompting, regardless of how many there
          are

        -s, --species

          Requires that the 'species' key listed for the given item, if it exists,
          contains at least one instance of the specified chemical symbol.

        -se, --species-exclusive

          Requires that the 'species' key listed for the given item, if it exists,
          contains at least one instance of each specified chemical symbol and no others.
          MUST BE GIVEN AFTER PRIMARY SEARCH TERM; multiple species should be separated by
          spaces, e.g. "Al Cu".

        -v, --verbose

          Show descriptions of the KIM Items returned by the search

        -vv, --veryverbose

          Show drivers and descriptions of the KIM Items returned by the search

        -vvv, --veryveryverbose

          Show all information about the KIM Items returned by the search (formatted in JSON)

    + remove

      Usage:

        kimitems remove [-h] [-i] [-t TYPE] [-c] [-D] [-f] search-term
        kimitems remove all

      Remove an item from the relevant item subdirectory of ~.  If the item is
      a Model Driver, Model, or Simulator Model, also delete its library binary
      from the KIM API user collection.  If the special keyword 'all' is given
      as the argument, all items in all of the item subdirectories of ~ will
      be removed and any corresponding Model Drivers, Models, or Simulator
      Models will be removed from the KIM API user collection.

      Options
      -------

        -c, --children

          If a Test Driver or Model Driver is being removed, also remove its children (if any)

        -D, --driver

          If a Test or Model which uses a driver is being removed, also remove
          the driver without asking for confirmation.  This does not circumvent the
          confirmation messages for deleting the item and its driver, which still
          require giving the --force option.

        -f, --force

          Delete the item without asking for confirmation

  B. pipeline-database [-h] {set,delete,import,export,restore,dump,status} <database or database-file>

    Manages the database that is queried by Tests in their pipeline.stdin.tpl
    files.  Select to either use the remote OpenKIM mongo database or a local
    mongo database; when a local database is used, Test Results generated
    using the pipeline-run-* utilities are automatically inserted into it.
    This utility also allows you to:

     (1) clear out the current local database
     (2) import/export a local database using the mongdo db extended json format
     (3) restore/dump a local database using the bson (binary json) format

    The local mongo database is stored at /pipeline/db/ by default

    NOTE: The `kimitems` and `kimgenie` utilities will always perform their queries
          to the remote OpenKIM database, even if you are using a local database.

    Subcommands
    ===========

    + set

      Usage:

        pipeline-database set local
        pipeline-database set remote

      Select whether to use the remote OpenKIM mongo database or a local mongo database.
      Your selection persists across starts/stops of the container.

    + delete

      Usage:

        pipeline-database delete [-f]

      Deletes the local mongo database, which is stored at /pipeline/db/ by default

      Options
      -------

      -f, --force

        Delete the local database without asking for confirmation

    + import

      Usage:

        pipeline-database import database-file

      Import the local mongo database from a mongodb extended json file

    + export

      Usage:

        pipeline-database export database-file

      Export the local mongo database to a mongodb extended json file

    + restore

      Usage:

        pipeline-database restore database-file

      Restore the local mongo database from a bson file

    + dump

      Usage:

        pipeline-database dump database-file

      Dump the local mongo database to a bson file

    + status

      Usage:

        pipeline-database dump database-file

      Report whether remote or local database is being used.  If a local
      database can be found, report its size in human-readable format.

  C. pipeline-find-matches [-a][-m][-v] <Test, Model, Verification Check, or Simulator Model>

    Determines, but does not execute, matches in the local repository for the
    specified KIM Item and prints them to the console.  By default, only the
    matching items are displayed in the following alphanumerically sorted
    format.  If no matches are found, the string "No matches found" will be
    printed.  Wildcard and tab completion is attempted against all items found
    in ~/[tests, models, simulator-models, verification-checks].

    Options:
    ========

      -a, --all

        If this flag is given, the specified item will attempt to match against
        *all* items, including those which are "stale" (i.e. they are not the
        highest version within their lineage in the relevant item subdirectory
        of ~).  For example, supposed you have two Models and a Test in your
        local repository:

          ~
          |-- models
          |   |-- LennardJones__MO_111111111111_000
          |   `-- LennardJones__MO_111111111111_001
          `-- tests
              `-- DimerOscillationFrequency__TE_222222222222_000

        Issuing

          `pipeline-find-matches --all DimerOscillationFrequency__TE_222222222222_000`

        will check to see if DimerOscillationFrequency__TE_222222222222_000
        matches against both LennardJones__MO_111111111111_000 and
        LennardJones__MO_111111111111_001 and print out both results, whereas
        the default behavior is to only check whether
        LennardJones__MO_111111111111_001 matches.  This flag can be combined
        with -m (--mismatch) and -v (--verbose).

      -m, --mismatch

        If given, both matches and mismatches of the given KIM Item will be
        printed to the console in the format:

          MATCHES
          -------

            matching item 1
            matching item 2
            .
            .
            .

          MISMATCHES
          ----------

            mismatch item 1
            mismatch item 2
            .
            .
            .

      -v, --verbose

        This flag has the same effect as -m (--mismatch) mentioned above, but also
        forces additional information to be printed after the 'MATCHES' and
        'MISMATCHES' headers and corresponding lists of items if there are one
        or more mismatches found (which will usually be the case).  This
        additional information consists of the name of each mismatch, followed
        by an explanation of why the items are a mismatch.  Reasons include

          1. a Test or Verification Check contains species which are not
             supported by the Model or Simulator Model (as listed in the
             kimspec.edn of each)
          2. KIM API versions listed in kimspec.edn are incompatible
          3. pipeline API version listed in the kimspec.edn of the Test or
             Verification Check is not compatible with the version of the
             utility stack installed on the VM
          4. the KIM API indicates that the KIM descriptor files of a
             Test-Model pair are incompatible
          5. the 'simulator-name' kimspec.edn key of a Test or Verification
             Check is incompatible with that of a Simulator Model

        In the event that a Test and Model are compatible in the sense of 1-3
        above (that is, they are compatible as far as their kimspec.edn entries
        are concerned), the invocation of the KIM API in step 4 may still
        result in a mismatch.  In this case, the contents of the kim.log file
        produced by the KIM API are also reflected in the output of this
        utility.  Altogether, the format  is as follows:

          MATCHES
          -------

            matching item 1
            matching item 2
            .
            .
            .

          MISMATCHES
          ----------

            mismatch item 1
            mismatch item 2
            .
            .
            .

          MISMATCH INFO
          -------------

          - mismatch item 1

            Message explaining reason for mismatch here.

            kim.log:

              Contents of kim.log here

          - mismatch item 2

            Message explaining reason for mismatch here.

          - mismatch item 3

            Message explaining reason for mismatch here.

        If no mismatches are found, no additional information will be printed.
        Furthermore, if this flag is present, the -a (--all) flag is ignored
        whether it has been given or not.

  D. pipeline-run-matches [-a][-v] <Test, Model, Verification Check, or Simulator Model>

    Runs the specified KIM Item against all compatible matching items found
    under the relevant item subdirectories of ~ which are the highest version
    within their item lineage, i.e. the specified item will run against all
    "fresh" matches.  If a Test or Verification Check is given as the argument,
    it will attempt to run against all matching Models and Simulator Models.
    If a Model or Simulator Model is given as the argument, it will attempt to
    run against all Tests and Verification Checks.  Test Results, Verification
    Results, and Errors produced by running these pairs are placed under
    ~/[test-results, verification-results, errors], respectively.  Note that
    this utility ignores any results or errors that already exist --- it will
    always attempt to run all fresh matches of the specified item.

    Wildcard and tab completion is attempted against all items found in
    ~/[tests, models, simulator-models, verification-checks].

    Options:
    ========

      -a, --all

        If this flag is given, the specified item will be run against *all*
        matching items, including matches which are "stale" (i.e. they are not
        the highest version of their lineage in the relevant item subdirectory
        in ~).  For example, supposed you have two Models and a Test in your
        local repository:

          ~
          |-- models
          |   |-- LennardJones__MO_111111111111_000
          |   `-- LennardJones__MO_111111111111_001
          `-- tests
              `-- DimerOscillationFrequency__TE_222222222222_000

        Issuing

          `pipeline-run-matches --all DimerOscillationFrequency__TE_222222222222_000`

        will force the Test to be run against both LennardJones__MO_111111111111_000
        and LennardJones__MO_111111111111_001, whereas the default behavior is
        to run against only LennardJones__MO_111111111111_001.

      -v, --verbose

        If given, this forces the stdout and stderr streams for a job to be
        printed to the console while it is running.  Even if this flag is
        given, these streams will also be written to the  pipeline.stdout and
        pipeline.stderr files that always accompany a Test Result, Verification
        Result, or Error.

  E. pipeline-run-pair [-i] <Test or Verification Check> <Model or Simulator Model>

    Attempt to run a specific Test or Verification Check with a specific Model
    or Simulator Model.  If the specified pair is not a match, an error message
    will be printed to the console.  Like `pipeline-run-matches`, this utility
    ignores whether a result or error for the specified pair already exists
    under ~/[test-results, verification-results, errors].

    Wildcard and tab completion on the first argument is attempted against all
    items found in ~/[tests, verification-checks], while completion for the
    second argument is attempted against all items found in ~/[models,
    simulator-models].  In the event that wildcards are used in both arguments,
    all pairwise combinations of the corresponding matches are attempted.

    Options:
    ========

      -v, --verbose

        If given, this forces the stdout and stderr streams for a job to be
        printed to the console while it is running.  Even if this flag is
        given, these streams will also be written to the  pipeline.stdout and
        pipeline.stderr files that always accompany a Test Result, Verification
        Result, or Error.

      -i, --inplace

        Run the given pair in the Test or Verification Check's absolute
        directory instead of creating a temporary working directory and copying
        the results to one of ~/[test-results,verification-results,errors].  If
        you are using a local database (see `pipeline-database` command), any
        Test Results generated using this option will *not* be inserted into it.

  F. pipeline-run-tests [-a][-v] <Model or Simulator Model>

    Attempt to run all of the Tests in ~/tests/ against the specified Model or
    Simulator Model.

    Wildcard completion is attempted against all items found in ~/[models,
    simulator-models].

    Options:
    ========

      --all

        Same meaning as in `pipeline-run-matches`.  If this flag is given, the
        specified item will be run against *all* Tests, including those which
        are "stale" (i.e. they are not the highest version within their lineage
        in the relevant item subdirectory of ~).

      -v, --verbose

        Same meaning as in `pipeline-run-matches`.  This forces the stdout and
        stderr streams of the job to be written to the console while it is
        running.

  G. pipeline-run-verification-checks [-a][-v] <Model or Simulator Model>

    Attempt to run all of the Verification Checks in ~/verification-checks/
    against the specified Model or Simulator Model.

    Wildcard completion is attempted against all items found in ~/[models,
    simulator-models].

    Options:
    ========

      --all

        Same meaning as in `pipeline-run-matches`.  If this flag is given, the
        specified item will be run against *all* verification checks, including
        those which are "stale" (i.e. they are not the highest version within
        their lineage in the relevant item subdirectory of ~).

      -v, --verbose

        Same meaning as in `pipeline-run-matches`.  This forces the stdout and
        stderr streams of the job to be written to the console while it is
        running.

  H. kimgenie

    Generate a set of Tests or Reference Data based on a set of template files.
    See the output of `kimgenie -h` for a description of how this tool works.

    Usage:

      kimgenie [-h] {tests,ref-data} ...

      Arguments and options vary depending on which subcommand ('tests' or 'ref-data').

    Examples:

      kimgenie tests --test-driver LatticeConstantCubicEnergy__TD_475411767977_007
      kimgenie ref-data ~/my_refdata_templating_root_dir/

    Options
    =======

      The following options can be used with either `kimgenie` subcommand:

      --add-random-kimnums

        Use randomly generated kimid numbers, provided as Jinja key 'kimnum'.
        Using this flag means that the generator file you provide will be
        OVERWRITTEN with one in which a 'kimnum' key (with a random kimcode as
        its corresponding value) is added to each dictionary contained within.
        Before this alteration is made, a check is performed to determine if
        there is already a 'kimnum' key present in any of the dictionaries in
        the generator file and, if so, the entire item generation process is
        aborted and your generator file will not be overwritten.

      --destination DESTINATION

        Destination directory for generated items.  When using the 'tests'
        subcommand, the default is ~/tests/; when using the 'ref-data'
        subcommand, the default is ~/reference-data/.

      --dry-run

        Don't actually create the items, but rather just show what would be
        generated.

      --filename-extension FILENAME_EXTENSION

        Only files with the specified extension are included in the rendered
        item directories.

      --filename-prefix FILENAME_PREFIX

        Only files with the specified prefix are included in the rendered
        item directories.

      --generator-file GENERATOR_FILE

        A file where each line is a JSON-formatted dictionary used to create a
        template variable namespace to apply to the files in the template file
        directory in order to generate an item.  When using the 'tests'
        subcommand, the default is test_generator.json; when using the
        'ref-data' subcommand, the default is refdata_generator.json.

      --global-variables GLOBAL_VARIABLES

        Additional JSON-formatted dictionary of global variables, as file or string

      --log-file LOG_FILE

        Name of file to write logs to. If left unspecified, logs are not
        written (although the list of generated items is still printed to the
        terminal).

      --overwrite

        Overwrite any existing item directories which already exist at the
        locations where the Tests being generated are trying to be written to.
        Use with caution!

      --template-dir TEMPLATE_DIR

        Directory containing the template files.  When using the 'tests'
        subcommand, the default is test_template; when using the 'ref-data'
        subcommand, the default refdata_template.

      -v, --verbose

        Show debugging messages and timestamps in log

      --version VERSION

        Used to define the 'version' variable in the template variable
        namespace.  Although this option is an integer, it will be cast to a
        three-character string, e.g. a value of 1 is mapped to string '001'.

    Subcommands
    ===========

    + tests

      Usage:

        kimgenie tests [-h] [--add-random-kimnums] [--dry-run]
                       [--filename-extension FILENAME_EXTENSION] [--filename-prefix FILENAME_PREFIX]
                       [--global-variables GLOBAL_VARIABLES] [--log-file LOG_FILE] [--overwrite] [-v]
                       [--version VERSION] [--destination DESTINATION]
                       [--generator-file GENERATOR_FILE] [--root-dir ROOT_DIR]
                       [--template-dir TEMPLATE_DIR] [--test-driver TEST_DRIVER]

      Generates tests from a generator file and template file directory.

      Options
      -------

        --root-dir

          The directory that contains the template file directory and generator
          file.  Either this option must be supplied or the 'test-driver'
          option must be supplied.

        --test-driver

          Extended KIM ID of the Test Driver whose Tests you wish to generate.
          Either this option or the 'root-dir' option should be given.  If this
          option is specified, the corresponding Test Driver directory must
          exist under ~/test-drivers/.

    + ref-data

      Usage:

        kimgenie ref-data [-h] [--add-random-kimnums] [--dry-run]
                          [--filename-extension FILENAME_EXTENSION]
                          [--filename-prefix FILENAME_PREFIX] [--global-variables GLOBAL_VARIABLES]
                          [--log-file LOG_FILE] [--overwrite] [-v] [--version VERSION]
                          [--destination DESTINATION] [--generator-file GENERATOR_FILE]
                          [--template-dir TEMPLATE_DIR]
                          root-dir

      Generates reference data from a generator file and template file
      directory.  No additional options are offered beyond those given above.