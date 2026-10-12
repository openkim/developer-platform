ElasticConstants Crystal Genome Test Driver
===========================================

Computes the elastic constants of an arbitrary crystal using numerical differentiation.
Reports the results as  the ``bulk-modulus-isothermal-npt`` and 
``elastic-constants-isothermal-npt`` OpenKIM Properties: https://openkim.org/properties.

The code also computes the distance from the obtained elasticity tensor to
the nearest isotropic tensor. This provides a measure of the anisotropy
of the crystal. Note that this calculation can fail if the elasticity tensor
is not positive definite.

The Test Driver computes the elastic constants as if the crystal was triclinic,
and then symmetrizes the result according to material symmetry. Both the raw
and material-symmetrized results are reported.
The errors reported by this Test Driver are the 95% errors reported by ``numdifftools``.
In order to compute the error in the material-symmetrized case, the raw components
are treated as independent random variables (only the upper triangle of the Voigt matrix,
as the Voigt matrix is symmetric). The components of the material-symmetrized
matrix are linear combinations of these random variables, and the error is summed
accordingly.

By default, the Test Driver attempts several computations until the extrapolation
error reported by ``numdifftools`` and the deviation from material symmetry 
are below the requested threshold. If no computation was below both thresholds,
the run with the smallest weighed error is chosen.

Test Driver invocation optional arguments
-----------------------------------------

If the ``method`` and/or ``strain_step`` arguments
are provided, only a single calculation is performed instead of the multiple
computations as described above. 

* ``method``:

   Three methods are available:

   #. ``energy-condensed`` : Compute elastic constants from the hessian of the 
      condensed strain energy density, W_eff(eps) = min_d W(eps,d), where d are
      the displacements of the internal atoms (aside from preventing rigid-body
      translation) and eps is the strain.
   #. ``stress-condensed`` : Compute elastic constants from the jacobian of the
      condensed stress, sig_eff(eps) = sig(eps,dmin), where dmin = arg min_d
      W(eps,d). 
   #. ``energy-full`` : Compute elastic constants from the hessian of the full
      strain energy density, W(eps,d). This involves an algebraic manipulation
      to account for the effect of atom relaxation; see eqn (27), in Tadmor et
      al, Phys. Rev. B, 59:235-245, 1999.

   For well-behaved potentials, all three methods give similar results with 
   differences beyond the first or second digit due to the numerical differentiation. 
   The ``energy-condensed`` and ``energy-full`` approaches have comparable accuracy, 
   but full Hessian is *much* slower. The ``stress-condensed`` approach is 
   significantly faster than ``energy-condensed``, but is less accurate. 

   For potentials with a rough energy landscape due to sharp cut-offs or
   electrostatics, ``stress-condensed`` is sometimes better behaved.

   The default approach is ``energy-condensed``. 

* ``strain_step``:

   The ``numdifftools.MaxStepGenerator`` or a single step to use for numerical
   differentiation. If a single step is provided, error will not be estimated.
   The default is:

   .. code-block:: python

      MaxStepGenerator(
         base_step=1e-4,
         num_steps=14,
         use_exact_steps=True,
         step_ratio=1.6,
         offset=0,
      )

* ``fmax``, ``steps``, ``algorithm``, ``fix_symmetry``, ``opt_kwargs``:

   These are passed to the following function to control minimization
   at each strain step:
   https://kim-tools.readthedocs.io/en/latest/kim_tools.test_driver.html#kim_tools.test_driver.core.minimize_wrapper

* ``extrap_tol_95``, ``matl_symm_tol``:

   If neither ``method`` nor ``strain_step`` are specified,
   these are the tolerances that will be used to threshold
   the 95% extrapolation error reported by
   numdifftools and the deviation from material symmetry,
   respectively. The norm of the error matrices in Kelvin
   form divided by the norm of the elasticity matrix in
   Kelvin form will be compared to these tolerances. 
   If no calculation attempt is below both thresholds,
   the sum of squares of the relative errors divided by their
   respective thresholds will be used to choose the run with
   the smallest combined error.