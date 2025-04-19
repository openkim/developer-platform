#!/usr/bin/python

"""
Debugging script for SingleCrystalTestDriver
"""

from test_driver.test_driver import TestDriver
from kim_tools import query_crystal_structures, detect_unique_crystal_structures

kim_model_name = "Sim_LAMMPS_Buckingham_CarreHorbachIspas_2008_SiO__SM_886641404623_000"
test_driver = TestDriver(kim_model_name)

list_of_queried_structures = query_crystal_structures(
    stoichiometric_species=["O", "Si"], prototype_label="A2B_oC24_20_abc_c"
)

unique_structure_indices = detect_unique_crystal_structures(list_of_queried_structures)

print(
    f"\n{len(unique_structure_indices)} of {len(list_of_queried_structures)} "
    "queried structures were found to be unique.\n"
)

for i in unique_structure_indices:
    print("\nRUNNING TEST DRIVER ON QUERIED STRUCTURE\n")
    computed_property_instances = test_driver(list_of_queried_structures[i])

print(f"\nI've accumulated {len(test_driver.property_instances)} Property Instances\n")
test_driver.write_property_instances_to_file()
