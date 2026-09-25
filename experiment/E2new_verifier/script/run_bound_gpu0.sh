#!/usr/bin/env bash
set -euo pipefail
cd /data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
export CUDA_VISIBLE_DEVICES=0
export PYTHONDONTWRITEBYTECODE=1
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python
SCRIPT=BOUND_rebuttal/experiment/E2new_verifier/script/generate_bound_timed.py
for model in deepseekcoder qwen3-release; do
  for fold in A B C D; do
    echo "START $(date -u +%FT%TZ) $model fold $fold GPU0"
    "$PY" "$SCRIPT" --model "$model" --fold "$fold" --gpu 0
    echo "DONE $(date -u +%FT%TZ) $model fold $fold GPU0"
  done
done
