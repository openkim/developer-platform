# Utilities for working with LAMMPS bonded data files in the context of OpenKIM tests or VCs

import pathlib
from curses.ascii import isalpha
from typing import Any, Callable, Dict, List, Optional, Tuple
import os

def get_labelmap_from_lammps_data(lammps_data_filename: str) -> Dict:
    """
    Extract the labelmap from a LAMMPS data file
    
    Args:
        lampps_data_filename: LAMMPS data file

    Returns:
        labelmap as a dict of integers to strings
    """

    num_to_type = {}
    with open(lammps_data_filename) as f:
        reading_atom_types = False        
        for line in f:
            line_stripped = line.strip()
            if line_stripped == "": 
                continue
            if reading_atom_types:
                if isalpha(line_stripped[0]): # we encountered the heading for the next section
                    break
                line_split = line_stripped.split()
                assert(len(line_split)==2)
                assert(int(line_split[0]) not in num_to_type)
                num_to_type[int(line_split[0])]=line_split[1]
            elif line_stripped == "Atom Type Labels":
                reading_atom_types = True
    return num_to_type

def get_type_to_element_mapping(sym_map_filename: str) -> Dict:
    """
    Read file mapping internal atom types to chemical elements and return it as a dict

    Args:
        sym_map_filename: path to file mapping atom types to species

    Returns:
        Dict mapping internal atom types to chemical elements, e.g. {"c1":"C",...}
    """        
    try:
        with open(sym_map_filename) as f:
            lines = f.readlines()
            type_to_sym = {}
            for line in lines:
                line_list = line.split()
                typ = line_list[0]
                sym = line_list[1]
                type_to_sym[typ] = sym
    except:
        raise RuntimeError("Could not find file {}".format(sym_map_filename))
    return type_to_sym