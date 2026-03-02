#!/bin/bash -l
#PBS -N test_gpu_debug
#PBS -l walltime=00:20:00
#PBS -l mem=16gb
#PBS -l ncpus=1
#PBS -l ngpus=1
#PBS -j eo
#PBS -m abe

cd "$PBS_O_WORKDIR"

# 1. Load Modules
module load CUDA/12.6.0
module load cuDNN/9.5.0.50-CUDA-12.6.0

# 2. Activate Environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate hieu_env_biorex

# 3. Resolve the libdevice path dynamically
# We look for where the actual .bc file is and point XLA directly to the PARENT of the nvvm folder.
BITCODE_PATH=$(find $CUDA_HOME -name "libdevice.10.bc" | head -n 1)
CUDA_NVVM_DIR=$(dirname $(dirname $BITCODE_PATH))

export XLA_FLAGS="--xla_gpu_cuda_data_dir=$CUDA_NVVM_DIR"

# 4. Suppress duplicate registration noise
# 1 = Info, 2 = Warning, 3 = Error. Setting to 2 or 3 hides the factory logs.
export TF_CPP_MIN_LOG_LEVEL=2

echo "--- Debug Info ---"
echo "CUDA_HOME: $CUDA_HOME"
echo "XLA_DIR set to: $CUDA_NVVM_DIR"
echo "------------------"

# 5. Run a more robust Python check
python - <<'PY'
import os
import tensorflow as tf

print(f"TensorFlow Version: {tf.__version__}")
print(f"Visible Devices: {tf.config.list_physical_devices('GPU')}")

# Test XLA Compilation
@tf.function(jit_compile=True)
def test_op(a, b):
    return a * b + a

try:
    val = test_op(tf.constant([1.0, 2.0]), tf.constant([3.0, 4.0]))
    print(f"XLA Result: {val.numpy()}")
    print("XLA Compilation: SUCCESS")
except Exception as e:
    print(f"XLA Compilation: FAILED\n{e}")
PY