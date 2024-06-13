#!/usr/bin/env python3
"""
Get all species combinations that OpenKIM has potentials for up to a given number of species. Split it into a requested number of chunks for parallel processing. The chunks are load balanced based on the number of structures for each species combination in the ICSD subset of the AFLOW database. Write species_combos_[n].txt, as well as download[n].in and process[n].in -- input files for build_tests_refdata_from_aflow.py for downloading and processing the structures separately.
"""

from itertools import combinations
from send_openkim_query import send_openkim_query
import requests

def get_all_models_and_supported_elements():
    """
    Query openkim.org to get all models on the site and the elements they support.
    """
    query_params = {
        "database": "obj",
        "query": {"type": {"$in": ["mo", "sm"]}, "kim-api-version": {"$gte": "2"}, "potential-type": {"$ne": "iff"}},
        "fields": {"kimcode": 1, "species": 1},
        "limit": 0,
    }
    try:
        model_and_supported_species = send_openkim_query(query_params, None)
    except:
        raise RuntimeError("KIM query failed")

    # Create dict keyed on model name
    supported_species_for_each_model = {
        result["kimcode"]: result["species"] for result in model_and_supported_species
    }
    return supported_species_for_each_model

if __name__ == "__main__":
    """
    Generate a list of all species combinations, up to a specified limit of
    species, for which compounds are sought.  Only include compounds for which
    there are models in OpenKIM.
    """

    # Read max species per compound
    max_species = int(input("Maximum number of species in a compound = "))
    print("Maximum species = ", max_species)
    # Read number of workers to split between
    n_workers = int(input("Number of workers = "))
    print("Number of workers = ", n_workers)

    elements = [
        "H",
        "He",
        "Li",
        "Be",
        "B",
        "C",
        "N",
        "O",
        "F",
        "Ne",
        "Na",
        "Mg",
        "Al",
        "Si",
        "P",
        "S",
        "Cl",
        "Ar",
        "K",
        "Ca",
        "Sc",
        "Ti",
        "V",
        "Cr",
        "Mn",
        "Fe",
        "Co",
        "Ni",
        "Cu",
        "Zn",
        "Ga",
        "Ge",
        "As",
        "Se",
        "Br",
        "Kr",
        "Rb",
        "Sr",
        "Y",
        "Zr",
        "Nb",
        "Mo",
        "Tc",
        "Ru",
        "Rh",
        "Pd",
        "Ag",
        "Cd",
        "In",
        "Sn",
        "Sb",
        "Te",
        "I",
        "Xe",
        "Cs",
        "Ba",
        "La",
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
        "Hf",
        "Ta",
        "W",
        "Re",
        "Os",
        "Ir",
        "Pt",
        "Au",
        "Hg",
        "Tl",
        "Pb",
        "Bi",
        "Po",
        "At",
        "Rn",
        "Fr",
        "Ra",
        "Ac",
        "Th",
        "Pa",
        "U",
        "Np",
        "Pu",
        "Am",
        "Cm",
        "Bk",
        "Cf",
        "Es",
        "Fm",
        "Md",
        "No",
        "Lr",
        "Rf",
        "Db",
        "Sg",
        "Bh",
        "Hs",
        "Mt",
        "Ds",
        "Rg",
        "Cn",
        "Uut",
        "Fl",
        "Uup",
        "Lv",
        "Uus",
        "Uuo",
    ]
    models_to_skip_prefix = ["LJ_ElliottAkerson_2015_Universal"]

    # Get list of all KIM models and the species they support
    supported_species_for_each_model = get_all_models_and_supported_elements()

    # Build the list of species combinations that KIM models can support
    species_combos = []
    for model in supported_species_for_each_model:
        model_species = supported_species_for_each_model[model]
        # Skip models known to be irrelevant
        if any(model.startswith(prefix) for prefix in models_to_skip_prefix):
            continue
        # Skip models that support custom species not in the periodic table
        if any(item not in elements for item in model_species):
            continue
        # Add single elements for current model
        for spec in model_species:
            if [spec] not in species_combos:
                species_combos.append([spec])
        # Add multi-element combinations for current model up to specified limit
        for i in range(1, max_species):
            model_combinations = list(combinations(model_species, i + 1))
            for combo in model_combinations:
                #sort here, not later, to avoid duplicates -- 
                #duplicates are removed anyway later, but that's after querying aflux,
                #so much faster to do it here
                if sorted(combo) not in species_combos:
                    species_combos.append(sorted(combo))

    # Sort OpenKIM species combinations  by number of elements,
    # and then alphabetically by species
    for i in range(len(species_combos)):
        species_combos[i] = list(species_combos[i])
    species_combos.sort(key=lambda spec_arr: (len(spec_arr), spec_arr))

    print(
        "Found {} species combinations from OpenKIM.".format(
            len(species_combos)
        )
    )

    afloworg_species_list=requests.post("http://aflow.org/API/aflux/?$nspecies(*%d),$paging(0),$catalog(icsd),$compound,$Pearson_symbol_relax,$spacegroup_relax,species,$auid,$aurl"%max_species).json()

    species_combo_counts_dict = {}
    for entry in afloworg_species_list:
        species_combo = entry["species"]
        if species_combo in species_combos:
            species_combo = str(species_combo)
            if species_combo not in species_combo_counts_dict:
                species_combo_counts_dict[species_combo] = 0
            species_combo_counts_dict[species_combo] += 1
    print ("Found {} species combinations in aflow.org.".format(len(species_combo_counts_dict)))
    
    species_combo_counts_dict = {k: v for k, v in sorted(species_combo_counts_dict.items(), key=lambda item: item[1], reverse=True)}
    worker_counts = [0 for i in range(n_workers)]
    worker_species_combos = [[] for i in range(n_workers)]
    for species_combo in species_combo_counts_dict:
        worker_index_where_this_combo_will_go = worker_counts.index(min(worker_counts))
        worker_species_combos[worker_index_where_this_combo_will_go].append(species_combo)
        worker_counts[worker_index_where_this_combo_will_go] += species_combo_counts_dict[species_combo]    

    for i in range(n_workers):
        # Write result
        print ("Worker %d will process %d species combinations corresponding to %d aflow compounds"%(i, len(worker_species_combos[i]), worker_counts[i]))
        species_combo_file = "species_combos_%d.txt"%i
        with open(species_combo_file, "w") as f:
            for species_combo in worker_species_combos[i]:
                f.write(species_combo + "\n")

    DOWNLOAD_IN_TEMPLATE = "1                                       # build tests\n1                                       # build reference data\n1                                       # restrict to ICSD\n1                                       # Only write AFLUX query and files, don't process?\n0                                       # Don't query and download files, expect them to exist already?\n{0}                                       # \"thread number\" (for avoiding filename conflicts)\ndft_type ldau_type                      # DFT hyperparameters to query for\n4ad03136-ed7f-4316-b586-1e94ccceb311    # kim user ID\n                                        # aflow version (default:auto detect)\n1                                      # number of threads for aflow++ (default: 1)\nwork_dir                                # working directory"
    PROCESS_TEMPLATE = "1                                       # build tests\n1                                       # build reference data\n1                                       # restrict to ICSD\n0                                       # Only write AFLUX query and files, don't process?\n1                                       # Don't query and download files, expect them to exist already?\n{0}                                       # \"thread number\" (for avoiding filename conflicts)\ndft_type ldau_type                      # DFT hyperparameters to query for\n4ad03136-ed7f-4316-b586-1e94ccceb311    # kim user ID\n                                        # aflow version (default:auto detect)\n1                                      # number of threads for aflow++ (default: 1)\nwork_dir                                # working directory"
    for i in range(n_workers):
        with open("download%d.in"%i, "w") as f:
            f.write(DOWNLOAD_IN_TEMPLATE.format(i))
        with open("process%d.in"%i, "w") as f:
            f.write(PROCESS_TEMPLATE.format(i))



