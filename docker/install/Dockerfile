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

ARG PIP=pip3 --no-cache-dir
ARG PYTHON=python3
RUN ${PIP} install wheel==0.36.2
RUN ${PIP} install setuptools==54.0.0
RUN ${PIP} install packaging==20.9
RUN ${PIP} install markupsafe==2.0.1
RUN ${PIP} install Jinja2==2.11.3
RUN ${PIP} install edn_format==0.7.5
RUN ${PIP} install kim-edn==1.4.1
RUN ${PIP} install kim-property==2.6.4
RUN ${PIP} install kim-query==3.0.0
RUN ${PIP} install simplejson==3.17.2
RUN ${PIP} install numpy==1.19.5
RUN ${PIP} install scipy==1.5.4
RUN ${PIP} install matplotlib==3.7.1
RUN ${PIP} install pymongo==3.11.3
RUN ${PIP} install montydb==2.1.1
RUN ${PIP} install pybind11==2.6.2
RUN ${PIP} install spglib==2.1.0
RUN ${PIP} install numdifftools==0.9.41

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
ARG KIM_API_VER=2.3.0
ARG KIM_API_PACKAGE=kim-api-${KIM_API_VER}
ARG KIM_API_ARCHIVE_TXZ=${KIM_API_PACKAGE}.txz
RUN cd ${PACKAGE_DIR} \
 && wget -q https://s3.openkim.org/kim-api/${KIM_API_ARCHIVE_TXZ} \
 && tar xJf ${KIM_API_ARCHIVE_TXZ} \
 && rm ${KIM_API_ARCHIVE_TXZ} \
 && cd ${KIM_API_PACKAGE} \
 && mkdir build && cd build \
 && cmake .. -DCMAKE_BUILD_TYPE=Release \
 && make -j2 && make install \
 && cd ${PACKAGE_DIR} \
 && cp ${KIM_API_PACKAGE}/build/install_manifest.txt kim_api_install_manifest.txt \
 && rm -r ${KIM_API_PACKAGE} \
 && ldconfig

#########################################
## kimpy
#########################################
# NOTE: Must be installed after KIM API
RUN ${PIP} install kimpy==2.1.0

#########################################
## LAMMPS
#########################################
ARG DEBIAN_FRONTEND=noninteractive
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
      ../cmake \
 && make -j2 \
 && make install \
 && apt-get update -qq \
 && apt-get install --no-install-recommends -qqy python3-venv \
 && make install-python \
 && apt-get purge -y python3-venv \
 && apt-get clean \
 && rm -fr /var/lib/apt/lists/* \
 && ln -s /usr/local/bin/lmp /usr/local/bin/lammps \
 && rm -r /usr/local/share/lammps/potentials \
 && cd ${PACKAGE_DIR} \
 && rm -r ${PACKAGE_DIR}/lammps

#########################################
## OpenKIM ASE fork
#########################################
RUN cd ${PACKAGE_DIR}/ase/ \
 && ${PIP} install .

#########################################
## kim-python-utils
#########################################
RUN cd ${PACKAGE_DIR}/kim-python-utils \
 && ${PIP} install .
 
#########################################
## crystal-genome-util
#########################################
RUN cd ${PACKAGE_DIR}/crystal-genome-util \
 && ${PIP} install .

#########################################
## kim-tools
#########################################
RUN cd ${PACKAGE_DIR}/kim-tools \
 && ${PIP} install .

#########################################
## convergence
#########################################
RUN cd ${PACKAGE_DIR} \
 && tar xJf convergence.txz \
 && rm convergence.txz \
 && cd convergence \
 && ${PIP} install .

#########################################
## AFLOW
#########################################
ARG AFLOW_VER=3.2.14
ARG AFLOW_PACKAGE=aflow.${AFLOW_VER}
ARG AFLOW_ARCHIVE_TXZ=${AFLOW_PACKAGE}.tar.xz
RUN cd ${PACKAGE_DIR} \
 && wget -q http://materials.duke.edu/AFLOW/${AFLOW_ARCHIVE_TXZ} \
 && tar xJf ${AFLOW_ARCHIVE_TXZ} \
 && rm ${AFLOW_ARCHIVE_TXZ} \
 && cd ${AFLOW_PACKAGE} \
 && make -j2 aflow \
 && cp aflow /usr/local/bin \
 && touch /usr/local/bin/aflow_data \
 && chmod +x /usr/local/bin/aflow_data \
 && cd ${PACKAGE_DIR} \
 && rm -r ${AFLOW_PACKAGE}
