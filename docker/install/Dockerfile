#
# Copyright (c) 2018-2022, Regents of the University of Minnesota. All rights
# reserved.
#
# This software may be distributed as-is, without modification.
#
ARG IMAGE_GIT
ARG IMAGE_SYS

# Import all necessary git packages
FROM ${IMAGE_GIT} AS git

# Import all sys-level libs/utils
FROM ${IMAGE_SYS}

# Staging point for source code and/or build artifacts between images
ARG PACKAGE_DIR=/pipeline/packages/

# Copy packages fetched via git
COPY --from=git ${PACKAGE_DIR} ${PACKAGE_DIR}

# Copy static local packages
COPY packages/convergence.txz ${PACKAGE_DIR}

# Symlinks
RUN if [ ! -f "/usr/bin/python" ]; then \
  ln -fs /usr/bin/python3 /usr/bin/python; \
  fi
RUN if [ ! -f "/usr/bin/pip" ]; then \
  ln -fs /usr/bin/pip3 /usr/bin/pip; \
  fi

ARG PIP_INSTALL="pip3 --no-cache-dir install --break-system-packages"
ARG PYTHON=python3

# Breaking changes in setuptools and packaging 
# are exceedingly rare, I am comfortable setting
# them to latest.
RUN ${PIP_INSTALL} --upgrade setuptools
RUN ${PIP_INSTALL} packaging
RUN ${PIP_INSTALL} markupsafe==2.0.1
RUN ${PIP_INSTALL} Jinja2==2.11.3
RUN ${PIP_INSTALL} edn_format==0.7.5
RUN ${PIP_INSTALL} kim-edn==1.6.0
RUN ${PIP_INSTALL} kim-property==2.7.0
RUN ${PIP_INSTALL} kim-query==4.0.0
RUN ${PIP_INSTALL} simplejson==3.17.2
RUN ${PIP_INSTALL} numpy==1.26.4
RUN ${PIP_INSTALL} scipy==1.15.3
RUN ${PIP_INSTALL} matplotlib==3.8.3
RUN ${PIP_INSTALL} pymongo==3.11.3
RUN ${PIP_INSTALL} montydb==2.5.3
RUN ${PIP_INSTALL} pybind11==2.6.2
RUN ${PIP_INSTALL} numdifftools==0.9.41
RUN ${PIP_INSTALL} kim-convergence==0.1.0
RUN ${PIP_INSTALL} pymatgen==2025.10.7
RUN ${PIP_INSTALL} findiff==0.12.1

#########################################
## OpenMPI
#########################################
ARG OPENMPI_MINOR_VER=5.0
ARG OPENMPI_FULL_VER=5.0.8
ARG OPENMPI_PACKAGE=openmpi-${OPENMPI_FULL_VER}
ARG OPENMPI_ARCHIVE_TXZ=${OPENMPI_PACKAGE}.tar.gz
RUN cd ${PACKAGE_DIR} \
 && wget -q https://download.open-mpi.org/release/open-mpi/v${OPENMPI_MINOR_VER}/${OPENMPI_ARCHIVE_TXZ} \
 && tar xzf ${OPENMPI_ARCHIVE_TXZ} \
 && rm ${OPENMPI_ARCHIVE_TXZ} \
 && cd ${OPENMPI_PACKAGE} \
 && ./configure \
 && make -j4 && make install \
 && cd ${PACKAGE_DIR} \
 && rm -r ${OPENMPI_PACKAGE}

#########################################
## MD++
#########################################
# Alterations we make to install MD++
# 1. Change "SPEC = " -> "SPEC = -DNO_X11" in makefile
# 2. Change "TCL = yes" -> "TCL = no" in src/Makefile
# 3. Change "XLIBS=$(XLIBS.$(SYS))" -> "XLIBS=" in src/Makefile.base
RUN cd ${PACKAGE_DIR}/MD++ \
 && mkdir bin \
 && sed -i 's/SPEC = /SPEC = -DNO_X11/g' makefile \
 && sed -i 's/TCL = yes/TCL = no/g' src/Makefile \
 && sed -i 's/XLIBS=$(XLIBS.$(SYS))/XLIBS=/g' src/Makefile.base \
 && make -j4 md build=R \
 && cp bin/md_gpp /usr/local/bin \
 && cd ${PACKAGE_DIR} \
 && rm -r MD++

#########################################
## KIM API
#########################################
ARG KIM_API_VER=2.4.2
ARG KIM_API_PACKAGE=kim-api-${KIM_API_VER}
ARG KIM_API_ARCHIVE_TXZ=${KIM_API_PACKAGE}.txz
RUN cd ${PACKAGE_DIR} \
 && wget -q https://s3.openkim.org/kim-api/${KIM_API_ARCHIVE_TXZ} \
 && tar xJf ${KIM_API_ARCHIVE_TXZ} \
 && rm ${KIM_API_ARCHIVE_TXZ} \
 && cd ${KIM_API_PACKAGE} \
 && mkdir build && cd build \
 && cmake .. -DCMAKE_BUILD_TYPE=Release \
 && make -j4 && make install \
 && cd ${PACKAGE_DIR} \
 && cp ${KIM_API_PACKAGE}/build/install_manifest.txt kim_api_install_manifest.txt \
 && rm -r ${KIM_API_PACKAGE} \
 && ldconfig

#########################################
## kimpy
#########################################
# NOTE: Must be installed after KIM API
RUN ${PIP_INSTALL} kimpy==2.1.4

#########################################
## LAMMPS
#########################################
RUN cd ${PACKAGE_DIR}/lammps/ \
 && mkdir build && cd build \
 && cmake \
      -D CMAKE_BUILD_TYPE=Release \
      -D CMAKE_INSTALL_PREFIX=/usr/local/ \
      -D CMAKE_TUNE_FLAGS="-march=x86-64 -mtune=generic" \
      -D BUILD_SHARED_LIBS=yes \
      -D BUILD_MPI=yes \
      -D LAMMPS_EXCEPTIONS=yes \
      -D PKG_KIM=yes \
      -D PKG_KSPACE=yes \
      -D PKG_MANYBODY=yes \
      -D PKG_MOLECULE=yes \
      -D PKG_CLASS2=yes \
      -D PKG_PYTHON=yes \
      -D PKG_ML-SNAP=yes \
      -D PKG_MGPT=yes \
      -D PKG_MEAM=yes \
      -D PKG_REAXFF=yes \
      -D PKG_MISC=yes \
      -D PKG_SMTBQ=yes \
      -D PKG_EXTRA-PAIR=yes \
      -D PKG_CORESHELL=yes \
      -D PKG_EXTRA-FIX=yes \
      -D PKG_ML-PACE=yes \
      ../cmake \
 && make -j4 \
 && make install \
 && mkdir -p ~/.config/pip \
 && echo "[global]" >> ~/.config/pip/pip.conf \
 && echo "break-system-packages = true" >> ~/.config/pip/pip.conf \
 && make install-python \
 && ln -s /usr/local/bin/lmp /usr/local/bin/lammps \
 && rm -r /usr/local/share/lammps/potentials \
 && cd ${PACKAGE_DIR} \
 && rm -r ${PACKAGE_DIR}/lammps \
 && rm -r ~/.config

#########################################
## OpenKIM ASE fork
#########################################
RUN cd ${PACKAGE_DIR}/ase/ \
 && ${PIP_INSTALL} . \
 && cd ${PACKAGE_DIR} \
 && rm -r ${PACKAGE_DIR}/ase

#########################################
## kim-tools, kimvv. Install after
## most Python reqs (incl LAMMPS and ASE)
## are explicitly satisfied
#########################################
RUN ${PIP_INSTALL} kim-tools==0.4.15
RUN ${PIP_INSTALL} kimvv==0.1.13

#########################################
## kim-python-utils
#########################################
RUN cd ${PACKAGE_DIR}/kim-python-utils \
 && ${PIP_INSTALL} . \
 && cd ${PACKAGE_DIR} \
 && rm -r ${PACKAGE_DIR}/kim-python-utils
 
###################################################
## convergence -- legacy version of kim-convergence
###################################################
# RUN cd ${PACKAGE_DIR} \
# && tar xJf convergence.txz \
# && rm convergence.txz \
# && cd convergence \
# && ${PIP_INSTALL} . \
# && cd ${PACKAGE_DIR} \
# && rm -r ${PACKAGE_DIR}/convergence

#########################################
## AFLOW
#########################################
ARG AFLOW_VER=4.1
ARG AFLOW_ARCHIVE=aflow-${AFLOW_VER}-ubuntu24-amd64.tar.gz
ARG AFLOW_URL=https://github.com/aflow-org/aflow/releases/download/v${AFLOW_VER}/${AFLOW_ARCHIVE}
ARG AFLOW_DIR_VER=4.1.0
ARG AFLOW_DIR=aflow-${AFLOW_DIR_VER}-Linux
ARG AFLOW_EXEC=${AFLOW_DIR}/bin/aflow
RUN cd ${PACKAGE_DIR} \
 && wget -q ${AFLOW_URL} \
 && tar xf ${AFLOW_ARCHIVE} \
 && rm ${AFLOW_ARCHIVE} \
 && cp ${AFLOW_EXEC} /usr/local/bin \
 && cd ${PACKAGE_DIR} \
 && rm -r ${PACKAGE_DIR}/${AFLOW_DIR}

#########################################
## Clean up packages that are unneeded after install
#########################################
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get purge -y python3-venv