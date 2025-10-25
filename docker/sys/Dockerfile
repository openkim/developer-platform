#
# Copyright (c) 2018-2022, Regents of the University of Minnesota. All rights
# reserved.
#
# This software may be distributed as-is, without modification.
#
FROM ubuntu:22.04

# This is the common base layer used for all user-facing kim environments,
# and includes all of the apt-get installs

## Install apt packages
ARG DEBIAN_FRONTEND=noninteractive
ENV CUDA_MAJOR_VER=11
ENV CUDA_MINOR_VER=7
RUN apt-get update -qq \
 && apt-get install --no-install-recommends -qqy apt-utils \
 sudo \
 time \
 tzdata \
 xxd \
 vim \
 xz-utils \
 ca-certificates \
 ssh \
 tar \
 wget \
 curl \
 libcurl4-openssl-dev \
 rsync \
 python3-dev \
 python3-pip \
 cmake \
 make \
 g++ \
 gfortran \
 units \
 pkg-config \
 valgrind \
 tree \
 libfreetype6-dev \
 git \
 python3-venv \
 unzip \
 && wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb \
 && dpkg -i cuda-keyring_1.0-1_all.deb \
 && apt-get update -qq \
 && apt-get install --no-install-recommends -qqy cuda-toolkit-${CUDA_MAJOR_VER}-${CUDA_MINOR_VER} \
 && apt-get clean \
 && rm -fr /var/lib/apt/lists/*
ENV PATH="$PATH:/usr/local/cuda/bin"