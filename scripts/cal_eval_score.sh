in_tsv_file="datasets/ncbi_relation/processed/test.tsv"

echo '===================='
echo 'Calculate Eval Score'
echo '===================='

python src/utils/run_pubtator_eval.py --exp_option 'biored_eval' \
  --in_gold_tsv_file "${in_tsv_file}" \
  --in_pred_tsv_file "out_biorex_results.tsv" \
  --out_bin_result_file "out_biorex_bin_results.txt" \
  --out_result_file "out_biorex_results.txt" \
  --out_pred_pubtator_file "out_biorex_bin_results.pubtator"
  
#echo '======================================='
#echo 'Calculate Binary Dataset Eval Score'
#echo '======================================='
#python src/utils/run_pubtator_eval.py --exp_option 'simple_tsv_eval' \
#  --in_gold_tsv_file "${in_tsv_file}" \
#  --in_pred_tsv_file "out_biorex_results.tsv" \
#  --out_bin_result_file "ncbi_relation_eval_binary_results.txt"