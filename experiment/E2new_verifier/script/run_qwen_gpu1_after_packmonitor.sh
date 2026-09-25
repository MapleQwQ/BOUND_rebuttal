#!/usr/bin/env bash
set -euo pipefail
cd /data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
RESULTS=BOUND_rebuttal/experiment/E2new_verifier/results
export CUDA_VISIBLE_DEVICES=1
export PYTHONDONTWRITEBYTECODE=1
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python
SCRIPT=BOUND_rebuttal/experiment/E2new_verifier/script/generate_bound_timed.py

# Only after the final PackMonitor model has saved its summary (and exited).
for attempt in $(seq 1 720); do
  if [[ -f "$RESULTS/packmonitor_native_llama3.1-release_runtime_summary.json" ]]; then break; fi
  if [[ "$attempt" -eq 720 ]]; then echo "PackMonitor did not complete in 6h" >&2; exit 1; fi
  sleep 30
done
sleep 60
for fold in C D; do
  echo "START $(date -u +%FT%TZ) qwen3-release fold $fold GPU1"
  "$PY" "$SCRIPT" --model qwen3-release --fold "$fold" --gpu 1
  echo "DONE $(date -u +%FT%TZ) qwen3-release fold $fold GPU1"
done
