from ase.build import bulk
from ase.calculators.kim import KIM
from kim_tools.ase.core import randomize_positions
from kim_tools import minimize_wrapper

atoms = bulk("Si", cubic=True)
atoms.repeat((40, 40, 40))
atoms.calc = KIM("TorchML_MACE_GuptaTadmorMartiniani_2024_Si__MO_781946209112_001")
for _ in range(20):
    randomize_positions(atoms, pert_amp=0.1)
    minimize_wrapper(atoms, variable_cell=False)
    print(
        f"Energy after perturbation and minimization: {atoms.get_potential_energy()}"
    )
