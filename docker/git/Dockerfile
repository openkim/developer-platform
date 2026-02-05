#
# Copyright (c) 2018-2022, Regents of the University of Minnesota. All rights
# reserved.
#
# This software may be distributed as-is, without modification.
#
FROM ubuntu:22.04

ARG PACKAGE_DIR=/pipeline/packages/
RUN mkdir -p ${PACKAGE_DIR}
RUN apt-get -qq update
RUN apt-get install --no-install-recommends -qqy ca-certificates
RUN apt-get install --no-install-recommends -qqy git
RUN git clone -q https://github.com/openkim/kim-python-utils -b master ${PACKAGE_DIR}/kim-python-utils \
  && cd ${PACKAGE_DIR}/kim-python-utils \
  && git checkout 2aa7a7ee692fb0ecd895b2da338f5ae99b86ef53
RUN git clone -q https://github.com/openkim/crystal-genome-util -b main ${PACKAGE_DIR}/crystal-genome-util \
  && cd ${PACKAGE_DIR}/crystal-genome-util \
  && git checkout e18a2d62fc3e391acbf9c98a28efaebca914b007
RUN git clone -q https://github.com/lammps/lammps -b stable_22Jul2025_update1 ${PACKAGE_DIR}/lammps
RUN git clone -q https://gitlab.com/openkim/ase -b user-species ${PACKAGE_DIR}/ase \
  && cd ${PACKAGE_DIR}/ase \
  && git checkout 23b90a5461c21a8530c431629a1423dc1ce84b56
RUN git clone -q https://github.com/openkim/MDpp.git -b fix_species_added_atoms ${PACKAGE_DIR}/MD++ \
  && cd ${PACKAGE_DIR}/MD++ \
  && git checkout d2cf99f58aa342c06b73914a89f051761d6153c3
