#!/usr/bin/env bash
set -euo pipefail

ROOT=/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
RESULTS="$ROOT/BOUND_rebuttal/experiment/E2_verifier_packmonitor/results"
COMMON=(
  --model-path /data0/shuhanliu/models/deepseekcoder
  --registry /tmp/PackMonitor/HFuzzer/valid_packages/pypi_packages.json
  --eval-json knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder/fold_A/blast_50/eval_unseen_prompts.json
  --manifest-json "$RESULTS/manifest.json"
  --manifest-model deepseekcoder
  --max-tokens 64
)

cd "$ROOT"
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH="/tmp/packmonitor_deps:/tmp/PackMonitor/HFuzzer/Framework:$ROOT"
export PYTHONDONTWRITEBYTECODE=1

echo "START $(date -u +%FT%TZ) Base vs PackMonitor, n=100"
/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python \
  BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py \
  "${COMMON[@]}" \
  --output-jsonl "$RESULTS/packmonitor_runtime100_generations.jsonl" \
  --output-summary "$RESULTS/packmonitor_runtime100_summary.json"
echo "DONE  $(date -u +%FT%TZ) Base vs PackMonitor, n=100"

echo "START $(date -u +%FT%TZ) BOUND-A vs BOUND-A+PackMonitor, n=100"
/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python \
  BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py \
  "${COMMON[@]}" \
  --delta-dir knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder/fold_A/blast_50 \
  --condition-prefix bound \
  --output-jsonl "$RESULTS/packmonitor_bound_runtime100_generations.jsonl" \
  --output-summary "$RESULTS/packmonitor_bound_runtime100_summary.json"
echo "DONE  $(date -u +%FT%TZ) BOUND-A vs BOUND-A+PackMonitor, n=100"
