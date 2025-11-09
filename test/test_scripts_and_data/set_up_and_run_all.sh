#!/bin/bash

date
pipeline-database set local
date


# Need models that support Si and an FCC metal to get max coverage of tests
date
kimitems install -D  MEAM_LAMMPS_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__MO_262519520678_002
date

date
kimitems install Sim_LAMMPS_MEAM_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__SM_656517352485_000
date


# This is for testing failure-to-match based on special-purpose logic
date
kimitems install Sim_LAMMPS_IFF_CHARMM_GUI_HeinzLinMishra_2023_Nanomaterials__SM_232384752957_000
date


# ASE TDs
date
kimitems install -D LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_007
date

date
kimitems install -D ElasticConstantsCubic_fcc_Cu__TE_188557531340_006
date

date
kimitems install -D EquilibriumCrystalStructure_A15B4_cI76_220_ae_c_CuSi__TE_684342186166_003
date

date
kimitems install -D LatticeConstantHexagonalEnergy_hcp_Cu__TE_344176839725_005
date

date
kimitems install -D PhononDispersionCurve_fcc_Cu__TE_575177044018_004
date

date
kimitems install -D SurfaceEnergyCubicCrystalBrokenBondFit_fcc_Cu__TE_689904280697_004
date


# LAMMPS TDs
date
kimitems install -D CohesiveEnergyVsLatticeConstant_fcc_Cu__TE_311348891940_004
date

date
kimitems install -D ClusterEnergyAndForces_3atom_Si__TE_002471259796_003
date

date
kimitems install -D TriclinicPBCEnergyAndForces_bcc2atom_Si__TE_006970922000_003
date


# Should fail to match with anything so far based on special-purpose logic even though species are supported
date
kimitems install -D EquilibriumCrystalStructure_Unconstrained_TypeLabels_PCFF_INTERFACE_Aluminum__TE_741008777397_000
date


# VCs
date
kimitems install -D InversionSymmetry__VC_021653764022_002
date

date
kimitems install -D Objectivity__VC_813478999433_002
date

date
kimitems install -D PeriodicitySupport__VC_895061507745_004
date

date
kimitems install -D PermutationSymmetry__VC_903502816694_002
date

date
kimitems install -D SpeciesSupportedAsStated__VC_651200051721_002
date

date
kimitems install -D ThreadSafety__VC_881176209980_005
date

date
kimitems install -D UnitConversion__VC_128739598203_001
date


date
pipeline-run-matches LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_007 -v
date


date
kimitems remove -f LatticeConstantCubicEnergy_fcc_Cu__TE_387272513402_007
date


date
pipeline-run-matches MEAM_LAMMPS_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__MO_262519520678_002 -v 
date

date
pipeline-run-matches Sim_LAMMPS_MEAM_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__SM_656517352485_000 -v
date


# Should not match with anything
date
pipeline-run-matches Sim_LAMMPS_IFF_CHARMM_GUI_HeinzLinMishra_2023_Nanomaterials__SM_232384752957_000 -v
date


date
kimitems install Sim_LAMMPS_IFF_PCFF_HeinzMishraLinEmami_2015Ver1v5_FccmetalsMineralsSolventsPolymers__SM_039297821658_001
date


# Should match with one test
date
pipeline-run-matches Sim_LAMMPS_IFF_PCFF_HeinzMishraLinEmami_2015Ver1v5_FccmetalsMineralsSolventsPolymers__SM_039297821658_001 -v
date


# Not included TDs and VCs, and why:
#	DislocationCoreEnergyCubic__TD_452950666597_002	Slow
#	ElasticConstantsFirstStrainGradient__TD_361847723785_001	No tests
#	ElasticConstantsHexagonal__TD_612503193866_004	Broken
#	GrainBoundaryCubicCrystalSymmetricTiltRelaxedEnergyVsAngle__TD_410381120771_003	Slow
#	LammpsExample2__TD_887699523131_002	No tests
#	LammpsExample__TD_567444853524_004	Outdated
#	LatticeConstant2DHexagonalEnergy__TD_034540307932_002	Only one test, Carbon-only
#	LinearThermalExpansionCoeffCubic__TD_522633393614_002	Slow
#   VacancyFormationMigration__TD_554849987965_001 Slow
#   VacancyFormationEnergyRelaxationVolume__TD_647413317626_001 Slow
#	StackingFaultFccCrystal__TD_228501831190_002	Slow and broken
#   ForcesNumerDeriv__VC_710586816390_003 Slow
#   MemoryLeak__VC_561022993723_004 Slow, not very informative
#   DimerContinuityC1__VC_303890932454_005 Slow

# Test database commands
date
pipeline-database dump $HOME/tmp.bson
date

date
pipeline-database delete -f
date

date
pipeline-database restore $HOME/tmp.bson
date

date
pipeline-database export $HOME/tmp.json
date

date
pipeline-database delete -f
date

date
pipeline-database import $HOME/tmp.json
date
