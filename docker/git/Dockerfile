#
# Copyright (c) 2018-2021, Regents of the University of Minnesota. All rights
# reserved.
#
# This software may be distributed as-is, without modification.
#
FROM ubuntu:20.04

ARG PACKAGE_DIR=/pipeline/packages/
RUN mkdir -p ${PACKAGE_DIR}
RUN apt-get -qq update
RUN apt-get install --no-install-recommends -qqy ca-certificates
RUN apt-get install --no-install-recommends -qqy git
RUN git clone -q https://github.com/openkim/numdifftools -b openkim-master ${PACKAGE_DIR}/numdifftools \
  && cd ${PACKAGE_DIR}/numdifftools \
  && git checkout a53debb144ed02c5c6eb74d5c18d53058259f27c \
  && cd ${PACKAGE_DIR}
RUN git clone -q https://github.com/openkim/kim-python-utils -b master ${PACKAGE_DIR}/kim-python-utils \
  && cd ${PACKAGE_DIR}/kim-python-utils \
  && git checkout 0fdeaf2c0ab4704f1789c57c4abe3026a55ff03b
RUN git clone -q https://github.com/lammps/lammps -b patch_30Jul2021 ${PACKAGE_DIR}/lammps
RUN git clone -q https://gitlab.com/openkim/ase -b user-species ${PACKAGE_DIR}/ase \
  && cd ${PACKAGE_DIR}/ase \
  && git checkout 94c6ad70814965408a2977f7428b62271988619c
RUN git clone -q https://gitlab.com/micronano_public/MDpp -b release ${PACKAGE_DIR}/MD++ \
  && cd ${PACKAGE_DIR}/MD++ \
  && git checkout f7d64a7720a4bc1602371a128c8db7779fcf8dcb
