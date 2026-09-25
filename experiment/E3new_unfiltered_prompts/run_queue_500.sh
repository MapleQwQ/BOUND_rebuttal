#!/usr/bin/env bash
set -euo pipefail

gpu="${1:?usage: run_queue_500.sh GPU (1, 2, or 3)}"
repo="/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2"
python_bin="/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
root="$repo/BOUND_rebuttal/experiment/E3new_unfiltered_prompts"
manifest="$root/results/sample500/sample500_manifest.jsonl"
raw="$root/results/sample500/raw"
process_log="$root/process_log.md"
mkdir -p "$raw" "$root/results/sample500/logs"
cd "$repo"

run_one() {
  local model="$1" fold="$2" model_path="$3" baseline="$4" adapter="$5" cutoff="$6"
  local name="${model}_fold${fold}"
  local output="$raw/$name.json"
  local detail="$raw/$name.details.jsonl"
  local log="$root/results/sample500/logs/$name.log"
  if [[ -f "$detail" && -f "$output" && $(wc -l < "$detail") -eq 500 ]]; then
    printf '\n- %s UTC: GPU%s skip completed supplementary %s.\n' "$(date -u +%FT%TZ)" "$gpu" "$name" >> "$process_log"
    return
  fi
  printf '\n- %s UTC: GPU%s START supplementary %s; 500 prompts × 5 generations, 128 tokens, cutoff=%s.\n' "$(date -u +%FT%TZ)" "$gpu" "$name" "$cutoff" >> "$process_log"
  CUDA_VISIBLE_DEVICES="$gpu" PYTHONDONTWRITEBYTECODE=1 "$python_bin" BOUND_rebuttal/experiment/E3new_unfiltered_prompts/run_generation.py \
    --model-path "$model_path" --adapter-type blast --delta-dir "$adapter" \
    --prompts-file "$manifest" --baseline-response-file "$baseline" \
    --output-file "$output" --gpu "$gpu" --num-generations 5 \
    --max-new-tokens 128 --temperature 0.7 --top-k 40 --top-p 0.95 --seed 20260926 \
    --model-cutoff "$cutoff" \
    --release-cache-jsonl BOUND_rebuttal/experiment/E2new_verifier/results/package_first_release_jsonapi.jsonl \
    --defer-release-lookups > "$log" 2>&1
  local count
  count="$(wc -l < "$detail")"
  if [[ "$count" -ne 500 ]]; then
    printf '\n- %s UTC: GPU%s ERROR supplementary %s ended with %s/500; see %s.\n' "$(date -u +%FT%TZ)" "$gpu" "$name" "$count" "$log" >> "$process_log"
    exit 1
  fi
  printf '\n- %s UTC: GPU%s DONE supplementary %s.\n' "$(date -u +%FT%TZ)" "$gpu" "$name" >> "$process_log"
}

case "$gpu" in
  1)
    for fold in A B C D; do
      run_one deepseekcoder "$fold" /data0/shuhanliu/models/deepseekcoder \
        getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl \
        "knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder/fold_$fold/blast_50" 2023-10-29
    done
    ;;
  2)
    for fold in A B C D; do
      run_one qwen3 "$fold" /data0/shuhanliu/models/qwen3-8B \
        getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl \
        "knowledgeEdit/results/robust_nonedit_highrisk_20260605/qwen3-release/fold_$fold/blast_50" 2025-04-29
    done
    ;;
  3)
    for fold in A B C D; do
      run_one llama31 "$fold" /data0/shuhanliu/models/llama3.1 \
        getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl \
        "knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_$fold/blast_50" 2023-12-31
    done
    ;;
  *) echo "GPU must be 1, 2, or 3" >&2; exit 2 ;;
esac
