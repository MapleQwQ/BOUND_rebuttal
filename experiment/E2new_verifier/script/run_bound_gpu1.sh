#!/usr/bin/env bash
set -euo pipefail
cd /data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2
export CUDA_VISIBLE_DEVICES=1
export PYTHONDONTWRITEBYTECODE=1
PY=/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python
SCRIPT=BOUND_rebuttal/experiment/E2new_verifier/script/generate_bound_timed.py
for fold in A B C D; do
  echo "START $(date -u +%FT%TZ) llama3.1-release fold $fold GPU1"
  "$PY" "$SCRIPT" --model llama3.1-release --fold "$fold" --gpu 1
  echo "DONE $(date -u +%FT%TZ) llama3.1-release fold $fold GPU1"
done
