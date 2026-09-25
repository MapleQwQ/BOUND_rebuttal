#!/usr/bin/env bash
set -euo pipefail
ROOT=/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
cd "$ROOT"
RESULTS=BOUND_rebuttal/experiment/E2new_verifier/results
SOURCE=knowledgeEdit/results/robust_nonedit_highrisk_20260605
MANIFEST=BOUND_rebuttal/experiment/E2_verifier_packmonitor/results/manifest.json
REGISTRY=$RESULTS/pypi_index_packmonitor_registry.json
RUNNER=BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py
export CUDA_VISIBLE_DEVICES=0
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="/tmp/packmonitor_deps:/tmp/PackMonitor/HFuzzer/Framework:$ROOT"
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python

wait_for_gpu0() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 | tr -d ' ')
    if [[ "$used" =~ ^[0-9]+$ ]] && (( used <= 100 )); then
      echo "GPU0 idle check $(date -u +%FT%TZ): ${used}MiB; starting next stage"
      return
    fi
    echo "GPU0 occupied check $(date -u +%FT%TZ): ${used}MiB; waiting 30 minutes"
    sleep 1800
  done
}

wait_for_gpu0
echo "START $(date -u +%FT%TZ) Qwen3 Base/PackMonitor nonthinking GPU0"
"$PY" "$RUNNER" \
  --model-path /data0/shuhanliu/models/qwen3-8B --registry "$REGISTRY" \
  --eval-json "$SOURCE/qwen3-release/fold_A/blast_50/eval_unseen_prompts.json" \
  --manifest-json "$MANIFEST" --manifest-model qwen3-release \
  --max-tokens 128 --generations 5 --temperature 0.7 --disable-thinking \
  --output-jsonl "$RESULTS/packmonitor_native_qwen3-release_nothink_full.jsonl" \
  --output-summary "$RESULTS/packmonitor_native_qwen3-release_nothink_full_runtime_summary.json" \
  > "$RESULTS/packmonitor_native_qwen3-release_nothink_full.log" 2>&1
echo "DONE $(date -u +%FT%TZ) Qwen3 Base/PackMonitor nonthinking GPU0"

wait_for_gpu0
echo "START $(date -u +%FT%TZ) Qwen3 BOUND-A nonthinking GPU0"
"$PY" "$RUNNER" \
  --model-path /data0/shuhanliu/models/qwen3-8B --registry "$REGISTRY" \
  --eval-json "$SOURCE/qwen3-release/fold_A/blast_50/eval_unseen_prompts.json" \
  --manifest-json "$MANIFEST" --manifest-model qwen3-release \
  --delta-dir "$SOURCE/qwen3-release/fold_A/blast_50" \
  --condition-prefix bound --only-unconstrained --disable-thinking \
  --max-tokens 128 --generations 5 --temperature 0.7 \
  --output-jsonl "$RESULTS/packmonitor_native_bound_qwen3-release_nothink_full.jsonl" \
  --output-summary "$RESULTS/packmonitor_native_bound_qwen3-release_nothink_full_runtime_summary.json" \
  > "$RESULTS/packmonitor_native_bound_qwen3-release_nothink_full.log" 2>&1
echo "DONE $(date -u +%FT%TZ) Qwen3 BOUND-A nonthinking GPU0"
