#!/usr/bin/env bash
set -euo pipefail

repo="/data0/shuhanliu/code/PackageHallucinationEdit/reference/PackageHallucination/KnowledgeEdit2"
root="$repo/BOUND_rebuttal/experiment/E3new_unfiltered_prompts"
python_bin="/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
log="$root/process_log.md"
sub="$root/results/sample500"
cd "$repo"
declare -A restarts=([1]=0 [2]=0 [3]=0)

while true; do
  complete=0
  total=0
  for model in deepseekcoder qwen3 llama31; do
    for fold in A B C D; do
      name="${model}_fold${fold}"
      detail="$sub/raw/$name.details.jsonl"
      output="$sub/raw/$name.json"
      count=0
      if [[ -f "$detail" ]]; then count="$(wc -l < "$detail")"; fi
      total=$((total + count))
      if [[ "$count" -eq 500 && -f "$output" ]]; then complete=$((complete + 1)); fi
    done
  done
  printf '\n- %s UTC: supplementary generation progress %s/6000 prompt-condition records, %s/12 conditions complete.\n' "$(date -u +%FT%TZ)" "$total" "$complete" >> "$log"
  if [[ "$complete" -eq 12 ]]; then break; fi
  for gpu in 1 2 3; do
    case "$gpu" in 1) model=deepseekcoder;; 2) model=qwen3;; 3) model=llama31;; esac
    model_complete=0
    for fold in A B C D; do
      name="${model}_fold${fold}"
      detail="$sub/raw/$name.details.jsonl"
      output="$sub/raw/$name.json"
      if [[ -f "$detail" && -f "$output" && $(wc -l < "$detail") -eq 500 ]]; then
        model_complete=$((model_complete + 1))
      fi
    done
    if [[ "$model_complete" -eq 4 ]]; then continue; fi
    if ! tmux has-session -t "e3new500_gpu$gpu" 2>/dev/null; then
      restarts[$gpu]=$((restarts[$gpu] + 1))
      if [[ "${restarts[$gpu]}" -gt 3 ]]; then
        printf '\n- %s UTC: ERROR GPU%s queue stopped after three restart attempts; see logs.\n' "$(date -u +%FT%TZ)" "$gpu" >> "$log"
        exit 1
      fi
      printf '\n- %s UTC: GPU%s queue stopped; restarting resumable queue (attempt %s/3).\n' "$(date -u +%FT%TZ)" "$gpu" "${restarts[$gpu]}" >> "$log"
      tmux new-session -d -s "e3new500_gpu$gpu" "bash $root/run_queue_500.sh $gpu"
    fi
  done
  sleep 600
done

printf '\n- %s UTC: all 12 supplementary conditions complete; building PyPI first-release cache.\n' "$(date -u +%FT%TZ)" >> "$log"
for attempt in 1 2 3; do
  "$python_bin" "$root/build_release_cache.py" \
    --manifest "$sub/sample1500_manifest.jsonl" \
    --raw-dir "$root/results/raw" --extra-raw-dir "$sub/raw" \
    --seed-cache "$root/results/release_dates_final.jsonl" \
    --output "$sub/release_dates.jsonl" --workers 32 \
    > "$sub/release_cache_stdout.json" 2> "$sub/release_cache_stderr.log"
  if "$python_bin" - "$sub/release_cache_audit.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['statuses'].get('query_unknown',0)==0, x['statuses']
print(x)
PY
  then break; fi
  printf '\n- %s UTC: release-date cache has unresolved lookups; retry %s/3.\n' "$(date -u +%FT%TZ)" "$attempt" >> "$log"
  if [[ "$attempt" -eq 3 ]]; then exit 1; fi
  sleep 60
done
printf '\n- %s UTC: release-date cache complete with no query_unknown; merging 500 and 1500.\n' "$(date -u +%FT%TZ)" >> "$log"

"$python_bin" "$root/merge_and_summarize.py" \
  --repo "$repo" --manifest "$sub/sample500_manifest.jsonl" \
  --raw-dir "$sub/raw" --release-cache "$sub/release_dates_final.jsonl" \
  --output-dir "$sub/merged_500" --bootstrap 2000 \
  > "$sub/merge500_stdout.json"
"$python_bin" "$root/merge_and_summarize.py" \
  --repo "$repo" --manifest "$sub/sample1500_manifest.jsonl" \
  --raw-dir "$root/results/raw" --extra-raw-dir "$sub/raw" \
  --release-cache "$sub/release_dates_final.jsonl" \
  --output-dir "$sub/merged_1500" --bootstrap 2000 \
  > "$sub/merge1500_stdout.json"
printf '\n- %s UTC: supplementary 500 and combined 1500 merges complete.\n' "$(date -u +%FT%TZ)" >> "$log"
"$python_bin" "$root/write_supplementary_results.py"
