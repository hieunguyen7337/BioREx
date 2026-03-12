# BioREx

## Updates:
Updated BioREx to the Python 3.12 version

## Environment:

* GPU: NVIDIA Tesla V100 SXM2
* Python: Python 3.12
* OS: Linux or WSL2 

## Installation

```bash
conda create -n biorex python=3.12
conda activate biorex
pip install --upgrade pip setuptools wheel
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

## BioREx Pre-trained Models

You can download the BioREx pre-trained models:

* [BioREx BioLinkBERT model (Preferred)](https://ftp.ncbi.nlm.nih.gov/pub/lu/BioREx/pretrained_model_biolinkbert.zip)
* [BioREx PubMedBERT model (Original)](https://ftp.ncbi.nlm.nih.gov/pub/lu/BioREx/pretrained_model.zip) 

Download the model and extract it into the `biorex_model/` directory in the root of the project.

## Prediction Pipeline

To predict relations on new data, the data needs to follow the json -> pubtator -> tsv pipeline. Follow the steps below:

### Step 1: Data Preparation (JSON -> PubTator -> TSV)

Since the `datasets/` folder is not included in the repository, you will first need to create the directory structure and place your JSON files there.

```bash
mkdir -p datasets/Phos_dataset/
mkdir -p datasets/Unified_PPI/
```
Place `cleaned_phosphorylation_corpus.json` into `datasets/Phos_dataset/`.
Place `Unified_PPI_dataset_clean.json` into `datasets/Unified_PPI/`.

Next, convert your JSON/JSONL format to PubTator format using our custom dataset format converters located in `src/dataset_format_converter/custom_converters/`.

For the Phos dataset:
```bash
python src/dataset_format_converter/custom_converters/convert_phos_to_pubtator.py \
  --input_file "datasets/Phos_dataset/cleaned_phosphorylation_corpus.json" \
  --output_file "datasets/Phos_dataset/phosphorylation_corpus.PubTator"
```

For the Unified_PPI dataset:
```bash
python src/dataset_format_converter/custom_converters/convert_unified_to_pubtator.py \
  --input_file "datasets/Unified_PPI/Unified_PPI_dataset_clean.json" \
  --output_file "datasets/Unified_PPI/Unified_PPI_dataset.PubTator"
```
This will generate the required `.PubTator` files.

Next, convert the PubTator file into TSV format containing the extracted relations and candidates. 

For the Phos dataset:
```bash
# Ensure the model input directory exists
mkdir -p datasets/Phos_dataset/processed/

python src/dataset_format_converter/convert_pubtator_2_tsv.py \
  --exp_option biored_pred \
  --in_pubtator_file "datasets/Phos_dataset/phosphorylation_corpus.PubTator" \
  --out_tsv_file "datasets/Phos_dataset/processed/test_for_Phos.tsv"
```

For the Unified_PPI dataset:
```bash
# Ensure the model input directory exists
mkdir -p datasets/Unified_PPI/processed/

python src/dataset_format_converter/convert_pubtator_2_tsv.py \
  --exp_option biored_pred \
  --in_pubtator_file "datasets/Unified_PPI/Unified_PPI_dataset.PubTator" \
  --out_tsv_file "datasets/Unified_PPI/processed/test_for_Unified_PPI.tsv"
```

### Step 2: Run Predictions

To initiate the prediction process over the generated TSV files using the BioREx pre-trained model on GPU 0:

For the Phos dataset, edit scripts\run_test_pred.sh and replace the following lines with the value below:
```python
in_pubtator_file="datasets/Phos_dataset/phosphorylation_corpus.PubTator"
out_tsv_file="datasets/Phos_dataset/processed/test_for_Phos.tsv"
out_pubtator_file="predict.pubtator"
```
then run the following command:
```bash
bash scripts/run_test_pred.sh
```
*(If on HPC, use `qsub scripts/run_test_pred.sh` instead of `bash`)*

For the Unified_PPI dataset, edit scripts\run_test_pred.sh and replace the following lines with the value below:
```python
in_pubtator_file="datasets/Unified_PPI/Unified_PPI_dataset.PubTator"
out_tsv_file="datasets/Unified_PPI/processed/test_for_Unified_PPI.tsv"
out_pubtator_file="predict.pubtator"
```
then run the following command:
```bash
bash scripts/run_test_pred.sh
```
*(If on HPC, use `qsub scripts/run_test_pred.sh` instead of `bash`)*

### Step 3: Evaluation

A standalone metric evaluation script, `evaluate_metrics.py`, is available in the root directory. It automatically computes accurate binary or multi-class classification scores (Accuracy, Precision, Recall, Micro F1, Macro F1).

To evaluate your predictions against the gold-standard PubTator files:

For the Phos dataset:
```bash
python evaluate_metrics.py \
  --pred_file "datasets/Phos_dataset/predict.pubtator" \
  --gold_file "datasets/Phos_dataset/phosphorylation_corpus.PubTator"
```

For the Unified_PPI dataset:
```bash
python evaluate_metrics.py \
  --pred_file "datasets/Unified_PPI/predict.pubtator" \
  --gold_file "datasets/Unified_PPI/Unified_PPI_dataset.PubTator"
```

## Citing BioREx

* Lai P. T., Wei C. H., Luo L., Chen Q. and Lu Z. BioREx: Improving Biomedical Relation Extraction by Leveraging Heterogeneous Datasets. Journal of Biomedical Informatics. 2023.
```
@article{lai2023biorex,
  author  = {Lai, Po-Ting and Wei, Chih-Hsuan and Luo, Ling and Chen, Qingyu and Lu, Zhiyong},
  title   = {BioREx: Improving Biomedical Relation Extraction by Leveraging Heterogeneous Datasets},
  journal = {Journal of Biomedical Informatics},
  volume  = {146},
  pages   = {104487},
  year    = {2023},
  issn    = {1532-0464},
  doi     = {https://doi.org/10.1016/j.jbi.2023.104487},
  url     = {https://www.sciencedirect.com/science/article/pii/S1532046423002083},
}
```

## Acknowledgments

This research was supported by the NIH Intramural Research Program, National Library of Medicine. It was also supported by the National Library of Medicine of the National Institutes of Health under award number 1K99LM014024 (Q. Chen) and the Fundamental Research Funds for the Central Universities [DUT23RC(3)014 to L.L.].

## Disclaimer
This tool shows the results of research conducted in the Computational Biology Branch, NCBI. The information produced on this website is not intended for direct diagnostic use or medical decision-making without review and oversight by a clinical professional. Individuals should not change their health behavior solely on the basis of information produced on this website. NIH does not independently verify the validity or utility of the information produced by this tool. If you have questions about the information produced on this website, please see a health care professional. More information about NCBI's disclaimer policy is available.
