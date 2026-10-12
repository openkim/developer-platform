import logging
from dataclasses import dataclass
from kim_tools import SingleCrystalTestDriver
from kim_tools.test_driver.core import FMAX_INITIAL, MAXSTEPS_INITIAL
from kim_tools.symmetry_util.core import (
    fit_voigt_tensor_to_cell_and_space_group,
    fit_voigt_tensor_and_error_to_cell_and_space_group,
)
from kim_tools.symmetry_util.elasticity import (
    indep_elast_compon_names_and_values_from_voigt,
    calc_bulk,
    find_nearest_isotropy,
    map_to_Kelvin,
    voigt_elast_struct_svg,
)
from kim_tools.aflow_util.core import AFLOW_EXECUTABLE
from typing import Optional, Union, Dict
from numdifftools import MaxStepGenerator
from ase.units import GPa
from ase.optimize.lbfgs import LBFGSLineSearch
from ase.optimize.optimize import Optimizer
from ase.calculators.calculator import Calculator
from .elastic import ElasticConstants
import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)
logging.basicConfig(filename="kim-tools.log", level=logging.INFO, force=True)


@dataclass
class ElConstResultsErrors:
    """
    All information of interest from a given run of ElasticConstants.results()
    """

    elconst_raw: npt.ArrayLike
    elconst_raw_err: npt.ArrayLike
    elconst_raw_err_frac: float
    elconst_matl_symm: npt.ArrayLike
    elconst_matl_symm_err: npt.ArrayLike
    matl_symm_err_frac: float
    message: str


def compute_results_summary(
    elconst_raw: npt.ArrayLike,
    elconst_raw_err: npt.ArrayLike,
    message: str,
    cell: npt.ArrayLike,
    sgnum: Union[int, str],
) -> ElConstResultsErrors:
    """
    Make an ElConstResultsErrors object from the output of
    ``ElasticConstants.results()``
    """
    econst_raw_Kelv = map_to_Kelvin(elconst_raw)
    elconst_raw_norm = np.einsum("ij,ij", econst_raw_Kelv, econst_raw_Kelv)
    elconst_raw_norm = elconst_raw_norm**0.5

    addtl_msg = ""

    if np.isnan(elconst_raw_err).any():
        elconst_raw_err_frac = np.nan
        elconst_matl_symm = fit_voigt_tensor_to_cell_and_space_group(
            voigt_input=elconst_raw, cell=cell, sgnum=sgnum
        )
        elconst_matl_symm_err = np.full((6, 6), np.nan)
    else:
        elconst_raw_err_Kelv = map_to_Kelvin(elconst_raw_err)
        elconst_raw_err_norm = np.einsum(
            "ij,ij", elconst_raw_err_Kelv, elconst_raw_err_Kelv
        )
        elconst_raw_err_norm = elconst_raw_err_norm**0.5

        elconst_raw_err_frac = elconst_raw_err_norm / elconst_raw_norm

        elconst_matl_symm, elconst_matl_symm_err = (
            fit_voigt_tensor_and_error_to_cell_and_space_group(
                voigt_input=elconst_raw,
                voigt_error=elconst_raw_err,
                cell=cell,
                sgnum=sgnum,
                symmetric=True,
            )
        )
        addtl_msg += f"\nRelative norm of error estimate: {elconst_raw_err_frac}"

    matl_symm_err = elconst_matl_symm - elconst_raw

    matl_symm_err_Kelv = map_to_Kelvin(matl_symm_err)
    matl_symm_err_norm = np.einsum("ij,ij", matl_symm_err_Kelv, matl_symm_err_Kelv)
    matl_symm_err_norm = matl_symm_err_norm**0.5

    matl_symm_err_frac = matl_symm_err_norm / elconst_raw_norm

    addtl_msg += (
        f"\nRelative norm of deviation from material symmetry: {matl_symm_err_frac}"
    )

    print(addtl_msg)

    return ElConstResultsErrors(
        elconst_raw=elconst_raw,
        elconst_raw_err=elconst_raw_err,
        elconst_raw_err_frac=elconst_raw_err_frac,
        elconst_matl_symm=elconst_matl_symm,
        elconst_matl_symm_err=elconst_matl_symm_err,
        matl_symm_err_frac=matl_symm_err_frac,
        message=message + addtl_msg,
    )


def makeDefaultStepGenerator(base_step: float) -> MaxStepGenerator:
    return MaxStepGenerator(
        base_step=base_step,
        num_steps=14,
        use_exact_steps=True,
        step_ratio=1.6,
        offset=0,
    )


class TestDriver(SingleCrystalTestDriver):
    def __init__(
        self,
        model: Union[str, Calculator],
        suppr_sm_lmp_log: bool = True,
        aflow_executable: str = AFLOW_EXECUTABLE,
    ) -> None:
        """
        Args:
            model:
                ASE calculator or KIM model name to use
            suppr_sm_lmp_log:
                Suppress writing a lammps.log
            aflow_executable:
                Path to AFLOW executable
        """
        self.aflow_executable = aflow_executable
        super().__init__(model, suppr_sm_lmp_log=suppr_sm_lmp_log)

    def _calculate(
        self,
        method: Optional[str] = None,
        strain_step: Optional[Union[MaxStepGenerator, float]] = None,
        fmax: float = FMAX_INITIAL,
        steps: int = MAXSTEPS_INITIAL,
        algorithm: Optimizer = LBFGSLineSearch,
        fix_symmetry: bool = True,
        opt_kwargs: Dict = {},
        extrap_tol_95: float = 0.02,
        matl_symm_tol: float = 0.01,
        **kwargs,
    ) -> None:
        """
        Calculate the elasticity tensor (both raw and symmetrized according to material
        symmetry), unique elastic constant components, and distance to nearest isotropic
        elasticity tensor. By default, this Test Driver performs a loop over several
        settings to find the lowest error in a weighed combination of extrapolation
        error and deviation from material symmetry. If
        ``method`` and/or ``strain_step`` are provided, this behavior is overridden, and a
        single calculation is performed instead.

        Args:
            method:
                Select method for computing the elastic constants. The following
                methods are supported:
                "energy-condensed" : Compute elastic constants from the Hessian
                    of the condensed strain energy density (i.e. the enregy for
                    a given strain is relaxed with respect to internal atom
                    positions)
                "stress-condensed" : Compute elastic constants from the Jacobian
                    of the condensed stress (i.e. the stress for a given strain
                    where the energy is relaxed with respect to internal atom
                    positions)
                "energy-full" : Compute elastic constants from the full Hessian
                    relative to both strains and internal atom degrees of
                    freedom. This is followed by an algebraic manipulation to
                    account for the effect of atom relaxation on elastic
                    constants.
                In general, "energy-condensed" is the preferred method.
                The "stress-condensed" method is much faster, but generally less
                accurate. The "energy-full" method has accuracy comparable
                to "energy-condensed" but tends to be much slower due to the
                larger Hessian matrix that has to be computed.
                If `strain_step` is provided, but this is not, this will be set
                to "energy-condensed".
            strain_step:
                The step or ``numdifftools.MaxStepGenerator`` to use for numerical
                differentiation.
                If ``method`` is provided, but this is not, this will be set
                to:
                    MaxStepGenerator(
                        base_step=1e-4,
                        num_steps=14,
                        use_exact_steps=True,
                        step_ratio=1.6,
                        offset=0,
                    )
            fmax:
                Force convergence tolerance (the magnitude of the force on each
                atom must be less than this for convergence)
            steps:
                Maximum number of iterations for the minimization
            algorithm:
                ASE optimizer algorithm
            fix_symmetry:
                Whether to fix the symmetry during minimization
            opt_kwargs:
                Dictionary of kwargs to pass to optimizer
            extrap_tol_95:
                If neither ``method`` nor ``strain_step`` are specified,
                this is the tolerance that will be used to threshold
                and weight the 95% extrap error reported by
                numdifftools. The norm of the error matrix in Kelvin
                form divided by the norm of the elasticity matrix in
                Kelvin form will be compared to this tolerance.
            matl_symm_tol:
                If neither ``method`` nor ``strain_step`` are specified,
                this is the tolerance that will be used to threshold
                and weight the deviation from material symmetry.
                The deviation is the difference between the elastic constants
                symmetrized to fit the space group of the material and
                the as-computed elastic constants.
                The norm of the deviation matrix in Kelvin
                form divided by the norm of the elasticity matrix in
                Kelvin form will be compared to this tolerance.
        """

        print("\nE L A S T I C  C O N S T A N T  C A L C U L A T I O N S\n")
        print()

        prototype_label = self._get_nominal_crystal_structure_npt()["prototype-label"][
            "source-value"
        ]
        sgnum = int(prototype_label.split("_")[2])

        if fix_symmetry:
            sgnum_for_min = sgnum
        else:
            sgnum_for_min = 1

        atoms = self._get_atoms()

        o_cell = atoms.get_cell()

        moduli = ElasticConstants(
            atoms=atoms,
            sgnum=sgnum_for_min,
            fmax=fmax,
            steps=steps,
            algorithm=algorithm,
            opt_kwargs=opt_kwargs,
        )

        extrap_err_undef = False
        # Set up sequence of calculations
        if method is not None or strain_step is not None:
            if method is None:
                method = "energy-condensed"
            if strain_step is None:
                strain_step = makeDefaultStepGenerator(1e-4)
            else:
                if isinstance(strain_step, float):
                    # Can't get extrapolation error with a single step
                    extrap_err_undef = True
            sequence = [(method, strain_step)]
        else:
            sequence = []
            # From testing, only one model out of 388
            # benefitted from having a strain step of 1e-2
            # with energy-condensed
            for base_step in [1e-4, 1e-3]:
                sequence.append(
                    ("energy-condensed", makeDefaultStepGenerator(base_step))
                )
            for base_step in [1e-4, 1e-3, 1e-2, 0.1]:
                sequence.append(
                    ("stress-condensed", makeDefaultStepGenerator(base_step))
                )

        results_summaries = []
        converged = False
        for method, step in sequence:
            try:
                results = moduli.results(
                    method=method,
                    step=step,
                )
                results_summaries.append(
                    compute_results_summary(*results, o_cell, sgnum)
                )
                if (results_summaries[-1].elconst_raw_err_frac < extrap_tol_95) and (
                    results_summaries[-1].matl_symm_err_frac < matl_symm_tol
                ):
                    # If elconst_raw_err_frac is np.nan, will never get here
                    converged = True
                    break
            except Exception as e:
                msg = (
                    "\nThe following exception was caught during "
                    "Hessian or Jacobian calculation:\n"
                )
                msg += repr(e)
                print(msg)
                logger.info(msg)

        if results_summaries == []:
            raise RuntimeError(
                "All attempts to compute elastic constants failed. See log for error(s)"
            )
        # Check that presence or absence of NaNs makes sense given what we ran
        if any([np.isnan(result.elconst_raw_err_frac) for result in results_summaries]):
            assert extrap_err_undef, (
                "Unexpectedly got a NaN extrapolation error. This should only happen "
                "if a user asked for a single strain step"
            )
        # Check the converse -- if the user asked for a single strain step, we should
        # not have any extrapolation error estimates, and we should only have one result
        if extrap_err_undef:
            assert (
                len(results_summaries) == 1
            ), "We should never have more than one result if the user specified a step"
            assert np.isnan(results_summaries[0].elconst_raw_err_frac), (
                "If the user specified a single strain step, the extrapolation error "
                "must be nan"
            )

        if converged:
            disclaimer = None
        else:
            if extrap_err_undef:
                disclaimer = (
                    "Elastic constants were evaluated with a single step. Unable to "
                    "compute uncertainty."
                )
            else:
                disclaimer = (
                    r"Elastic constants calculation had a relative 95% uncertainty "
                    f"greater than {extrap_tol_95} and/or relative deviation from "
                    f"material symmetry greater than {matl_symm_tol}.\n"
                    "See stdout and logs for calculation details."
                )
            print(disclaimer)
            if len(results_summaries) > 1:
                # We did a loop but didn't converge. Need to find the best result
                results_summaries.sort(
                    key=lambda x: (x.elconst_raw_err_frac / extrap_tol_95) ** 2
                    + (x.matl_symm_err_frac / matl_symm_tol) ** 2,
                    reverse=True,
                )
                print()
                print("The following run was chosen as having the lowest error: ")
                print(results_summaries[-1].message)

        # In all cases, the best result ended up at the end of the list. Assign
        # variables and convert. NaN will stay NaN, no special treatment
        # needed
        elconst_raw = results_summaries[-1].elconst_raw / GPa
        elconst_raw_err = results_summaries[-1].elconst_raw_err / GPa
        elconst_matl_symm = results_summaries[-1].elconst_matl_symm / GPa
        elconst_matl_symm_err = results_summaries[-1].elconst_matl_symm_err / GPa
        units = "GPa"

        elconst_names, elconst_values = indep_elast_compon_names_and_values_from_voigt(
            voigt=elconst_matl_symm, sgnum=sgnum
        )
        _, elconst_values_err = indep_elast_compon_names_and_values_from_voigt(
            voigt=elconst_matl_symm_err, sgnum=sgnum
        )

        bulk = calc_bulk(elconst_raw)
        # Compute nearest isotropic constants and distance
        try:
            d_iso, bulk_iso, shear_iso = find_nearest_isotropy(elconst_raw)
            got_iso = True
        except Exception:
            got_iso = False  # Failure can occur if elastic constants are
            # not positive definite

        # Echo output
        print("\nR E S U L T S\n")
        print(f"Elastic constants [{units}]:")
        print(
            np.array_str(
                elconst_raw,
                precision=5,
                max_line_width=100,
                suppress_small=True,
            )
        )
        if not extrap_err_undef:
            print()
            print(f"95 %% Error estimate [{units}]:")
            print(
                np.array_str(
                    elconst_raw_err,
                    precision=5,
                    max_line_width=100,
                    suppress_small=True,
                )
            )
        print()
        print(f"Bulk modulus [{units}] = {bulk}")
        print()
        print("Unique elastic constants for space group {} [{}]".format(sgnum, units))
        print(elconst_names)
        print(elconst_values)
        print()
        if got_iso:
            print("Nearest matrix of isotropic elastic constants:")
            print(f"Distance to isotropic state [-]  = {d_iso}")
            print(f"Isotropic bulk modulus      [{units}] = {bulk_iso}")
            print(f"Isotropic shear modulus     [{units}] = {shear_iso}")
        else:
            print("WARNING: Nearest isotropic state not computed.")

        ####################################################
        # ACTUAL CALCULATION ENDS
        ####################################################

        ####################################################
        # PROPERTY WRITING
        ####################################################
        self._add_property_instance_and_common_crystal_genome_keys(
            "elastic-constants-isothermal-npt",
            write_stress=True,
            write_temp=True,
            disclaimer=disclaimer,
        )
        self._add_key_to_current_property_instance(
            "elastic-constants-names", elconst_names
        )
        if not extrap_err_undef:
            self._add_key_to_current_property_instance(
                "elastic-constants-values",
                elconst_values,
                "GPa",
                {
                    "source-expand-uncert-value": elconst_values_err,
                    "uncert-lev-of-confid": 95,
                },
            )
            self._add_key_to_current_property_instance(
                "elasticity-matrix-raw",
                elconst_raw,
                "GPa",
                {
                    "source-expand-uncert-value": elconst_raw_err,
                    "uncert-lev-of-confid": 95,
                },
            )
            self._add_key_to_current_property_instance(
                "elasticity-matrix",
                elconst_matl_symm,
                "GPa",
                {
                    "source-expand-uncert-value": elconst_matl_symm_err,
                    "uncert-lev-of-confid": 95,
                },
            )
        else:
            self._add_key_to_current_property_instance(
                "elastic-constants-values",
                elconst_values,
                "GPa",
            )
            self._add_key_to_current_property_instance(
                "elasticity-matrix-raw",
                elconst_raw,
                "GPa",
            )
            self._add_key_to_current_property_instance(
                "elasticity-matrix",
                elconst_matl_symm,
                "GPa",
            )

        matrix_structure_file = "matrix-structure.svg"
        voigt_elast_struct_svg(sgnum, matrix_structure_file)
        self._add_file_to_current_property_instance(
            "elasticity-matrix-structure", matrix_structure_file
        )

        if got_iso:
            self._add_key_to_current_property_instance("distance-to-isotropy", d_iso)

        self._add_property_instance_and_common_crystal_genome_keys(
            "bulk-modulus-isothermal-npt",
            write_stress=True,
            write_temp=True,
            disclaimer=disclaimer,
        )
        self._add_key_to_current_property_instance(
            "isothermal-bulk-modulus", bulk, "GPa"
        )
