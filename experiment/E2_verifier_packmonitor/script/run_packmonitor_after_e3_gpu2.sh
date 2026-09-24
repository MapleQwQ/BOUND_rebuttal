#!/usr/bin/env bash
set -euo pipefail

ROOT=/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
RESULTS="$ROOT/BOUND_rebuttal/experiment/E2_verifier_packmonitor/results"
E3_QUEUE_PID="${E3_QUEUE_PID:-4032975}"
while kill -0 "$E3_QUEUE_PID" 2>/dev/null; do
  sleep 120
done

cd "$ROOT"
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH="/tmp/packmonitor_deps:/tmp/PackMonitor/HFuzzer/Framework:$ROOT"
exec /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python \
  BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py \
  --model-path /data0/shuhanliu/models/deepseekcoder \
  --registry /tmp/PackMonitor/HFuzzer/valid_packages/pypi_packages.json \
  --eval-json knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder/fold_A/blast_50/eval_unseen_prompts.json \
  --output-jsonl "$RESULTS/packmonitor_runtime_generations.jsonl" \
  --output-summary "$RESULTS/packmonitor_runtime_summary.json" \
  --max-tokens 64
