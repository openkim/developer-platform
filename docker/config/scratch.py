from ase.build import bulk
from ase.calculators.kim import KIM
from kim_tools.ase.core import randomize_positions

atoms = bulk("Si", cubic=True)
atoms.repeat((40,40,40))
atoms.calc = KIM("TorchML_MACE_GuptaTadmorMartiniani_2024_Si__MO_781946209112_001")
for _ in range(1000):
    randomize_positions(atoms, pert_amp=0.1)
    atoms.get_potential_energy()