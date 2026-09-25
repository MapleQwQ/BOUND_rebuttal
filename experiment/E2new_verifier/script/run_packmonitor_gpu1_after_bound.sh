#!/usr/bin/env bash
set -euo pipefail
ROOT=/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
cd "$ROOT"
RESULTS=BOUND_rebuttal/experiment/E2new_verifier/results
SOURCE=knowledgeEdit/results/robust_nonedit_highrisk_20260605
MANIFEST=BOUND_rebuttal/experiment/E2_verifier_packmonitor/results/manifest.json
REGISTRY=$RESULTS/pypi_index_packmonitor_registry.json
RUNNER=BOUND_rebuttal/experiment/E2_verifier_packmonitor/script/run_packmonitor_native_smoke.py
export CUDA_VISIBLE_DEVICES=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="/tmp/packmonitor_deps:/tmp/PackMonitor/HFuzzer/Framework:$ROOT"
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python

# GPU1 is reserved for the four Llama BOUND folds first. Wait without loading a model.
for attempt in $(seq 1 720); do
  ready=1
  for fold in A B C D; do
    file="$RESULTS/bound_timed_llama3.1-release_fold_${fold}.jsonl"
    if [[ ! -f "$file" ]] || [[ $(wc -l < "$file") -ne 4670 ]]; then ready=0; break; fi
  done
  if [[ "$ready" -eq 1 ]]; then break; fi
  if [[ "$attempt" -eq 720 ]]; then echo "BOUND GPU1 did not finish in 6h" >&2; exit 1; fi
  sleep 30
done
sleep 60

for model in deepseekcoder qwen3-release llama3.1-release; do
  case "$model" in
    deepseekcoder) model_path=/data0/shuhanliu/models/deepseekcoder ;;
    qwen3-release) model_path=/data0/shuhanliu/models/qwen3-8B ;;
    llama3.1-release) model_path=/data0/shuhanliu/models/llama3.1 ;;
  esac
  echo "START $(date -u +%FT%TZ) PackMonitor $model GPU1"
  if "$PY" "$RUNNER" \
    --model-path "$model_path" --registry "$REGISTRY" \
    --eval-json "$SOURCE/$model/fold_A/blast_50/eval_unseen_prompts.json" \
    --manifest-json "$MANIFEST" --manifest-model "$model" \
    --max-tokens 128 --generations 5 --temperature 0.7 \
    --output-jsonl "$RESULTS/packmonitor_native_${model}.jsonl" \
    --output-summary "$RESULTS/packmonitor_native_${model}_runtime_summary.json" \
    > "$RESULTS/packmonitor_native_${model}.log" 2>&1; then
    echo "DONE $(date -u +%FT%TZ) PackMonitor $model GPU1"
  else
    echo "FAILED $(date -u +%FT%TZ) PackMonitor $model GPU1; inspect log" >&2
  fi
done
