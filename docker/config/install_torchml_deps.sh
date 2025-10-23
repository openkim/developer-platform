#!/usr/bin/bash

# Set up CUDA repo and install CUDA and set paths
# wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
# sudo dpkg -i cuda-keyring_1.0-1_all.deb
# sudo apt update
# sudo apt install cuda-toolkit-11-7 unzip --no-install-recommends
# rm cuda-keyring_1.0-1_all.deb
export PATH=$PATH:/usr/local/cuda/bin
echo 'export PATH=$PATH:/usr/local/cuda/bin' >> /home/openkim/.bashrc


# Get cuDNN archive and set paths
wget https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/linux-x86_64/cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz
tar -xf cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz
rm cudnn-linux-x86_64-8.9.7.29_cuda11-archive.tar.xz
mv cudnn-linux-x86_64-8.9.7.29_cuda11-archive cudnn
export CUDNN_ROOT=/home/openkim/cudnn
echo "export CUDNN_ROOT=$CUDNN_ROOT" >> /home/openkim/.bashrc

# Get libtorch archive and set paths
wget https://download.pytorch.org/libtorch/cu117/libtorch-cxx11-abi-shared-with-deps-1.13.0%2Bcu117.zip
unzip libtorch-cxx11-abi-shared-with-deps-1.13.0+cu117.zip 
rm libtorch-cxx11-abi-shared-with-deps-1.13.0+cu117.zip 
export TORCH_ROOT=/home/openkim/libtorch
TORCH_LIB=/home/openkim/libtorch/lib
TORCH_INCLUDE=/home/openkim/libtorch/include
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TORCH_LIB
export INCLUDE=$INCLUDE:$TORCH_INCLUDE
echo "export TORCH_ROOT=$TORCH_ROOT" >> /home/openkim/.bashrc
echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$TORCH_LIB" >> /home/openkim/.bashrc
echo "export INCLUDE=\$INCLUDE:$TORCH_INCLUDE" >> /home/openkim/.bashrc

# Clone, build, and configure pytorch_scatter with WITH_CUDA=on
git clone --recurse-submodules https://github.com/rusty1s/pytorch_scatter
cd pytorch_scatter && git checkout fa4f442952955acf8fe9fcfb98b600f6ca6081b6 && cd ..
mkdir build_scatter && cd build_scatter
cmake -DWITH_CUDA=on -DCMAKE_PREFIX_PATH="${TORCH_ROOT}" -DCMAKE_INSTALL_PREFIX="" -DCUDNN_INCLUDE_PATH="${CUDNN_ROOT}/include" -DCUDNN_LIBRARY_PATH="${CUDNN_ROOT}/lib/libcudnn.so" -DCMAKE_BUILD_TYPE=Release ../pytorch_scatter
make -j4 install DESTDIR="../pytorch_scatter/install"
LIB_DIR_NAME="lib"
CMAKE_DIR_NAME="share/cmake"
export TorchScatter_ROOT=/home/openkim/pytorch_scatter/install
TorchScatter_LIB=/home/openkim/pytorch_scatter/install/$LIB_DIR_NAME
TorchScatter_INCLUDE=/home/openkim/pytorch_scatter/install/include
export TorchScatter_DIR=/home/openkim/pytorch_scatter/install/$CMAKE_DIR_NAME
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TorchScatter_LIB
export INCLUDE=\$INCLUDE:$TorchScatter_INCLUDE
echo "export TorchScatter_ROOT=$TorchScatter_ROOT" >> /home/openkim/.bashrc
echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$TorchScatter_LIB" >> /home/openkim/.bashrc
echo "export INCLUDE=\$INCLUDE:$TorchScatter_INCLUDE" >> /home/openkim/.bashrc
echo "export TorchScatter_DIR=$TorchScatter_DIR" >> /home/openkim/.bashrc
cd ..

# Clone, build, and configure pytorch_sparse with WITH_CUDA=on
git clone --recurse-submodules https://github.com/rusty1s/pytorch_sparse
cd pytorch_sparse && git checkout e55e8331ef2881b934036054cbcd39f8efcd4725 && cd ..
mkdir build_sparse && cd build_sparse
cmake -DWITH_CUDA=on -DCMAKE_PREFIX_PATH="${TORCH_ROOT}" -DCMAKE_INSTALL_PREFIX="" -DCUDNN_INCLUDE_PATH="${CUDNN_ROOT}/include" -DCUDNN_LIBRARY_PATH="${CUDNN_ROOT}/lib/libcudnn.so" -DCMAKE_BUILD_TYPE=Release ../pytorch_sparse
make -j4 install  DESTDIR="../pytorch_sparse/install"
export TorchSparse_ROOT=/home/openkim/pytorch_sparse/install
TorchSparse_LIB=/home/openkim/pytorch_sparse/install/$LIB_DIR_NAME
TorchSparse_INCLUDE=/home/openkim/pytorch_sparse/install/include
export TorchSparse_DIR=/home/openkim/pytorch_sparse/install/$CMAKE_DIR_NAME
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TorchSparse_LIB
export INCLUDE=$INCLUDE:$TorchSparse_INCLUDE
echo "export TorchSparse_ROOT=$TorchSparse_ROOT" >> /home/openkim/.bashrc
echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$TorchSparse_LIB" >> /home/openkim/.bashrc
echo "export INCLUDE=\$INCLUDE:$TorchSparse_INCLUDE" >> /home/openkim/.bashrc
echo "export TorchSparse_DIR=$TorchSparse_DIR" >> /home/openkim/.bashrc
cd ..

# Download TorchML driver, patch the CMakeLists to disable the CUDA architecture
# detection in Caffe that was causing the CUDA98 dialect error and build
# for common architectures (which is what we want for portability anyway), and build
cd model-drivers && kimitems download TorchML__MD_173118614730_001
tar -xf TorchML__MD_173118614730_001.txz && rm TorchML__MD_173118614730_001.txz && cd TorchML__MD_173118614730_001
awk 'NR==2{print "set(TORCH_CUDA_ARCH_LIST Common)"}1' CMakeLists.txt > CMakeLists.txt_
mv CMakeLists.txt_ CMakeLists.txt
kimitems build -v TorchML__MD_173118614730_001
