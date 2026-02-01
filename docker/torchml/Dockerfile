ARG IMAGE_MINIMAL

FROM ${IMAGE_MINIMAL}

# Temporarily switch to root to do system-wide installs
USER root

# Install apt packages for CUDA (and unzip -- could theoretically delete it after but who cares, it's 30KB in a 10GB image)
ARG DEBIAN_FRONTEND=noninteractive
ENV CUDA_MAJOR_VER=11
ENV CUDA_MINOR_VER=7
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb \
 && dpkg -i cuda-keyring_1.0-1_all.deb \
 && apt-get update -qq \
 && apt-get install --no-install-recommends -qqy cuda-toolkit-${CUDA_MAJOR_VER}-${CUDA_MINOR_VER} unzip \
 && apt-get clean \
 && rm -fr /var/lib/apt/lists/*

ARG PACKAGE_DIR=/pipeline/packages/
RUN git clone -q --recurse-submodules https://github.com/rusty1s/pytorch_scatter -b master ${PACKAGE_DIR}/pytorch_scatter \
  && cd ${PACKAGE_DIR}/pytorch_scatter \
  && git checkout fa4f442952955acf8fe9fcfb98b600f6ca6081b6
RUN git clone -q --recurse-submodules https://github.com/rusty1s/pytorch_sparse -b master ${PACKAGE_DIR}/pytorch_sparse \
  && cd ${PACKAGE_DIR}/pytorch_sparse \
  && git checkout e55e8331ef2881b934036054cbcd39f8efcd4725

#########################################
## cuDNN
#########################################
ARG CUDNN_VER=8.9.7.29
ARG CUDNN_PACKAGE=cudnn-linux-x86_64-${CUDNN_VER}_cuda${CUDA_MAJOR_VER}-archive
ARG CUDNN_ARCHIVE_TXZ=${CUDNN_PACKAGE}.tar.xz
RUN cd ${PACKAGE_DIR} \
 && wget -q https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/linux-x86_64/${CUDNN_ARCHIVE_TXZ} \
 && tar xJf ${CUDNN_ARCHIVE_TXZ} \
 && rm ${CUDNN_ARCHIVE_TXZ} \
 && cp -r ${CUDNN_PACKAGE}/* /usr/local/ \
 && rm -r ${CUDNN_PACKAGE}
 
#########################################
## libtorch
#########################################
ARG LIBTORCH_VER=1.13.0
ARG LIBTORCH_ARCHIVE_ZIP=libtorch-cxx11-abi-shared-with-deps-${LIBTORCH_VER}+cu${CUDA_MAJOR_VER}${CUDA_MINOR_VER}.zip
RUN cd ${PACKAGE_DIR} \
 && wget -q https://download.pytorch.org/libtorch/cu117/libtorch-cxx11-abi-shared-with-deps-${LIBTORCH_VER}%2Bcu${CUDA_MAJOR_VER}${CUDA_MINOR_VER}.zip \
 && unzip ${LIBTORCH_ARCHIVE_ZIP} \
 && rm ${LIBTORCH_ARCHIVE_ZIP} \
 && rm libtorch/build-* \
 && cp -r libtorch/* /usr/local/ \
 && rm -r libtorch

# Add cuda to PATH
ENV PATH="$PATH:/usr/local/cuda/bin"

#########################################
## pytorch_scatter
#########################################
RUN cd ${PACKAGE_DIR}/pytorch_scatter/ \
 && mkdir build && cd build \
 && cmake \
      -D CMAKE_BUILD_TYPE=Release \
      -D CMAKE_INSTALL_PREFIX=/usr/local/ \
      -DWITH_CUDA=on \
      -DTORCH_CUDA_ARCH_LIST=Common \
      .. \
 && make -j4 install
# TODO: I believe some files are needed for include, but others should be cleaned up

#########################################
## pytorch_sparse
#########################################
RUN cd ${PACKAGE_DIR}/pytorch_sparse/ \
 && mkdir build && cd build \
 && cmake \
      -D CMAKE_BUILD_TYPE=Release \
      -D CMAKE_INSTALL_PREFIX=/usr/local/ \
      -DWITH_CUDA=on \
      -DTORCH_CUDA_ARCH_LIST=Common \
      .. \
 && make -j4 install
# TODO: I believe some files are needed for include, but others should be cleaned up

RUN ldconfig

# Build Torch libraries for common Nvidia configs by default
ENV TORCH_CUDA_ARCH_LIST=Common

# Revert to user 'openkim'
USER openkim
WORKDIR /home/openkim/
