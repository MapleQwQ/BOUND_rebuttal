#!/usr/bin/env bash
set -euo pipefail
ROOT=/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
cd "$ROOT"
RESULTS=BOUND_rebuttal/experiment/E2new_verifier/results
SOURCE=knowledgeEdit/results/robust_nonedit_highrisk_20260605
MANIFEST=BOUND_rebuttal/experiment/E2_verifier_packmonitor/results/manifest.json
REGISTRY=$RESULTS/pypi_index_packmonitor_registry.json
RUNNER=BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py
for attempt in $(seq 1 960); do
  file="$RESULTS/packmonitor_native_bound_llama3.1-release.jsonl"
  if [[ -f "$file" ]] && [[ $(wc -l < "$file") -eq 500 ]]; then break; fi
  if [[ "$attempt" -eq 960 ]]; then echo "BOUND native Llama anchor did not complete in 8h" >&2; exit 1; fi
  sleep 30
done
sleep 60
export CUDA_VISIBLE_DEVICES=0
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="/tmp/packmonitor_deps:/tmp/PackMonitor/HFuzzer/Framework:$ROOT"
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python
echo "START $(date -u +%FT%TZ) native BOUND-A Qwen3 nonthinking GPU0"
"$PY" "$RUNNER" \
  --model-path /data0/shuhanliu/models/qwen3-8B --registry "$REGISTRY" \
  --eval-json "$SOURCE/qwen3-release/fold_A/blast_50/eval_unseen_prompts.json" \
  --manifest-json "$MANIFEST" --manifest-model qwen3-release \
  --delta-dir "$SOURCE/qwen3-release/fold_A/blast_50" \
  --condition-prefix bound --only-unconstrained --disable-thinking \
  --max-tokens 128 --generations 5 --temperature 0.7 \
  --output-jsonl "$RESULTS/packmonitor_native_bound_qwen3-release_nothink.jsonl" \
  --output-summary "$RESULTS/packmonitor_native_bound_qwen3-release_nothink_runtime_summary.json" \
  > "$RESULTS/packmonitor_native_bound_qwen3-release_nothink.log" 2>&1
echo "DONE $(date -u +%FT%TZ) native BOUND-A Qwen3 nonthinking GPU0"
