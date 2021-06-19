ARG IMAGE_MINIMAL

FROM ${IMAGE_MINIMAL}

# Temporarily switch to root to do system-wide installs
USER root

# Install apt packages
# (libgl1-mesa-glx and libfontconfig are for qt/pyside/ovito)
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq \
 && apt-get install --no-install-recommends -qqy libgl1 libfontconfig1 \
 && apt-get clean \
 && rm -fr /var/lib/apt/lists/*

#########################################
## OVITO
#########################################
ARG PIP=pip3 --no-cache-dir
RUN ${PIP} install PySide2==5.15.2

# Disable dependencies to avoid upgrading numpy unnecessarily
RUN ${PIP} install --no-dependencies ovito==3.4.3

# Revert to user 'openkim'
USER openkim
WORKDIR /home/openkim/
