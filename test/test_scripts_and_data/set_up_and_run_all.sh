#!/bin/bash

pipeline-database set local

# This set of calculation tests the ability of Test Drivers to run with
# both SMs and PMs, and the various pipeline matching utilities.
# It was written to use a minimal number of models, but it could
# probably stand to be rewritten to be faster by using
# calculations that have a lower usertime (which can be figured out
# by querying the database)

# Need models that support Si and an FCC metal to get max coverage of tests
kimitems install -D  MEAM_LAMMPS_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__MO_262519520678_
kimitems install Sim_LAMMPS_MEAM_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__SM_656517352485_

# This is for testing failure-to-match based on special-purpose logic
kimitems install Sim_LAMMPS_IFF_CHARMM_GUI_HeinzLinMishra_2023_Nanomaterials__SM_232384752957_

# ASE TDs
kimitems install -D LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_
kimitems install -D EquilibriumCrystalStructure_A15B4_cI76_220_ae_c_CuSi__TE_684342186166_
kimitems install -D LatticeConstantHexagonalEnergy_hcp_Cu__TE_344176839725_
kimitems install -D PhononDispersionCurve_fcc_Cu__TE_575177044018_
kimitems install -D SurfaceEnergyCubicCrystalBrokenBondFit_fcc_Cu__TE_689904280697_

# LAMMPS TDs
kimitems install -D CohesiveEnergyVsLatticeConstant_fcc_Cu__TE_311348891940_

# Should fail to match with anything so far based on special-purpose logic even though species are supported
kimitems install -D EquilibriumCrystalStructure_Unconstrained_TypeLabels_PCFF_INTERFACE_Aluminum__TE_741008777397_

# VCs
kimitems install -D InversionSymmetry__VC_021653764022_
kimitems install -D Objectivity__VC_813478999433_
kimitems install -D PeriodicitySupport__VC_895061507745_
kimitems install -D PermutationSymmetry__VC_903502816694_
kimitems install -D SpeciesSupportedAsStated__VC_651200051721_
kimitems install -D ThreadSafety__VC_881176209980_
kimitems install -D UnitConversion__VC_128739598203_

pipeline-run-matches LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_* -v

kimitems remove -f LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_

pipeline-run-matches MEAM_LAMMPS_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__MO_262519520678_* -v 
kimitems remove -f SurfaceEnergyCubicCrystalBrokenBondFit_fcc_Cu__TE_689904280697_ # Slow, no reason to test it twice
pipeline-run-matches Sim_LAMMPS_MEAM_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__SM_656517352485_* -v

# Should not match with anything
pipeline-run-matches Sim_LAMMPS_IFF_CHARMM_GUI_HeinzLinMishra_2023_Nanomaterials__SM_232384752957_* -v

kimitems install Sim_LAMMPS_IFF_PCFF_HeinzMishraLinEmami_2015Ver1v5_FccmetalsMineralsSolventsPolymers__SM_039297821658_

# Should match with one test -- CURRENTLY BROKEN, NOT INCLUDED IN THE REFERENCE DATABASE
pipeline-run-matches Sim_LAMMPS_IFF_PCFF_HeinzMishraLinEmami_2015Ver1v5_FccmetalsMineralsSolventsPolymers__SM_039297821658_* -v

# Additional one-off calculations, not part of the testing of matching logic
kimitems install -D LatticeConstantCubicEnergy_bcc_Mo__TE_279386991452_
kimitems install -D VacancyFormationMigration_bcc_Mo__TE_307021336684_
kimitems install -D EquilibriumCrystalStructure_A_cI2_229_a_Mo__TE_313831422432_
kimitems install -D ElasticConstantsCrystal_A_cI2_229_a_Mo__TE_397765171124_
kimitems install -D EAM_Dynamo_SmirnovaKuskinStarikov_2013_UMoXe__MO_679329885632_
pipeline-run-pair LatticeConstantCubicEnergy_bcc_Mo__TE_279386991452_* EAM_Dynamo_SmirnovaKuskinStarikov_2013_UMoXe__MO_679329885632_*
pipeline-run-pair VacancyFormationMigration_bcc_Mo__TE_307021336684_* EAM_Dynamo_SmirnovaKuskinStarikov_2013_UMoXe__MO_679329885632_*
pipeline-run-pair EquilibriumCrystalStructure_A_cI2_229_a_Mo__TE_313831422432_* EAM_Dynamo_SmirnovaKuskinStarikov_2013_UMoXe__MO_679329885632_*
pipeline-run-pair ElasticConstantsCrystal_A_cI2_229_a_Mo__TE_397765171124_* EAM_Dynamo_SmirnovaKuskinStarikov_2013_UMoXe__MO_679329885632_*

# Not included (non-discontinued) TDs and VCs, and why:
#	DislocationCoreEnergyCubic__TD_452950666597_002	Slow
#	ElasticConstantsFirstStrainGradient__TD_361847723785_001	No tests
#	GrainBoundaryCubicCrystalSymmetricTiltRelaxedEnergyVsAngle__TD_410381120771_003	Slow
#	LammpsExample2__TD_887699523131_002	No tests
#	LammpsExample__TD_567444853524_004	Outdated
#	LatticeConstant2DHexagonalEnergy__TD_034540307932_002	Only one test, Carbon-only
#	LinearThermalExpansionCoeffCubic__TD_522633393614_002	Runs on 5 CPUs, not available on Github runners
#	StackingFaultFccCrystal__TD_228501831190_002	Slow and broken
#   ForcesNumerDeriv__VC_710586816390_003 Slow
#   MemoryLeak__VC_561022993723_004 Slow, not very informative
#   DimerContinuityC1__VC_303890932454_005 Slow
#   A lot of Crystal Genome tests Slow, but we need to go through and add some nevertheless. Or create custom tests with fast settings
#   New VCs need to be added

# Test database commands
pipeline-database dump $HOME/tmp.bson
pipeline-database delete -f
pipeline-database restore $HOME/tmp.bson
pipeline-database export $HOME/tmp.json
pipeline-database delete -f
pipeline-database import $HOME/tmp.json