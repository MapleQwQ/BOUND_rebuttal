#!/usr/bin/env bash
set -euo pipefail

root="/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2/BOUND_rebuttal/experiment/E3new_unfiltered_prompts"
log="$root/process_log.md"
raw="$root/results/raw"

while true; do
  sleep 600
  total=0
  report=""
  completed=0
  for model in deepseekcoder qwen3 llama31; do
    for fold in A B C D; do
      name="${model}_fold${fold}"
      path="$raw/$name.details.jsonl"
      count=0
      if [[ -f "$path" ]]; then
        count="$(wc -l < "$path")"
      fi
      total=$((total + count))
      if [[ "$count" -eq 1000 ]]; then
        completed=$((completed + 1))
      elif [[ "$count" -gt 0 ]]; then
        report="$report $name=$count/1000"
      fi
    done
  done
  printf '\n- %s UTC: progress %s/12000 prompt-condition records, %s/12 conditions complete;%s.\n' "$(date -u +%FT%TZ)" "$total" "$completed" "$report" >> "$log"
  if [[ "$completed" -eq 12 ]]; then
    exit 0
  fi
  if ! tmux has-session -t e3new_gpu2 2>/dev/null && ! tmux has-session -t e3new_gpu3 2>/dev/null; then
    printf '\n- %s UTC: both GPU queues ended before 12 conditions completed; inspect condition logs before resuming.\n' "$(date -u +%FT%TZ)" >> "$log"
    exit 1
  fi
done
