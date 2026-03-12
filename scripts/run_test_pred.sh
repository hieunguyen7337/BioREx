#!/bin/bash -l
#PBS -N biorex_pred_phos
#PBS -l walltime=10:00:00
#PBS -l mem=16gb
#PBS -l ncpus=1
#PBS -l ngpus=1
#PBS -j eo
#PBS -m abe

echo '================================================'
echo "CWD = ${PBS_O_WORKDIR}"
echo '================================================'
cd "$PBS_O_WORKDIR"

echo '=========='
echo 'Load CUDA & cuDNN modules'
echo '=========='
module load CUDA/12.6.0
module load cuDNN/9.5.0.50-CUDA-12.6.0

echo '=========='
echo 'Fix TensorFlow CUDA/XLA path issues'
echo '=========='

# Correct CUDA root path for XLA
export CUDA_DIR="${CUDA_HOME}"
export XLA_FLAGS="--xla_gpu_cuda_data_dir=${CUDA_HOME}"

# Disable XLA JIT to avoid long startup hangs
export TF_XLA_FLAGS="--tf_xla_auto_jit=0"

# Prevent TensorFlow from allocating all GPU memory
export TF_FORCE_GPU_ALLOW_GROWTH=true

echo "CUDA_HOME=${CUDA_HOME}"
echo "XLA_FLAGS=${XLA_FLAGS}"
echo "TF_XLA_FLAGS=${TF_XLA_FLAGS}"

echo '=========='
echo 'Activate conda env'
echo '=========='
source ~/miniconda3/etc/profile.d/conda.sh
conda activate hieu_env_biorex

echo '=========='
echo 'Environment diagnostics'
echo '=========='

nvidia-smi || true
which python

echo "Testing TensorFlow import..."
python - <<EOF
import tensorflow as tf
print("TensorFlow version:", tf.__version__)
print("GPUs:", tf.config.list_physical_devices('GPU'))
EOF

echo '=========='
echo 'Prepare I/O variables'
echo '=========='

in_pubtator_file="datasets/Phos_dataset/phosphorylation_corpus.PubTator"
out_tsv_file="datasets/Phos_dataset/processed/test_for_Phos.tsv"
out_pubtator_file="predict.pubtator"
pre_train_model="biorex_model"

# Ensure TSV exists
if [ ! -s "${out_tsv_file}" ]; then
  echo "ERROR: ${out_tsv_file} was not found! Please run the preparation script first."
  exit 1
fi

# Respect GPU argument
GPU_INDEX="${1:-0}"
export CUDA_VISIBLE_DEVICES="$GPU_INDEX"

echo "Using GPU index: $CUDA_VISIBLE_DEVICES"

echo '========================='
echo 'Generating RE predictions'
echo '========================='
date

python src/run_ncbi_rel_exp.py \
  --task_name "biorex" \
  --test_file "${out_tsv_file}" \
  --use_balanced_neg false \
  --to_add_tag_as_special_token true \
  --model_name_or_path "${pre_train_model}" \
  --output_dir "biorex_model" \
  --num_train_epochs 10 \
  --per_device_train_batch_size 16 \
  --per_device_eval_batch_size 32 \
  --do_predict \
  --logging_steps 10 \
  --evaluation_strategy steps \
  --save_steps 10 \
  --overwrite_output_dir \
  --max_seq_length 512

echo '============'
echo 'Copy results'
echo '============'

if [[ -f "biorex_model/test_results.tsv" ]]; then
  cp "biorex_model/test_results.tsv" "out_biorex_results.tsv"
else
  echo "Expected predictions not found: biorex_model/test_results.tsv"
  exit 2
fi

echo '==========================================='
echo 'Convert predictions back to PubTator format'
echo '==========================================='

python src/utils/run_pubtator_eval.py \
  --exp_option 'to_pubtator' \
  --in_test_pubtator_file "${in_pubtator_file}" \
  --in_test_tsv_file "${out_tsv_file}" \
  --in_pred_tsv_file "out_biorex_results.tsv" \
  --out_pred_pubtator_file "${out_pubtator_file}"

echo 'Done.'
date