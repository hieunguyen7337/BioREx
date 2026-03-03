#!/bin/bash -l
#PBS -N biorex_pred_unified_ppi
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
echo 'Load CUDA & cuDNN modules (needed for libdevice)'
echo '=========='
module load CUDA/12.6.0
module load cuDNN/9.5.0.50-CUDA-12.6.0

# --- NEW: make TF/XLA find libdevice reliably ---
export CUDA_DIR="${CUDA_HOME}"
export XLA_FLAGS="--xla_gpu_cuda_data_dir=${CUDA_HOME}/nvvm/libdevice ${XLA_FLAGS:-}"
ln -sf "${CUDA_HOME}/nvvm/libdevice/libdevice.10.bc" "./libdevice.10.bc"  # satisfies './libdevice.10.bc'
# If you prefer to skip JIT entirely instead of using the symlink, comment the line above and use:
# export TF_XLA_FLAGS="--tf_xla_auto_jit=disabled"
# ------------------------------------------------

# (optional) quick sanity printout
echo "CUDA_HOME=${CUDA_HOME:-<unset>}"
if [[ -n "${CUDA_HOME:-}" && -d "${CUDA_HOME}/nvvm/libdevice" ]]; then
  echo "Found libdevice directory:"
  ls -1 "${CUDA_HOME}/nvvm/libdevice" | head -n 5 || true
else
  echo "WARNING: libdevice directory not found at ${CUDA_HOME:-<unset>}/nvvm/libdevice"
fi

echo '=========='
echo 'Activate conda env'
echo '=========='
# Robust conda activation across PBS environments
source ~/miniconda3/etc/profile.d/conda.sh
conda activate hieu_env_biorex

# Helpful runtime info (GPU status and library versions)
nvidia-smi || true
which python
python -c "import tensorflow as tf, transformers as tr; print('TF', tf.__version__, 'TR', tr.__version__)"

# I/O (unchanged except for a NEW mkdir -p to ensure output dirs exist)
in_pubtator_file="datasets/Unified_PPI/Unified_PPI_dataset.PubTator"
out_tsv_file="datasets/Unified_PPI/processed/test_for_Unified_PPI.tsv"
out_pubtator_file="predict.pubtator"
pre_train_model="microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract"

# ENSURE DIRECTORY EXISTS
mkdir -p datasets/Unified_PPI/processed/

# Note: The TSV conversion step is now handled by scripts/prepare_test_pred_cpu.sh.
# Make sure to run that script before running this one.

# ADD A CHECK: Stop here if the necessary input file wasn't created by the CPU job
if [ ! -s "${out_tsv_file}" ]; then
  echo "ERROR: ${out_tsv_file} was not found! Please run the preparation script first."
  exit 1
fi

# Respect a GPU index passed as arg (defaults to GPU 0)
GPU_INDEX="${1:-0}"
export CUDA_VISIBLE_DEVICES="$GPU_INDEX"

# Prevent TF from pre-allocating all GPU memory (cluster-friendly)
export TF_FORCE_GPU_ALLOW_GROWTH=true

echo '========================='
echo 'Generating RE predictions'
echo '========================='
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
# Guard the copy so failures are explicit instead of silent
if [[ -f "biorex_model/test_results.tsv" ]]; then
  cp "biorex_model/test_results.tsv" "out_biorex_results.tsv"
else
  echo "Expected predictions not found: biorex_model/test_results.tsv"
  exit 2
fi

echo '==========================================='
echo 'Convert predictions back to PubTator format'
echo '==========================================='
python src/utils/run_pubtator_eval.py --exp_option 'to_pubtator' \
  --in_test_pubtator_file "${in_pubtator_file}" \
  --in_test_tsv_file "${out_tsv_file}" \
  --in_pred_tsv_file "out_biorex_results.tsv" \
  --out_pred_pubtator_file "${out_pubtator_file}"

echo 'Done.'

