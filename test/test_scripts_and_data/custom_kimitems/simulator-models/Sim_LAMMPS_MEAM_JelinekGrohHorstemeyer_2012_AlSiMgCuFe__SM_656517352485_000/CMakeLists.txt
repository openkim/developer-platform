#
# Required preamble
#

cmake_minimum_required(VERSION 3.4...3.10)
list(APPEND CMAKE_PREFIX_PATH $ENV{KIM_API_CMAKE_PREFIX_DIR})
find_package(KIM-API 2.0 REQUIRED CONFIG)
if(NOT TARGET kim-api)
  enable_testing()
  project("${KIM_API_PROJECT_NAME}" VERSION "${KIM_API_VERSION}"
    LANGUAGES CXX C Fortran)
endif()

# End preamble


add_kim_api_model_library(
  NAME            "Sim_LAMMPS_MEAM_JelinekGrohHorstemeyer_2012_AlSiMgCuFe__SM_656517352485_000"
  SM_SPEC_FILE    "smspec.edn"
  PARAMETER_FILES "library.meam"
                  "AlSiMgCuFe.meam"
  )
