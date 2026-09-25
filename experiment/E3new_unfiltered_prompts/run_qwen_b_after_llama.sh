#!/usr/bin/env bash
set -euo pipefail

repo="/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2"
root="$repo/BOUND_rebuttal/experiment/E3new_unfiltered_prompts"
python_bin="/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
cd "$repo"
while [[ ! -f "$root/results/raw/llama31_foldD.json" ]]; do
  sleep 60
done
output="$root/results/raw/qwen3_foldB.json"
detail="$root/results/raw/qwen3_foldB.details.jsonl"
if [[ -f "$output" && -f "$detail" && "$(wc -l < "$detail")" -eq 1000 ]]; then
  printf '\n- %s UTC: GPU3 extra Qwen3 fold B skipped; already complete.\n' "$(date -u +%FT%TZ)" >> "$root/process_log.md"
  exit 0
fi
if [[ -f "$detail" ]]; then
  printf '\n- %s UTC: GPU3 extra Qwen3 fold B not started because another run already wrote its detail file.\n' "$(date -u +%FT%TZ)" >> "$root/process_log.md"
  exit 0
fi
printf '\n- %s UTC: GPU3 START extra qwen3_foldB after Llama-3.1 completed.\n' "$(date -u +%FT%TZ)" >> "$root/process_log.md"
CUDA_VISIBLE_DEVICES=3 PYTHONDONTWRITEBYTECODE=1 "$python_bin" BOUND_rebuttal/experiment/E3new_unfiltered_prompts/run_generation.py \
  --model-path /data0/shuhanliu/models/qwen3-8B --adapter-type blast \
  --delta-dir knowledgeEdit/results/robust_nonedit_highrisk_20260605/qwen3-release/fold_B/blast_50 \
  --prompts-file "$root/results/sample1000_manifest.jsonl" \
  --baseline-response-file getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl \
  --output-file "$output" --gpu 3 --num-generations 5 \
  --max-new-tokens 128 --temperature 0.7 --top-k 40 --top-p 0.95 --seed 20260926 \
  --release-cache-jsonl BOUND_rebuttal/experiment/E2new_verifier/results/package_first_release_jsonapi.jsonl \
  --defer-release-lookups > "$root/results/logs/qwen3_foldB_gpu3.log" 2>&1
if [[ "$(wc -l < "$detail")" -ne 1000 ]]; then
  printf '\n- %s UTC: GPU3 ERROR qwen3_foldB incomplete; inspect GPU3 log.\n' "$(date -u +%FT%TZ)" >> "$root/process_log.md"
  exit 1
fi
printf '\n- %s UTC: GPU3 DONE extra qwen3_foldB (1000 prompts, 5000 generations).\n' "$(date -u +%FT%TZ)" >> "$root/process_log.md"
