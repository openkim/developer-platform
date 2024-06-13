#!/bin/bash

pipeline-database set local

# Need models that support Si and an FCC metal to get max coverage of tests
kimitems install -D  MEAM_LAMMPS_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__MO_262519520678_002

# ASE TDs
kimitems install -D EquilibriumCrystalStructure_A15B4_cI76_220_ae_c_CuSi__TE_684342186166_002

pipeline-run-matches EquilibriumCrystalStructure_A15B4_cI76_220_ae_c_CuSi__TE_684342186166_002 -v
