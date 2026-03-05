#!/bin/bash

# I/O
in_pubtator_file="datasets/Phos_dataset/phosphorylation_corpus.PubTator"
out_tsv_file="datasets/Phos_dataset/processed/test_for_Phos.tsv"

# ENSURE DIRECTORY EXISTS
mkdir -p datasets/Phos_dataset/processed/

echo '==============================================='
echo 'Converting the dataset into BioREx input format'
echo '==============================================='
python src/dataset_format_converter/convert_pubtator_2_tsv.py \
  --exp_option biored_pred \
  --in_pubtator_file "${in_pubtator_file}" \
  --out_tsv_file "${out_tsv_file}"

if [ ! -s "${out_tsv_file}" ]; then
  echo "ERROR: ${out_tsv_file} was not created or is empty!"
  exit 1
fi

echo 'Done preparing dataset.'
