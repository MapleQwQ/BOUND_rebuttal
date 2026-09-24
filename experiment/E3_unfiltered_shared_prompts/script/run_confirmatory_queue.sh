#!/usr/bin/env bash
set -euo pipefail

gpu="${1:?usage: run_confirmatory_queue.sh GPU PARTITION}"
partition="${2:?usage: run_confirmatory_queue.sh GPU PARTITION}"
repo="/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2"
python_bin="/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
manifest="BOUND_rebuttal/experiment/E3_unfiltered_shared_prompts/results/shared_prompt_manifest_confirmatory200.jsonl"
result_dir="BOUND_rebuttal/experiment/E3_unfiltered_shared_prompts/results"
seed="20260926"

run_condition() {
  local model_key="$1"
  local model_path="$2"
  local baseline_file="$3"
  local condition="$4"
  local delta_dir="${5:-}"
  local adapter_type="blast"
  if [[ "$condition" == "base" ]]; then
    adapter_type="base"
  fi
  local output="$result_dir/confirm200_${model_key}_${condition}_seed${seed}.json"
  local log="$result_dir/confirm200_${model_key}_${condition}_seed${seed}.log"
  local cmd=(
    "$python_bin" scripts/eval_recommendation_nonedit_highrisk.py
    --model-path "$model_path"
    --adapter-type "$adapter_type"
    --prompts-file "$manifest"
    --baseline-response-file "$baseline_file"
    --output-file "$output"
    --gpu "$gpu"
    --num-generations 5
    --seed "$seed"
  )
  if [[ -n "$delta_dir" ]]; then
    cmd+=(--delta-dir "$delta_dir")
  fi
  echo "START $(date -u +%FT%TZ) $model_key $condition" >> "$result_dir/confirmatory_queue_gpu${gpu}.log"
  CUDA_VISIBLE_DEVICES="$gpu" PYTHONDONTWRITEBYTECODE=1 "${cmd[@]}" > "$log" 2>&1
  echo "DONE  $(date -u +%FT%TZ) $model_key $condition" >> "$result_dir/confirmatory_queue_gpu${gpu}.log"
}

cd "$repo"

if [[ "$partition" == "gpu2" ]]; then
  for condition in base foldA foldB foldC foldD; do
    delta=""
    [[ "$condition" != "base" ]] && delta="knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder/fold_${condition#fold}/blast_50"
    run_condition deepseekcoder /data0/shuhanliu/models/deepseekcoder getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl "$condition" "$delta"
  done
  for condition in base foldA; do
    delta=""
    [[ "$condition" != "base" ]] && delta="knowledgeEdit/results/robust_nonedit_highrisk_20260605/qwen3-release/fold_${condition#fold}/blast_50"
    run_condition qwen3 /data0/shuhanliu/models/qwen3-8B getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl "$condition" "$delta"
  done
elif [[ "$partition" == "gpu3" ]]; then
  for condition in foldB foldC foldD; do
    delta="knowledgeEdit/results/robust_nonedit_highrisk_20260605/qwen3-release/fold_${condition#fold}/blast_50"
    run_condition qwen3 /data0/shuhanliu/models/qwen3-8B getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl "$condition" "$delta"
  done
  for condition in base foldA foldB foldC foldD; do
    delta=""
    [[ "$condition" != "base" ]] && delta="knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_${condition#fold}/blast_50"
    run_condition llama31 /data0/shuhanliu/models/llama3.1 getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl "$condition" "$delta"
  done
else
  echo "unknown partition: $partition" >&2
  exit 2
fi
