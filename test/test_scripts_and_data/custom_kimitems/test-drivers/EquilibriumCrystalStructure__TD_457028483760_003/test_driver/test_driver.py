"""
Performs a symmetry-constrained minimization of the crystal
"""

from kim_tools import (
    SingleCrystalTestDriver,
    minimize_wrapper,
    get_stoich_reduced_list_from_prototype,
    get_isolated_energy_per_atom,
)
from ase.filters import FrechetCellFilter, UnitCellFilter
from ase.optimize.optimize import Optimizer
from ase.optimize.lbfgs import LBFGSLineSearch
from typing import Dict


class TestDriver(SingleCrystalTestDriver):
    def _calculate(
        self,
        fmax: float = 1e-5,
        steps: int = 200,
        algorithm: Optimizer = LBFGSLineSearch,
        cell_filter: UnitCellFilter = FrechetCellFilter,
        opt_kwargs: Dict = {},
        flt_kwargs: Dict = {},
        **kwargs
    ) -> None:
        """
        Performs a symmetry-constrained minimization of the crystal

        Args:
            fmax:
                Maximum force component tolerance
            steps:
                Maximum number of steps
        """
        atoms = self._get_atoms()
        num_atoms = len(atoms)
        prototype_label = self._get_nominal_crystal_structure_npt()["prototype-label"][
            "source-value"
        ]
        stoichiometry = get_stoich_reduced_list_from_prototype(prototype_label)
        stoichiometric_species = self._get_nominal_crystal_structure_npt()[
            "stoichiometric-species"
        ]["source-value"]
        num_atoms_in_formula = sum(stoichiometry)
        minimization_succeeded = minimize_wrapper(
            atoms=atoms,
            fmax=fmax,
            steps=steps,
            logfile="-",
            algorithm=algorithm,
            cell_filter=cell_filter,
            fix_symmetry=True,
            opt_kwargs=opt_kwargs,
            flt_kwargs=flt_kwargs,
        )
        potential_energy = atoms.get_potential_energy()
        potential_energy_per_atom = potential_energy / num_atoms
        potential_energy_per_formula = potential_energy_per_atom * num_atoms_in_formula
        isolated_energy_per_formula = sum(
            [
                num_per_formula
                * get_isolated_energy_per_atom(self.kim_model_name, species)
                for num_per_formula, species in zip(
                    stoichiometry, stoichiometric_species
                )
            ]
        )
        binding_potential_energy_per_formula = (
            potential_energy_per_formula - isolated_energy_per_formula
        )
        binding_potential_energy_per_atom = (
            binding_potential_energy_per_formula / num_atoms_in_formula
        )
        self._update_nominal_parameter_values(atoms)
        if minimization_succeeded:
            disclaimer = None
        else:
            disclaimer = (
                "The forces and stresses failed to converge "
                "to the requested tolerance"
            )
            print(
                "\nThe minimization failed to converge. "
                "See kim-tools.log for more info"
            )

        self._add_property_instance_and_common_crystal_genome_keys(
            "crystal-structure-npt",
            write_stress=True,
            write_temp=True,
            disclaimer=disclaimer,
        )
        self._add_property_instance_and_common_crystal_genome_keys(
            "binding-energy-crystal", disclaimer=disclaimer
        )
        self._add_key_to_current_property_instance(
            "binding-potential-energy-per-atom",
            binding_potential_energy_per_atom,
            unit="eV",
        )
        self._add_key_to_current_property_instance(
            "binding-potential-energy-per-formula",
            binding_potential_energy_per_formula,
            unit="eV",
        )
        self._add_property_instance_and_common_crystal_genome_keys(
            "mass-density-crystal-npt",
            write_stress=True,
            write_temp=True,
            disclaimer=disclaimer,
        )
        self._add_key_to_current_property_instance(
            "mass-density", self._get_mass_density(), unit="amu/angstrom^3"
        )
