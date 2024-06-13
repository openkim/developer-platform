import json
from ase.data import chemical_symbols
from ase.data import reference_states
from random import randint

# get fcc stuff
chemical_symbols_fcc = [
    sym
    for pk, sym in enumerate(chemical_symbols)
    if reference_states[pk] and reference_states[pk].get("symmetry") == "fcc"
]
chemical_symbols_bcc = [
    sym
    for pk, sym in enumerate(chemical_symbols)
    if reference_states[pk] and reference_states[pk].get("symmetry") == "bcc"
]

with open("test_generator.json", "w") as f:
    for element in chemical_symbols_fcc:
        kimnum = "{:012d}".format(randint(0, 10 ** 12 - 1))
        f.write(
            json.dumps({"symbol": element, "lattice": "fcc", "kimnum": kimnum}) + "\n"
        )
    for element in chemical_symbols_bcc:
        kimnum = "{:012d}".format(randint(0, 10 ** 12 - 1))
        f.write(
            json.dumps({"symbol": element, "lattice": "bcc", "kimnum": kimnum}) + "\n"
        )
