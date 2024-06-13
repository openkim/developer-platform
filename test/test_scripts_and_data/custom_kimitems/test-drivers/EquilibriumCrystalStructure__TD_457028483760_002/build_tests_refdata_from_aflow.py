#!/usr/bin/env python3

"""
This script builds tests for the EquilibriumCrystalStructure test driver by pulling compounds from AFLOW. It also generates KIM reference data items containing a single instance each of the ``binding-energy-crystal`` and ``crystal-structure-npt`` properties. If you have the Sphinx documentation built, see also :ref:`doc.testgen`.

Before running this script, the following data files must be created:
    1) ``[work_dir]/species_combos_[threadnum].txt``, where :data:`work_dir` and :data:`threadnum` are passed through ``stdin`` (see below). Each line should be a list of comma-separated chemical species in square brackets, e.g. ``[Al,Cu]`` or ``[Si]``. Tests and/or reference data will be built strictly for each set of species in the file.
    2) (Only if :data:`build_refdata` is set) ``taken_rd_kimnums.json`` in the directory the script is invoked from. This file can be generated using ``scripts/get_taken_rd_kimnums.py``. This file should contain a list of KIM numbers that have already been used for reference data items to avoid collisions. Additionally, the script will not duplicate any reference data numbers that are present in the ``Refdata`` directory if it exists. Because tests are much less numerous than reference data, collisions are unlikely (<0.1% chance for any pair out of 40,000 tests to collide) and no such checks are made for tests.

This script takes a number of inputs from ``stdin``. An example input file that can be piped in, ``build_example.in``, is provided. 

Of special interest are options :data:`write_files` and :data:`read_files`. If :data:`write_files` is set to 1, the script will carry out the initial tasks requiring an Internet connection and write the files, then exit without processing. If :data:`read_files` is set to 1, the script will not perform any of the tasks requiring an Internet connection, and expect the files to already exist. Writing the files is much faster, so if there is a lot of data to process, one can e.g. write the files on a local machine and then copy them to a cluster to run the processing. The :data:`threadnum` parameter is used to avoid filename conflicts when running multiple instances of this script. To facilitate this mode of operation, ``scripts/get_species_combos.py`` will generate ``species_combos_[threadnum].txt`` files, as well as two corresponding input files -- ``download[threadnum].in`` and ``process[threadnum].in``, for a requested number of threads. These contain all the species combinations up to the requested arity that OpenKIM has potentials for, approximately load balanced.

Inputs read from ``stdin``
==========================

.. data:: build_tests
    
    Build tests (1) or not (0)

    :type: int

.. data:: build_refdata
    
    Build reference data (1) or not (0)

    :type: int

.. data:: icsd
    
    Restrict AFLUX search to ICSD database (1) or not (0)

    :type: int

.. data:: write_files
    
    Carry out the initial tasks requiring an Internet connection and write the files, then exit without processing (1) or not (0). This is useful if you intend to run on a cluster without Internet access. Run with this option enabled first to download the files you need (fast), copy them to the cluster and then run there with this option disabled  and :data:`read_files` enabled to process the files (slow)

    :type: int

.. data:: read_files
    
    Do not perform any of the tasks requiring an Internet connection, and expect the files to already exist (1) or not (0). See :data:`write_files`.

    :type: int
    
.. data:: threadnum
    
    Numerical suffix for ``species_combos...`` input file and working directory name, for avoiding filename conflicts when running multiple instances of this script

    :type: int

.. data:: hyperparams_list
    
    Space-separated list of hyperparameters to request from AFLUX for characterizing the reference data

    :type: list[str]

.. data:: kim_user_id
    
    Your KIM user ID (long string of numbers and characters with several hyphens). This is used to set the ``contributor`` and ``maintainer`` fields in the ``kimspec.edn`` files for generated tests and reference data

    :type: str

.. data:: aflow_version
    
    Version of AFLOW used for symmetry detection. Can be left blank to be auto-detected

    :type: str

.. data:: num_threads
    
    The number to pass to the aflow executable for the np= argument (leave blank for np=1)

    :type: int

.. data:: work_dir

    Path to parent working directory. The ``species_combos_...`` files will be read from here, and the working directories for each :data:`threadnum` will be created here


Overview of operation:
======================

First, housekeeping is performed such as reading the above input, creating directories and reading data files. Then, the main loop over species combinations is run:

Main loop, one iteration for each species combination:
------------------------------------------------------

1) Create working subdirectory for this :data:`threadnum` and species combination, e.g. ``work_dir/data_dir0/OSi``
2) If :data:`read_files` is not set:

    i. Call :func:`query_aflux` to query the AFLOW AFLUX web API for all materials for the specified combination of species and remove entries with excessive stress.
    ii. Call :func:`download_contcars` to download the relaxed geometries of each material using the ``aurl`` field of each material returned by the AFLUX query
    iii. If :data:`write_files` is set, write ``aflux_response.json`` and continue to next species combination

3) If :data:`read_files` is set, read the previously saved ``aflux_response.json``
4) If :data:`build_refdata` is set, initialize the :class:`Genie_data` object with the old reference data generator file, if any. The old generator is backed up (an indefinite chain of old files is kept, named .old0, .old1, etc.)
5) For each downloaded geometry:

    i. Obtain the :ref:`doc.appendices.aflowproto` using :func:`~crystal_genome_util.aflow_util.AFLOW.get_prototype`
    ii. Obtain the closest matching (if any) :ref:`doc.appendices.aflowlibproto` and its human-readable shortname using :func:`~crystal_genome_util.aflow_util.AFLOW.get_library_prototype_label_and_shortname`
    iii. If :data:`build_refdata` is set, call :func:`Genie_data.add` for this material. If the material is not a duplicate of an old entry, its validity is checked using :func:`~crystal_genome_util.property_util.equilibrium_crystal_structure.validate_binding_energy_crystal` and :func:`~crystal_genome_util.property_util.equilibrium_crystal_structure.validate_crystal_structure_npt`, then it is added to :attr:`Genie_data.genie_data` and its ``data.edn`` file is written.

6) If :data:`build_refdata` is set, write the reference data generators using :func:`Genie_data.write`
7) If :data:`build_tests` is set:

    i. Use :func:`~crystal_genome_util.aflow_util.AFLOW.compare_materials_dir` to use the AFLOW command line tool to identify groups of duplicate materials among the downloaded geometries
    ii. Initialize the :class:`Genie_tests` object with the old test generator file, if any. The old generator is backed up.
    iii. For each group of duplicate materials:

        a) If *any* auid is present in the old generators, move on to the next group (each test generator contains a list auids for all known duplicate materials specifically for this deduplication purpose)
        b) Loop over the group, calling :func:`~crystal_genome_util.aflow_util.AFLOW.build_atoms_from_prototype`. This is the same function is used by :mod:`runner` to build the :class:`ase.atoms.Atoms` object, and raises exceptions if problems arise. When a material that successfully runs this function is found, call :func:`Genie_tests.add` and move on the the next group. The list of auids written for this material is arranged such that the actual geometry used for the test is the first in the list.

    iv. Sort the tests using :func:`Genie_tests.sort` and write them using :func:`Genie_tests.write`

Members
=======
"""

import json
import os
import random
from typing import Dict, List, Set, Tuple, Union
import numpy as np
import requests
import shutil
import datetime
from kim_property import kim_property_dump
import crystal_genome_util.aflow_util as aflow_util
from crystal_genome_util.property_util.equilibrium_crystal_structure import add_property_inst, validate_binding_energy_crystal, validate_crystal_structure_npt

AFLOW_REQUIRED_KEYS = ["energy_atom","stress_tensor","aurl","auid"]
ABSMAX_STRESS_COMPONENT=10.
CONTCARS_SUBDIR = "contcars"
TEST_GENERATORS_DIR = "alloy_test_generators"
REFDATA_GENERATORS_DIR = "alloy_refdata_generators"
REFDATA_DIR = "Refdata"
DATA_DIR_PREFIX = "data_dir"
AFLUX_FILENAME = "aflux_response.json"
KIMNUMS_FILENAME = "taken_rd_kimnums.json"

class NumpyEncoder(json.JSONEncoder):
    """
    Encode numpy arrays as lists for JSON serialization
    """
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def input_to_int(prompt: str = "") -> int:
    """
    Prompt for input, split on # to allow for comments, strip and return first element
    """    
    return int(input(prompt+"\n").split("#")[0].strip())

def input_to_str(prompt: str = "") -> str:
    """
    Prompt for input, split on # to allow for comments, strip and return first element
    """    
    return input(prompt+"\n").split("#")[0].strip()

def input_to_list_of_str(prompt: str = "") -> List[str]:
    """
    Prompt for input, split on # to allow for comments, strip and return first element
    """    
    return input(prompt+"\n").split("#")[0].strip().split()

def aurl_to_contcar_relax_vasp_url(aurl: str) -> str:
    """
    Convert aurl (AFLOW URL) of the structure to the Web URL of the CONTCAR.relax.vasp file
    """
    return 'http://'+aurl.replace(':','/',1)+'/CONTCAR.relax.vasp'

def get_random_kim_id(taken_kimnums: Set = set(), existing_kimnums_dir: Union[str,None] = None) -> str:
    """
    Returns random 12-digit numerical string that is not in taken_kimnums and does not exist as a subdirectory of existing_kimnums_dir

    Args:
        taken_kimnums:
            A set of 12-digit numerical strings that should not be repeated
        existing_kimnums_dir:
            Path to a directory containing subdirectories with 12-digit numeric names, not to be repeated
    
    Returns:
        Non-duplicate random 12-digit numerical string
    """
    candidate_kimnum = "".join(["{}".format(random.randint(0, 9)) for num in range(12)])        
    if ((candidate_kimnum in taken_kimnums) or ((existing_kimnums_dir is not None) and (os.path.isdir(os.path.join(existing_kimnums_dir,candidate_kimnum))))):
        return get_random_kim_id(taken_kimnums,existing_kimnums_dir)
    else:
        return candidate_kimnum

def erase_and_remake_dir(dir):
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    os.mkdir(dir)

def read_existing_generators(generator_file: str,make_backup: bool=True) -> List:
    """
    Read existing generator dictionaries from file. Each line of the file is expected to be a JSON dictionary.
    
    Args:
        generator_file: path to file containing existing test generators
        make_backup: if true, the original file is renamed to generator_file+".old[n]" (where n is chosen not to overwrite previous backups) after reading
    Returns:
        List of dicts containing test or refdata generators
    """
    generator_file_dicts = []
    if os.path.exists(generator_file):        
        with open(generator_file, encoding="utf-8") as f:
            for line in f:
                this_dict = json.loads(line)
                generator_file_dicts.append(this_dict)
        if make_backup:
            def recursive_backup_filename(filename,index=0):
                backup_filename = filename+".old"+str(index)
                if os.path.exists(backup_filename):
                    return recursive_backup_filename(filename,index+1)
                else:
                    return backup_filename
            os.rename(generator_file,recursive_backup_filename(generator_file))
    return generator_file_dicts

class Genie_tests:
    """
    Class containing a list of dicts, each corresponding to a test generator to be read and rendered into a template by the ``kimgenie`` utility

    Attributes:
        genie_tests (List[Dict]):
            List of JSON dictionaries containing the test generator to be output. Only new tests or version updates to existing tests are put here.
        genie_tests_old (List[Dict]): 
            List of JSON dictionaries containing the test generators read from an existing file. 
            If this is provided, then materials can be checked using :func:`is_duplicate`
            

    """
    def __init__(self, generator_file:str=""):
        """
        Args:
            generator_file: path to file containing existing test generators to be read into :attr:`genie_tests_old`, if any
        """
        self.genie_tests = []
        if generator_file=="":
            self.genie_tests_old = []
        else:
            self.genie_tests_old = read_existing_generators(generator_file)

    def is_duplicate(self,auids:List[str])->bool:
        """
        Check if *any* of the ``auids`` are already present in the ``auids`` field of any parameter set of *any* old test
        
        """
        for genie_test_old in self.genie_tests_old:    
            for parameter_set in genie_test_old["parameter_sets"]:                    
                if any (auid_old == auid_new for auid_old in parameter_set["auids"] for auid_new in auids):                    
                    return True
        return False

    def add(self, species: List[str], proto_des: Dict, libproto_shortname: Tuple, auids: List[str], aurl: str, kim_user_id: str):        
        """
        Add a parameter set. If a test with matching prototype label is found in :attr:`genie_tests`, a new parameter set is added to that test. If not, but a matching prototype label is found in :attr:`genie_tests_old`, the old test is duplicated, its version number is incremented and a new parameter set is added to the new test. If neither of these is true, a new test is created with version 000.

        Args:
            species:
                Stoichiometric species, e.g. ``['Mo','S']`` corresponding to A and B respectively for prototype label AB2_hP6_194_c_f indicating molybdenite
            proto_des:
                Prototype designation returned by aflow --prototype command
            libproto_shortname:
                AFLOW library prototype and shortname
            auids:
                List of auids, first one is the actual structure, rest are duplicates to be saved for deduplication of new tests
            aurl:
                AFLOWLIB uniform resource locator
            kim_user_id:
                For maintainer-id and contributor-id in kimspec.edn
        """

        prototype_label = proto_des["aflow_prototype_label"]
        parameter_values = proto_des["aflow_prototype_params_values"]
        
        # variable to keep track of where this material should go in the list of tests or "None" if it's a new test
        test_index_where_this_material_goes = None
        for i in range(len(self.genie_tests)):        
            if self.genie_tests[i]["prototype_label"] == prototype_label: 
                # this means we've already decided we're building a test for this. Might be brand new or an update
                test_index_where_this_material_goes = i
                break

        # Don't have a place to put this yet, check to see if the prototype label already exists in the old list of tests
        # NOTE: No deduplication check here, assume it's already been done
        if test_index_where_this_material_goes is None:
            for genie_test_old in self.genie_tests_old:
                if genie_test_old["prototype_label"] == prototype_label:
                        # we found the prototype label, and we do not have a test already for this material. 
                        # This means we are upversioning this test and adding at least one new parameter set to it.
                        genie_test_old["version"] = str(int(genie_test_old["version"])+1).rjust(3,'0')                                            
                        # Append the upversioned test to the new list of tests and break out of the loop
                        test_index_where_this_material_goes = len(self.genie_tests)
                        self.genie_tests.append(genie_test_old)
                        break
                        
        parameter_names = proto_des["aflow_prototype_params_list"]        
        # We are creating a new test on this call
        if test_index_where_this_material_goes == None: 
            test_index_where_this_material_goes = len(self.genie_tests)
            self.genie_tests.append(
                {
                    "species": species,
                    "prototype_label": prototype_label,
                    "parameter_names": parameter_names,
                    "modeltype": "standard",
                    "version": "000",
                    "kimnum": get_random_kim_id(), 
                    "num_param_sets": "0",
                    "parameter_sets": [],
                }           
            )            
            
        # We are about to add a parameter set, increment num_param_sets
        self.genie_tests[test_index_where_this_material_goes]["num_param_sets"] = str(int(self.genie_tests[test_index_where_this_material_goes]["num_param_sets"])+1)
        # add the maintainer and contributor -- we do this now because it could be a change in maintainer/contributor-ship from the old test, or a new test
        self.genie_tests[test_index_where_this_material_goes]["kim_user_id"] = kim_user_id
        # add the parameter set 
        self.genie_tests[test_index_where_this_material_goes]["parameter_sets"].append(
            {
                "library_prototype_label": libproto_shortname[0],
                "short_name": libproto_shortname[1],
                "parameter_values": parameter_values,
                "auids": auids,
                "url": aurl_to_contcar_relax_vasp_url(aurl)
            }
            )
            
    def sort(self):
        """
        Sort the tests by their prototype labels
        """
        self.genie_tests = sorted(
            self.genie_tests,
            key=lambda d: (
                d["prototype_label"].split("_")[0],
                d["prototype_label"].split("_")[1],
                int(d["prototype_label"].split("_")[2]),
                d["prototype_label"].split("_")[3],
            ),
        )

    def write(self, new_generator_file:str="test_generator_new.json"):
        """
        Write out test generator file
        """
        with open(new_generator_file, "w") as f:
            for test in self.genie_tests:
                f.write(json.dumps(test,cls=NumpyEncoder) + "\n")

class Genie_data:   

    """
    Class containing a list of dicts, each corresponding to a refdata generator to be read by the ``kimgenie`` utility

    Attributes:
        genie_data (List[Dict]):
            List of JSON dictionaries containing the reference data generators to be output. Only new reference data  are put here
        genie_data_old (List[Dict]): 
            List of JSON dictionaries containing the reference data generators read from an existing file. 
            If this is provided, then new materials passed to  :func:`add` are first checked for duplicates against :attr:`genie_data_old` before being added to :attr:`genie_data`
        taken_kimnums (Set[str]):
            Set of 12-digit KIM IDs already attributed to reference data in the openkim.org repository
            

    """
    def __init__(self, generator_file:str="", taken_kimnums:Set[str]=set()):
        """
        Args:
            generator_file: path to file containing existing data generators to be read into :attr:`genie_data_old`, if any
            taken_kimnums: already-taken KIM numbers
        """
        self.genie_data = []
        if generator_file=="":
            self.genie_data_old = []
        else:
            self.genie_data_old = read_existing_generators(generator_file)

        self.taken_kimnums = taken_kimnums

    def add(
            self,hyperparams_list: List[str],aflow_version: str,kim_user_id: str,aflux_entry: Dict,proto_des: Dict, libproto: str, shortname: str
        ):        
        """
        Adds a kimgenie generator dictionary for a piece of reference data to :attr:`genie_data` if it does not already exist in :attr:`genie_data_old`

        Args:
            hyperparams_list:
                DFT hyperparameters that were queried for, so they can be put in the description in kimspec.edn
            aflow_version:
                For content-origin in kimspec.edn
            kim_user_id:
                For maintainer-id and contributor-id in kimspec.edn
            aflux_entry:
                Entry for this material returned by the AFLUX query
            proto_des:
                AFLOW prototype designation
            libproto:
                AFLOW library prototype
            shortname:
                Material shortname
        """

        species = aflux_entry["species"]
        prototype_label = proto_des["aflow_prototype_label"]

        # check for duplicates
        auid = aflux_entry["auid"]
        for entry in self.genie_data_old:
            if auid == entry["auid"]:
                print("Not adding %s to new generator because it was found in the old one"%auid)
                return
         
        
        # process info that will go into generator dict for kimspec.edn
        hyperparams_dict = {}
        for hyperparam in hyperparams_list:
            hyperparams_dict[hyperparam]=aflux_entry[hyperparam]
        url = aurl_to_contcar_relax_vasp_url(aflux_entry["aurl"])
        kimnum = get_random_kim_id(self.taken_kimnums,REFDATA_DIR)
        today = datetime.date.today()
        data_dir = os.path.join(REFDATA_DIR,kimnum)
        os.mkdir(data_dir) # if dir exists this will throw an error -- good
        data_file = os.path.join(data_dir,"data.edn")
        try:
            print("Adding reference data for %s"%auid)
            property_inst = add_property_inst(aflux_entry["energy_atom"],species,proto_des,libproto,shortname)
            validate_crystal_structure_npt(property_inst)
            validate_binding_energy_crystal(property_inst)
            with open(data_file,"w") as fp:
                kim_property_dump(property_inst,fp)
        except Exception as e:
            print("Skipping this material due to failure to add or validate property instance:\n%s"%e)
            return

        self.genie_data.append(
            {
                "species": species,
                "prototype_label": prototype_label,
                "library_prototype_label": libproto,
                "short_name": shortname,
                "hyperparams_dict": hyperparams_dict,
                "aflow_version": aflow_version,
                "auid": auid,
                "url": url,
                "kimnum": kimnum,
                "kim_user_id": kim_user_id,
                "access_year": str(today.year),
                "access_date": str(today.month)+"-"+str(today.day),
                "FILES_TO_COPY": [data_file]
            }           
        )

    def write(self, new_generator_file:str="data_generator_new.json"):
        """
        Write out data generator file
        """
        with open(new_generator_file, "w") as f:
            for data in self.genie_data:
                f.write(json.dumps(data) + "\n")

def send_aflow_query(params):
    """
    Send query to AFLOW
    """
    url = "http://aflow.org/API/aflux/"
    url += "?" + ",".join([str(param) for param in params])
    return requests.post(url).json()

def query_aflux(species_list: List[str], aflow_keys: List[str], icsd: bool = False, absmax_stress_component: float=10.) -> List[Dict]:
    """
    Query AFLOW to obtain all compounds for the provided list of elements.

    Args:
        species_list:
            List of chemical elements in the compound. Only compounds that
            have all of these elements and no additional ones are returned.
        aflow_keys:
            List of AFLOW keywords for properties to be returned.
        icsd:
            Whether to restrict the search to the ICSD database
        absmax_stress_component:
            After querying, remove any materials with stress components exceeding this absolute value
            
    Returns:    
        For each compound, a dictionary of the returned properties.
    """
    assert "stress_tensor" in aflow_keys, "ERROR: must include stress_tensor in aflow_keys"
    assert absmax_stress_component >= 0, "ERROR: absmax_stress_component must be non-negative"

    def format_filter_params_to_list(filter_params):
        return [key + "(" + str(val) + ")" for key, val in filter_params.items()]

    filter_params = {"species": ",".join(species_list), "$nspecies": len(species_list), "$paging": 0}
    if icsd:
        filter_params["catalog"]="icsd"
    select_params = aflow_keys
    params = format_filter_params_to_list(filter_params) + select_params
    query_result = send_aflow_query(params)
    filtered_query_result=[]
    for entry in query_result:
        if (max(abs(float(n)) for n in entry["stress_tensor"]) < absmax_stress_component):
                filtered_query_result.append(entry)
    return filtered_query_result

def download_contcars(aflux_response: List[Dict], destination_dir: str):
    """
    Download CONTCAR.relax files from each simulation found by the AFLUX query    
    """

    for (i,material) in enumerate(aflux_response):
        url = aurl_to_contcar_relax_vasp_url(material['aurl'])
        with open(os.path.join(destination_dir,str(i)),"w") as f:
            contcar = requests.get(url)
            f.write(contcar.text)

if __name__ == "__main__":

    build_tests = input_to_int("Build tests?")
    build_refdata = input_to_int("Build reference data?")
    icsd = input_to_int("Restrict to ICSD?")
    write_files = input_to_int("Only write AFLUX query and files, don't process?")
    read_files = input_to_int("Don't query and download files, expect them to exist already?")
    threadnum = input_to_int("Thread number?")
    hyperparams_list = input_to_list_of_str("Space-separated list of hyperparameters to request from AFLOW")
    kim_user_id = input_to_str("OpenKIM User ID?")
    aflow_version = input_to_str("AFLOW version?")
    num_threads = input_to_str("Number of threads for aflow++?\n")
    work_dir = input_to_str("Working directory?\n")
    
    # TODO: There is considerable speedup possible if tests are being built but not reference data (possibly in other scenarios),
    # but it would require complicated flow control.

    # postprocess input
    if icsd: 
        print("Restricting seach to ICSD database\n")
    if write_files:
        assert not read_files, 'ERROR: Why would we read files if we are writing them'
    if num_threads.strip() == "":
        num_threads = 1
    else:
        num_threads = int(num_threads)
    # Get dictionary of shortnames for prototype labels
    shortnames = aflow_util.read_shortnames()
    # Read species combos we will be querying and/or processing
    species_combo_file = work_dir+"/species_combos_%d.txt" % threadnum
    species_combinations = []
    with open(species_combo_file, 'r') as f:
        for line in f:
            species_combinations.append(eval(line))
    print("Read {} species combinations from file.".format(len(species_combinations)))
    
    # initial setup for getting data from Internet, or for that data to already exist
    data_dir = os.path.join(work_dir,DATA_DIR_PREFIX+str(threadnum))
    if not read_files:
        # List of properties to be requested in AFLOW queries -- these will be in every representative and duplicate structure       
        print ("Removing compounds with stress > " +str(ABSMAX_STRESS_COMPONENT)+" kbar")
        aflow_keys = AFLOW_REQUIRED_KEYS+hyperparams_list
        erase_and_remake_dir(data_dir)
    else: # we won't be querying or downloading CONTCARS, work_dir should already exist
        assert os.path.isdir(data_dir), "ERROR: Data directory %s does not exist" % data_dir

    if build_refdata:
        with open(KIMNUMS_FILENAME) as f:
            taken_kimnums = set(json.load(f))

    # AFLOW object, stores working directory and number of threads to use for aflow++
    aflow = aflow_util.AFLOW(aflow_work_dir=data_dir,np=num_threads)
    if aflow_version.strip() == "":        
        aflow_version = aflow.get_aflow_version()

    # Set up directories for generators and reference data
    if build_tests and not os.path.isdir(TEST_GENERATORS_DIR):
        os.mkdir(TEST_GENERATORS_DIR)
    if build_refdata and not os.path.isdir(REFDATA_GENERATORS_DIR):
        os.mkdir(REFDATA_GENERATORS_DIR)
    if build_refdata and not os.path.isdir(REFDATA_DIR):
        os.mkdir(REFDATA_DIR)
    
    # Main loop over species combinations
    for species_combo in species_combinations:
        # Should already be sorted alphabetically, but sort just in case
        species_combo.sort()
        species_combo_name = "".join(species_combo)

        #define paths
        species_work_dir = os.path.join(data_dir,species_combo_name)
        aflux_file_path = os.path.join(species_work_dir,AFLUX_FILENAME)        
        species_contcars_dir = os.path.join(species_work_dir,CONTCARS_SUBDIR)
        species_contcars_subdir = os.path.join(species_combo_name,CONTCARS_SUBDIR) #subdirectory relative to top-level work directory

        # Get the AFLUX query response from the Internet or from a previously saved file
        if not read_files:            
            os.mkdir(species_work_dir) # No checks, this shouldn't exist as we deleted and re-made the top-level work dir
            print("Querying AFLUX for..." + species_combo_name)
            aflux_response = query_aflux(species_combo, aflow_keys, icsd, ABSMAX_STRESS_COMPONENT)
            if write_files:
                with open(aflux_file_path,"w") as f:
                    json.dump(aflux_response,f)
        else:
            with open(aflux_file_path,"r") as f:
                aflux_response = json.load(f)

        if not aflux_response: # response was empty
            print("No compounds returned by AFLUX for "+species_combo_name)
            continue            
        num_materials = len(aflux_response)

        if not read_files:
            # download coordinate files for structures found by AFLUX
            print("Got AFLUX response, downloading files...")        
            erase_and_remake_dir(species_contcars_dir)
            download_contcars(aflux_response,species_contcars_dir)

        if write_files:            
            print("Finished writing files")
            continue

        # determine prototype designation and library prototype/shortname (if any) for each structure
        # TODO: make this more efficient if possible: right now symmetry detection happens 4 times: libproto, proto, comparison, and sgdata
        list_of_libproto_shortname_tuples = []
        list_of_proto_des = []
        print("\nDetecting prototypes "+("and generating reference data " if build_refdata else "") +  "for %s..."%species_combo_name)
        if build_refdata:
            refdata_path = os.path.join(REFDATA_GENERATORS_DIR,"data_generator_%s.json" % species_combo_name)
            genie_data = Genie_data(refdata_path,taken_kimnums)
        for i in range(num_materials):
            # TODO: if we build_tests only, we don't need this for every material, only representative ones
            filepath = os.path.join(species_contcars_subdir,str(i)) #relative to top-level work dir
            list_of_proto_des.append(aflow.get_prototype(filepath))
            list_of_libproto_shortname_tuples.append(aflow.get_library_prototype_label_and_shortname(filepath,shortnames))
            if build_refdata:
                genie_data.add(
                    hyperparams_list,aflow_version,kim_user_id,aflux_response[i],list_of_proto_des[i],list_of_libproto_shortname_tuples[i][0],list_of_libproto_shortname_tuples[i][1])
        if build_refdata:
            genie_data.write(refdata_path)            
            
        if build_tests:            
            # for tests, we only use AFLOW materials as initial guesses for coords. So we deduplicate similar coord sets using a material comparison
            print("\nPerforming material comparison for %s..."%species_combo_name)
            comparison_result = aflow.compare_materials_dir(species_contcars_subdir)                        
            print("Adding test generators...")
            genie_tests = Genie_tests(os.path.join(TEST_GENERATORS_DIR,"test_generator_%s.json" % species_combo_name))            
            for material_group in comparison_result:
                # There's nothing special about the structure chosen as representative, so concatenate them all together
                materials = [material_group["structure_representative"]]+material_group["structures_duplicate"]
                # Indices of this material group into the AFLUX response list
                material_indices = [int(material["name"].split("/")[-1]) for material in materials]
                auids = [aflux_response[i]["auid"] for i in material_indices]
                if genie_tests.is_duplicate(auids):
                    print("At least one of the following materials existed in the old tests, skipping this group: "+str(auids))
                else:
                    successfully_added_test = False
                    for i in material_indices:
                        # We will save this entire list of auids with the test generator for deduplication when generating new tests.
                        # We re-make it before every attempt to add a test because we always want the first auid to correspond to the material we actually wrote.
                        auids = [aflux_response[i]["auid"]]
                        for j in material_indices:
                            if j != i:
                                auids.append(aflux_response[j]["auid"])
                                
                        print ("Building test from "+auids[0])
                        try:
                            aflow.build_atoms_from_prototype(
                                species_combo,list_of_proto_des[i]["aflow_prototype_label"],list_of_proto_des[i]["aflow_prototype_params_values"],False
                                )
                        except (aflow.tooSymmetricException,aflow.incorrectNumAtomsException,aflow.failedRefineSymmetryException,aflow.incorrectSpaceGroupException) as e:
                            print("Failed to build test due to the following exception:")
                            print(e)
                            continue
                        genie_tests.add(species_combo,list_of_proto_des[i],list_of_libproto_shortname_tuples[i],auids,aflux_response[i]["aurl"],kim_user_id)     
                        successfully_added_test = True    
                        break
                    # only here if we didn't find a single valid duplicate
                    if not successfully_added_test:
                        # because we didn't find a suitable material, the first auid in the list is the representative material
                        print(
                            "WARNING: Failed to build a test from any of the following duplicate materials: "+str(auids))
                    
            genie_tests.sort()
            genie_tests.write(os.path.join(TEST_GENERATORS_DIR,"test_generator_%s.json" % species_combo_name))

