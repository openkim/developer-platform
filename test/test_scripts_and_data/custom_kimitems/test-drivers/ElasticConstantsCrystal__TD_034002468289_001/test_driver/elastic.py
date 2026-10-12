"""
Compute elasticity matrix for an arbitrary crystal structure defined by a
periodic cell and basis atom positions.

The following methods for computing the elastic constants are supported:

(I) energy-condensed : Compute elastic constants from the hessian of the
condensed strain energy density, W_eff(eps) = min_d W(eps,d), where d are
the displacements of the internal atoms (aside from preventing rigid-body
translation) and eps is the strain.

(II) stress-condensed : Compute elastic constants from the jacobian of the
condensed stress, sig_eff(eps) = sig(eps,dmin), where dmin = arg min_d
W(eps,d).

(III) energy-full : Compute elastic constants from the hessian of the full
strain energy density, W(eps,d). This involves an algebraic manipulation
to account for the effect of atom relaxation; see eqn (27), in Tadmor et
al, Phys. Rev. B, 59:235-245, 1999.

For well-behaved potentials, all three methods give similar results with
differences beyond the first or second digit due to the numerical differentiation.
The `energy-condensed` and `energy-full` approaches have comparable accuracy,
but full Hessian is *much* slower. The `stress-condensed` approach is
significantly faster than `energy-condensed`, but is less accurate.

For potentials with a rough energy landscape due to sharp cut-offs or
electrostatics, `stress-condensed` is sometimes better behaved.

The default approach is `energy-condensed`.

=== Theory ===

All three approaches involve numerical differentiation of energy or stress
expressions in terms of strains represented in Voigt notation. This is requires
the introduction of factors to account for the Voigt form as explained below.

The code assumes a Voigt notation with the following ordering:
1 = 11,  2 = 22,  3 = 33,  4 = 23,  5 = 13,  6 = 12  ---------------(1)

In this notation, the linear elastic stress-strain relation for infinitesimal
defomation is give by:

sig_m = C_mn eps_n -------------------------------------------------(2)

where

sig_1 = sig_11,  sig_2 = sig_22,  sig_3 = sig_33
sig_4 = sig_23,  sig_5 = sig_13,  sig_6 = sig_12

eps_1 = eps_11,  eps_2 = eps_22,  eps_3 = eps_33
eps_4 = gam_23,  eps_5 = gam_13,  eps_6 = gam_12 -------------------(3)

and gam_ij = 2 eps_ij.

In the above sig_ij and eps_ij are the components of the stress and strain
tensors in a Cartesian basis. The same basis is used to define the orientation
of the periodic cell and basis atom positions.

=== Energy-based calculation of elastic constants ===

The strain energy density of a linear elastic meterial is

W = 1/2 c_ijkl eps_ij eps_kl ---------------------------------------(4)

where c_ijkl are the components of the 4th-order elasticity tensor.
In Voigt notation strain energy density has the form:

W = 1/2 C_mn eps_m eps_n -------------------------------------------(5)

where C_mn are the components of elasticity matrix. The symmetries in the
summation of Eqn (4) (which includes 81 terms) are captured by the factors
of two in the 4, 5, 6 components of eps_* in Eqn (3).

Eqn (4) implies that the elasticity tensor components are given by

c_ijkl = d^2 W / d eps_ij d eps_kl ---------------------------------(6)

Substituting into Eqn (6), the definition of W in Eqn (5), a chain rule
must be applied:

c_ijkl = (d^2 W / d eps_m d eps_n )(d eps_m / d eps_ij)(d eps_n / d eps_kl)

                                                                    (7)

Transforming to Voigt notation and accounting for the factors of two
in the shear terms in Eqn (3), we have

C_mn = d^2 W / d eps_m d eps_n               for m,n <=3

C_mn = (1/2) d^2 W / d eps_m d eps_n         for m<=3, n>3  or
                                                 m>3, n<=3

C_mn = (1/4) d^2 W / d eps_m d eps_n         for m,n > 3

=== Stress-based calculation of elastic constants ===

An alternative aproach to computing the elastic constants is to use the
stress-strain relation in Eqn (2), which in full tensorial notation is

sig_ij = c_ijkl eps_kl ---------------------------------------------(8)

This relation implies that

c_ijkl = d sig_ij / d eps_kl ---------------------------------------(9)

Substituting in Eqn (2) for the stress and applying the chain rule,

c_ijkl = (d sig_m / d eps_n)(d eps_n / d eps_kl) ------------------(10)

where m is the Voigt index for ij. Transforming to Voigt notation and
accounting for the factors of two in the shear terms in Eqn (3), we have

C_mn = d sig_m / d eps_n                     for m,n <=3

C_mn = (1/2) d sig_m / d eps_n               for n > 3

Revisions:

2019/04/13 Ellad Tadmor added ability to do diamond)
2022/02/01 Chloe Zeller (lammps compatibility - specific usage case)
2022/02/22 Ellad Tadmor generalized to arbitrary crystal structures
2024/05/08 Ilia Nikiforov Symmetry checking and refactoring for robust Crystal Genome
operation
2025/07/19 Ilia Nikiforov Refactor for Elastic Constants Test Driver 001. Move
error checking and iteration out of this file, leaving that to the calling routine.
Allow option of symmetry restriction.

"""

import logging
import numpy as np
import numpy.typing as npt
from ase.atoms import Atoms
import numdifftools as ndt
from numdifftools.step_generators import MaxStepGenerator
import math
from typing import Union, Tuple, Dict
from kim_tools import minimize_wrapper
from kim_tools.symmetry_util.core import (
    fractional_to_cartesian_itc_rotation_from_ase_cell,
    FixProvidedSymmetry,
    get_primitive_genpos_ops,
)
from ase.optimize.optimize import Optimizer
from ase.optimize.lbfgs import LBFGSLineSearch


logger = logging.getLogger(__name__)
logging.basicConfig(filename="kim-tools.log", level=logging.INFO, force=True)


def energy_hessian_add_prefactors(
    hessian: npt.ArrayLike, hessian_error_estimate: npt.ArrayLike
) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    """
    Hessian was computed as d^2 W / d eps_m d eps_n.
    As noted in the module doc string, a prefactor is required for some terms
    to obtain the elastic constants

    Returns:
        * 6x6 elasticity matrix in Voigt order
        * 6x6 error estimate in Voigt order
    """
    elastic_constants = np.zeros(shape=(6, 6))
    error_estimate = np.zeros(shape=(6, 6))
    for m in range(6):
        if m < 3:
            factm = 1.0
        else:
            factm = 0.5
        for n in range(6):
            if n < 3:
                fact = factm
            else:
                fact = factm * 0.5
            elastic_constants[m, n] = fact * hessian[m, n]
            error_estimate[m, n] = fact * hessian_error_estimate[m, n]
    return elastic_constants, error_estimate


class ElasticConstants(object):
    """
    Compute the elastic constants of an arbitrary crystal
    through numerical differentiation
    """

    def __init__(
        self,
        atoms: Atoms,
        sgnum: int = 1,
        fmax: float = 1e-5,
        steps: int = 200,
        algorithm: Optimizer = LBFGSLineSearch,
        opt_kwargs: Dict = {},
    ):
        """
        Class containing data and routines for elastic constant calculations

        Parameters:
            atoms:
                ASE atoms object with calculator attached. This object
                contains the structure for which the elastic constant will be
                computed.
            sgnum:
                The optimization will be symmetry-restricted based on
                this space group number. In order for this to work correctly,
                the unit cell must be in the orientation defined in
                doi.org/10.1016/j.commatsci.2017.01.017. For each deformation
                step, the symmetry elements broken by the deformation will be
                disabled. Use a value of 1 (default) to disable
                symmetry restriction
            fmax:
                Force convergence tolerance (the magnitude of the force on each
                atom must be less than this for convergence)
            steps:
                Maximum number of iterations for the minimization
            algorithm:
                ASE optimizer algorithm
            opt_kwargs:
                Dictionary of kwargs to pass to optimizer

        """
        self.atoms = atoms
        self.natoms = atoms.get_global_number_of_atoms()
        self.sgnum = sgnum
        # Store the original reference cell structure and volume, and atom
        # positions.
        self.o_cell = self.atoms.get_cell()
        self.o_volume = self.atoms.get_volume()
        self.refpositions = self.atoms.get_positions()
        self.fmax = fmax
        self.steps = steps
        self.algorithm = algorithm
        self.opt_kwargs = opt_kwargs

    def voigt_to_matrix(self, voigt_vec: npt.ArrayLike) -> npt.ArrayLike:
        """
        Convert a voigt notation vector to a matrix

        Parameters:
            voigt_vec:
                A numpy array containing the six strain components in
                Voigt ordering (xx, yy, zz, yz, xz, xy)

        Returns:
            matrix:
               A 3x3 numpy array containg the strain tensor components
        """
        matrix = np.zeros((3, 3))
        matrix[0, 0] = voigt_vec[0]
        matrix[1, 1] = voigt_vec[1]
        matrix[2, 2] = voigt_vec[2]
        matrix[tuple([[1, 2], [2, 1]])] = voigt_vec[3]
        matrix[tuple([[0, 2], [2, 0]])] = voigt_vec[4]
        matrix[tuple([[0, 1], [1, 0]])] = voigt_vec[5]
        return matrix

    def get_energy_from_positions(self, pos: npt.ArrayLike) -> float:
        """
        Compute the potential energy of the configuration, given a set of positions for
        the internal atoms.

        Parameters:
            pos:
                A numpy array containing the positions of all atoms in a
                flat concatenated form

        Returns:
            energy:
               Potential energy of the configuration
        """
        self.atoms.set_positions(np.reshape(pos, (self.natoms, 3)))
        energy = self.atoms.get_potential_energy()

        return energy

    def get_gradient_from_positions(self, pos: npt.ArrayLike) -> npt.ArrayLike:
        """
        Compute the gradient of the configuration's potential energy, given a set of
        positions for the internal atoms.

        Parameters:
            pos:
                A numpy array containing the positions of all atoms in a
                flat concatenated form

        Returns:
            gradient:
               The gradient of the potential energy of the force (the negative
               of the forces) in a flat concatenated form
        """
        self.atoms.set_positions(np.reshape(pos, (self.natoms, 3)))
        forces = self.atoms.get_forces()
        return -forces.flatten()

    def get_energy_from_strain_and_atom_displacements(
        self, strain_and_disps_vec: npt.ArrayLike
    ) -> float:
        """
        Compute reference strain energy density for a given applied strain
        and internal atom positions for all but one atom constrained to
        prevent rigid-body translation.

        Parameters:
            strain_and_disps_vec:
                A numpy array of length 6+(natoms-1)*3 containing the
                strain components in Voigt order and the free internal
                atom degrees of freedom

        Returns:
            energy density:
                Potential energy of the configuration divided by its reference
                (unstrained) volume
        """
        if self.natoms < 2:
            return self.get_energy_from_strain(strain_and_disps_vec)

        # Set atom positions of the last N-1 atoms to reference positions
        # plus displacements, keeping first atom fixed
        defpositions = self.refpositions.copy()
        for i in range(self.natoms - 1):
            disp = strain_and_disps_vec[(6 + i * 3) : (9 + i * 3)]
            defpositions[i + 1] += disp
        self.atoms.set_positions(defpositions)

        # Apply strain to cell scaling the atom positions
        self.atoms.set_cell(self.o_cell, scale_atoms=False)
        strain_vec = strain_and_disps_vec[0:6]
        strain_mat = self.voigt_to_matrix(strain_vec)
        old_cell = self.o_cell
        new_cell = old_cell + np.dot(old_cell, strain_mat)
        self.atoms.set_cell(new_cell, scale_atoms=True)

        # Compute energy
        energy = self.atoms.get_potential_energy()

        return energy / self.o_volume

    def get_elasticity_matrix_and_error_energy_full(
        self, step: Union[MaxStepGenerator, float]
    ) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
        """
        Compute elastic constants from the full Hessian
        relative to both strains and internal atom degrees of
        freedom. This is followed by an algebraic manipulation to
        account for the effect of atom relaxation on elastic
        constants.

        Returns:
            * 6x6 elasticity matrix in Voigt order
            * 6x6 error estimate in Voigt order
        """
        hess = ndt.Hessian(
            self.get_energy_from_strain_and_atom_displacements,
            step=step,
            full_output=True,
        )
        answer = hess(np.zeros(6 + (self.natoms - 1) * 3, dtype=float))
        # numdifftools 0.10 changed API of ndt.Jacobian and .Hessian
        try:
            fullhessian, info = answer
        except ValueError:
            fullhessian = answer.estimate
            info = answer
        hessian_error_estimate = info.error_estimate
        fullhessian_error_estimate = info.error_estimate
        # Separate full Hessian into blocks
        # (eps-eps, eps-disp, disp-disp)
        hess_ee = fullhessian[0:6, 0:6]
        hess_ed = fullhessian[0:6, 6:]
        hess_dd = fullhessian[6:, 6:]
        # Invert disp-disp block
        hess_dd_inv = np.linalg.inv(hess_dd)
        # Compute hessian accounting for basis atom relaxation. based
        # on Eqn (27) in Tadmor et al, Phys. Rev. B, 59:235-245, 1999.
        hessian = hess_ee - np.dot(np.dot(hess_ed, hess_dd_inv), np.transpose(hess_ed))
        # TODO: Figure out how to estimate error of Hessian based on
        #      full Hessian errors in fullhessian_error_estimate
        #      Now just taken errors for hess_ee which is incorrect.
        hessian_error_estimate = info.error_estimate[0:6, 0:6]
        return energy_hessian_add_prefactors(hessian, hessian_error_estimate)

    def get_energy_from_strain(self, strain_vec: npt.ArrayLike) -> float:
        """
        Compute reference strain energy density for a given applied strain.

        Parameters:
            strain_vec:
                A numpy array of length 6 containing the strain components in
                Voigt order

        Returns:
            energy density:
                Potential energy of the configuration divided by its reference
                (unstrained) volume
        """
        logger.info(f"Strain vector: {strain_vec}")

        self.atoms.set_cell(self.o_cell, scale_atoms=False)
        self.atoms.set_positions(self.refpositions)
        strain_mat = self.voigt_to_matrix(strain_vec)

        # Find the symmetry operations for the requested space group
        full_symmetry_ops = get_primitive_genpos_ops(self.sgnum)
        # Knock out things that don't commute with the deformation
        strain_norm = np.linalg.norm(strain_vec)
        # Everything commutes with the identity, no need to change symm at all
        if np.isclose(strain_norm, 0.0):
            symm_ops = full_symmetry_ops
        else:
            symm_ops = []
            deform_direction_mat = np.eye(3) + strain_mat / strain_norm
            for op in full_symmetry_ops:
                cart_rot = fractional_to_cartesian_itc_rotation_from_ase_cell(
                    op["W"], self.o_cell
                )
                if np.allclose(
                    cart_rot @ deform_direction_mat,
                    deform_direction_mat @ cart_rot,
                ):
                    symm_ops.append(op)
        symm = FixProvidedSymmetry(self.atoms, symm_ops)

        old_cell = self.o_cell
        new_cell = old_cell + np.dot(old_cell, strain_mat)
        self.atoms.set_cell(new_cell, scale_atoms=True)

        if self.natoms > 1:
            minimize_wrapper(
                self.atoms,
                fmax=self.fmax,
                steps=self.steps,
                variable_cell=False,
                logfile=None,
                algorithm=self.algorithm,
                fix_symmetry=symm,
                opt_kwargs=self.opt_kwargs,
            )
            energy = self.atoms.get_potential_energy()
        else:
            energy = self.atoms.get_potential_energy()

        # check that symmetry restriction is working properly and not
        # preventing cell from changing
        assert np.allclose(self.atoms.get_cell(), new_cell)

        return energy / self.o_volume

    def get_elasticity_matrix_and_error_energy_condensed(
        self, step: Union[MaxStepGenerator, float]
    ) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
        """
        Compute elastic constants from the Hessian
        of the condensed strain energy density (i.e. the enregy for
        a given strain is relaxed with respect to internal atom
        positions)

        Returns:
            * 6x6 elasticity matrix in Voigt order
            * 6x6 error estimate in Voigt order
        """
        hess = ndt.Hessian(self.get_energy_from_strain, step=step, full_output=True)
        answer = hess(np.zeros(6, dtype=float))
        # numdifftools 0.10 changed API of ndt.Jacobian and .Hessian
        try:
            hessian, info = answer
        except ValueError:
            hessian = answer.estimate
            info = answer
        return energy_hessian_add_prefactors(hessian, info.error_estimate)

    def get_stress_from_strain(self, strain_vec: npt.ArrayLike) -> npt.ArrayLike:
        """
        Compute stress for a given applied strain.

        Parameters:
            strain_vec:
                A numpy array of length 6 containing the strain components in
                Voigt order

        Returns:
            stress:
                Cauchy stress of the configuration
        """
        # Call get_energy_from_strain to strain the
        # atoms
        _ = self.get_energy_from_strain(strain_vec)
        stress = self.atoms.get_stress()
        return stress

    def get_elasticity_matrix_and_error_stress(
        self, step: Union[MaxStepGenerator, float]
    ) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
        """
        Compute elastic constants from the Jacobian
        of the condensed stress (i.e. the stress for a given strain
        where the energy is relaxed with respect to internal atom
        positions)

        Returns:
            * 6x6 elasticity matrix in Voigt order
            * 6x6 error estimate in Voigt order
        """
        jac = ndt.Jacobian(self.get_stress_from_strain, step=step, full_output=True)
        answer = jac(np.zeros(6, dtype=float))
        # numdifftools 0.10 changed API of ndt.Jacobian and .Hessian
        try:
            hessian, info = answer
        except ValueError:
            hessian = answer.estimate
            info = answer
        hessian_error_estimate = info.error_estimate

        elastic_constants = np.zeros(shape=(6, 6))
        error_estimate = np.zeros(shape=(6, 6))

        # Hessian was computed as d sig_m / d eps_n.
        # As noted in the module doc string, a prefactor is required for some terms
        # to obtain the elastic constants
        for m in range(6):
            for n in range(6):
                if n < 3:
                    fact = 1.0
                else:
                    fact = 0.5
                elastic_constants[m, n] = fact * hessian[m, n]
                error_estimate[m, n] = fact * hessian_error_estimate[m, n]
        # The elastic constants matrix should be symmetric, however due to
        # numerical precision issues in the stress components, in general,
        # d sig m / d eps_n will not equal d sig_n / d eps_m.
        # To address this, symmetrize the elastic constants matrix.
        for m in range(5):
            for n in range(m + 1, 6):
                con = 0.5 * (elastic_constants[m, n] + elastic_constants[n, m])
                # Variances of a linear combination sum as the square of the
                # coefficient
                err = math.sqrt(
                    0.25 * (error_estimate[m, n] ** 2 + error_estimate[n, m] ** 2)
                )
                elastic_constants[m, n] = con
                elastic_constants[n, m] = con
                error_estimate[m, n] = err
                error_estimate[n, m] = err

        return elastic_constants, error_estimate

    def results(
        self,
        method: str = "energy-condensed",
        step: Union[MaxStepGenerator, float] = MaxStepGenerator(
            base_step=1e-4,
            num_steps=14,
            use_exact_steps=True,
            step_ratio=1.6,
            offset=0,
        ),
    ) -> Tuple[
        npt.ArrayLike,
        npt.ArrayLike,
        str,
    ]:
        """
        Compute the elastic constants of a crystal using numerical differentiation

        Parameters:
            method:
                Select method for computing the elastic constants. The following
                methods are supported:
                'energy-condensed' : Compute elastic constants from the Hessian
                    of the condensed strain energy density (i.e. the enregy for
                    a given strain is relaxed with respect to internal atom
                    positions)
                'stress-condensed' : Compute elastic constants from the Jacobian
                    of the condensed stress (i.e. the stress for a given strain
                    where the energy is relaxed with respect to internal atom
                    positions)
                'energy-full' : Compute elastic constants from the full Hessian
                    relative to both strains and internal atom degrees of
                    freedom. This is followed by an algebraic manipulation to
                    account for the effect of atom relaxation on elastic
                    constants.
                In general, 'energy-condensed' is the preferred method.
                The 'stress-condensed' method is much faster, but generally less
                accurate. The 'energy-full' method has accuracy comparable
                to 'energy-condensed' but tends to be much slower due to the
                larger Hessian matrix that has to be computed.
            step:
                Step(s) to pass to the numdifftools routines
        Returns:
            *   A 6x6 numpy array containing the elastic constants matrix
                in Voigt ordering. This is the full matrix of derivatives
                returned by numdifftools, with appropriate prefactors added
                for Voigt notation, but not yet corrected for material symmetry.
                Units are the default returned by the calculator.
            *   A 6x6 numpy array containing the 95% error in the elastic
                constants returned by numdifftools, with appropriate prefactors added
                for Voigt notation. Same units as elastic_constants.
            *   A summary of the run and any issues
        """
        if method == "stress-condensed":
            get_elasticity_matrix = self.get_elasticity_matrix_and_error_stress
        elif method == "energy-condensed":
            get_elasticity_matrix = (
                self.get_elasticity_matrix_and_error_energy_condensed
            )
        elif method == "energy-full":
            get_elasticity_matrix = self.get_elasticity_matrix_and_error_energy_full
        else:
            raise RuntimeError(
                "Unknown computation method. Supported methods: "
                "'energy-condensed','stress-condensed','energy-full'"
            )

        elastic_constants, elastic_constants_error_estimate = get_elasticity_matrix(
            step
        )

        message = (
            f"\nMethod: {method}\nStep generator: {step}\n\n"
            + "\nRaw elastic constants [ASE units]:\n"
            + np.array_str(
                elastic_constants,
                precision=5,
                max_line_width=100,
                suppress_small=True,
            )
            + "\n\n"
        )

        if isinstance(step, float):
            # When given a single float step,
            # we cannot give a meaningful error estimate
            elastic_constants_error_estimate = np.full((6, 6), np.nan)
        else:
            message = (
                message
                + "\n95%% Error estimate [ASE units]:\n"
                + np.array_str(
                    elastic_constants_error_estimate,
                    precision=5,
                    max_line_width=100,
                    suppress_small=True,
                )
                + "\n\n"
            )

        print()
        print("Summary of completed elastic constants calculation:")
        print(message)

        return (
            elastic_constants,
            elastic_constants_error_estimate,
            message,
        )
