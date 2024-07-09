#
# Copyright (c) 2018-2022, Regents of the University of Minnesota. All rights
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
RUN git clone -q https://github.com/openkim/numdifftools -b master ${PACKAGE_DIR}/numdifftools \
  && cd ${PACKAGE_DIR}/numdifftools \
  && git checkout a53debb144ed02c5c6eb74d5c18d53058259f27c \
  && cd ${PACKAGE_DIR}
RUN git clone -q https://github.com/openkim/kim-python-utils -b master ${PACKAGE_DIR}/kim-python-utils \
  && cd ${PACKAGE_DIR}/kim-python-utils \
  && git checkout e4e21b202264373a9f33dfc47b6e05c0af625950
RUN git clone -q https://github.com/openkim/crystal-genome-util -b main ${PACKAGE_DIR}/crystal-genome-util \
  && cd ${PACKAGE_DIR}/crystal-genome-util \
  && git checkout e18a2d62fc3e391acbf9c98a28efaebca914b007
RUN git clone -q https://github.com/lammps/lammps -b stable_2Aug2023_update1 ${PACKAGE_DIR}/lammps
RUN git clone -q https://gitlab.com/openkim/ase -b user-species ${PACKAGE_DIR}/ase \
  && cd ${PACKAGE_DIR}/ase \
  && git checkout abe2d6c6e265f7ba6e79cc9b437ef1940731eccc
RUN git clone -q https://gitlab.com/micronano_public/MDpp -b release ${PACKAGE_DIR}/MD++ \
  && cd ${PACKAGE_DIR}/MD++ \
  && git checkout f7d64a7720a4bc1602371a128c8db7779fcf8dcb
RUN git clone -q https://github.com/openkim/kim-test-utils -b main ${PACKAGE_DIR}/kim-test-utils \
  && cd ${PACKAGE_DIR}/kim-test-utils \
  && git checkout 385b23d7b3f7b957dfc7cc609428e65824042dcf
