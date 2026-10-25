import json
from ase.data import chemical_symbols
from ase.data import reference_states
from random import randint

# get lattice-specific elements
# chemical_symbols_fcc = [ sym for pk,sym in enumerate(chemical_symbols) if reference_states[pk] and reference_states[pk].get('symmetry') == 'fcc' ]
# chemical_symbols_bcc = [ sym for pk,sym in enumerate(chemical_symbols) if reference_states[pk] and reference_states[pk].get('symmetry') == 'bcc' ]

# chemical_symbols = ['Fe']
types = ["fcc", "bcc", "sc", "diamond"]

with open("test_generator.json", "w") as f:
    for lattice in types:
        for element in chemical_symbols:
            kimnum = "{:012d}".format(randint(0, 10 ** 12 - 1))
            f.write(
                json.dumps({"symbol": element, "lattice": lattice, "kimnum": kimnum})
                + "\n"
            )
