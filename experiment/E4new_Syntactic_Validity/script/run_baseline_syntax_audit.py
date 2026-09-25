"""Extend the frozen E4new syntax audit to ROME, MEMIT, DINM and Full-FT."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter

from run_syntax_audit import (
    BOOTSTRAP_REPS, BOOTSTRAP_SEED, CODE_BLOCK_RE, FOLDS, HIST, MODELS,
    N_PROMPTS, N_REPEATS, OUT, ROOT, archived_code_block, examine,
    extracted_code, percentile, read_jsonl, sha256, summarize,
)

METHODS = ("ROME", "MEMIT", "DINM", "Full-FT")
METRICS = ("syntax_valid_rate", "no_code_rate", "parse_failure_rate", "compile_failure_rate",
           "compile_valid_rate", "syntax_valid_third_party_import_rate")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "import_modules": json.dumps(row["import_modules"], ensure_ascii=False)})


def main() -> None:
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"Expected Python 3.10, got {sys.version}")
    previous = OUT / "per_generation.csv"
    if not previous.exists():
        raise SystemExit("Run run_syntax_audit.py first")
    prior = list(csv.DictReader(previous.open(encoding="utf-8")))
    if len(prior) != 7_500:
        raise ValueError(f"Unexpected prior audit rows: {len(prior)}")
    snapshot_prefix = "BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization/"
    prior_bound = [row for row in prior if row["method"] == "BOUND"]
    if len(prior_bound) != 6_000 or any(not row["source_path"].startswith(snapshot_prefix) for row in prior_bound):
        raise ValueError("BOUND rows must come from BOUND_rebuttal/replication package/BOUND")
    prior_manifest = json.loads((OUT / "input_manifest.json").read_text(encoding="utf-8"))
    manifest_bound = [item for item in prior_manifest["inputs"] if item["method"] == "BOUND"]
    if len(manifest_bound) != 12 or any(not item["path"].startswith(snapshot_prefix) for item in manifest_bound):
        raise ValueError("BOUND manifest must contain the 12 replication-package inputs")
    records = []
    inventory = []
    for model, historical_model in MODELS:
        base = {row["generation_id"]: row for row in prior if row["model"] == model and row["method"] == "Base"}
        if len(base) != N_PROMPTS * N_REPEATS:
            raise ValueError(f"Base audit missing for {model}")
        for method in METHODS:
            for fold in FOLDS:
                path = HIST / historical_model / method / f"fold_{fold}" / "test100_case_repeat5/rq2_details.jsonl"
                rows = read_jsonl(path)
                ids = {str(row["id"]) for row in rows}
                if len(rows) != 500 or len(ids) != 500 or ids != set(base):
                    raise ValueError(f"Count/ID mismatch: {path}")
                if any(hashlib.sha256(row["question"].encode()).hexdigest() != base[str(row["id"])]["question_sha256"] for row in rows):
                    raise ValueError(f"Question mismatch: {path}")
                for row in rows:
                    data = row["tasks"]["code"]
                    raw = data["code_generation_raw"]
                    code, route = extracted_code(raw)
                    if archived_code_block(raw) != data["code_block"]:
                        raise ValueError(f"Cannot reproduce archived code block: {path} id={row['id']}")
                    result = examine(code, route)
                    archived_route = "python_fence" if CODE_BLOCK_RE.search(raw) else "answer_fallback"
                    archived_result = examine(data["code_block"], archived_route)
                    records.append({
                        "model": model, "method": method, "fold": fold,
                        "generation_id": str(row["id"]), "prompt_id": str(row["original_id"]),
                        "question_sha256": hashlib.sha256(row["question"].encode()).hexdigest(),
                        "source_path": str(path.relative_to(ROOT)),
                        "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                        "code_chars": len(code), "extraction_route": route,
                        "differs_from_archived_code_block": code != data["code_block"],
                        "archived_parse_ok": archived_result["parse_ok"],
                        "archived_status": archived_result["status"], **result,
                    })
                inventory.append({"model": model, "method": method, "fold": fold,
                                  "path": str(path.relative_to(ROOT)), "sha256": sha256(path), "n": len(rows)})
    if len(records) != 24_000:
        raise ValueError(f"Expected 24,000 baseline rows, got {len(records)}")
    write_csv(OUT / "baseline_per_generation.csv", records)
    (OUT / "baseline_input_manifest.json").write_text(json.dumps({
        "python": sys.version, "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": BOOTSTRAP_REPS, "inputs": inventory,
        "base_bound_manifest": "input_manifest.json",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    by_condition = {}
    by_model = {}
    prompt_rates = {}
    for model, _ in MODELS:
        by_condition[model] = {}
        by_model[model] = {}
        prior_base = [row for row in prior if row["model"] == model and row["method"] == "Base"]
        base_groups = {}
        for row in prior_base:
            base_groups.setdefault(row["prompt_id"], []).append(row)
        if len(base_groups) != N_PROMPTS or any(len(v) != N_REPEATS for v in base_groups.values()):
            raise ValueError(f"Base prompt grouping mismatch: {model}")
        prompt_rates[(model, "Base", "")] = {pid: {metric: summarize([{
            **r, "parse_ok": r["parse_ok"] == "True", "compile_ok": r["compile_ok"] == "True",
            "third_party_import": r["third_party_import"] == "True",
        } for r in group])[metric] for metric in METRICS} for pid, group in base_groups.items()}
        for method in METHODS:
            fold_summaries = {}
            for fold in FOLDS:
                selected = [row for row in records if row["model"] == model and row["method"] == method and row["fold"] == fold]
                if len(selected) != 500:
                    raise ValueError((model, method, fold, len(selected)))
                fold_summaries[fold] = summarize(selected)
                groups = {}
                for row in selected:
                    groups.setdefault(row["prompt_id"], []).append(row)
                if set(groups) != set(base_groups) or any(len(v) != N_REPEATS for v in groups.values()):
                    raise ValueError(f"Baseline prompt grouping mismatch: {model}/{method}/{fold}")
                prompt_rates[(model, method, fold)] = {pid: {metric: summarize(group)[metric] for metric in METRICS}
                                                        for pid, group in groups.items()}
            by_condition[model][method] = fold_summaries
            by_model[model][method] = {metric: sum(fold_summaries[f][metric] for f in FOLDS) / 4 for metric in METRICS}
    three_model_macro = {method: {metric: sum(by_model[model][method][metric] for model, _ in MODELS) / 3
                                  for metric in METRICS} for method in METHODS}

    rng = random.Random(BOOTSTRAP_SEED)
    draws = {model: {method: {metric: [] for metric in METRICS} for method in METHODS} for model, _ in MODELS}
    draws["three_model_macro"] = {method: {metric: [] for metric in METRICS} for method in METHODS}
    prompts = {model: sorted(prompt_rates[(model, "Base", "")]) for model, _ in MODELS}
    for _ in range(BOOTSTRAP_REPS):
        pooled = {method: {metric: 0.0 for metric in METRICS} for method in METHODS}
        for model, _ in MODELS:
            sampled = rng.choices(prompts[model], k=N_PROMPTS)
            multiplicity = Counter(sampled)
            for metric in METRICS:
                base_value = sum(prompt_rates[(model, "Base", "")][pid][metric] * count for pid, count in multiplicity.items()) / N_PROMPTS
                for method in METHODS:
                    value = sum(sum(prompt_rates[(model, method, fold)][pid][metric] * count for pid, count in multiplicity.items()) / N_PROMPTS for fold in FOLDS) / 4
                    diff = value - base_value
                    draws[model][method][metric].append(diff)
                    pooled[method][metric] += diff / 3
        for method in METHODS:
            for metric in METRICS:
                draws["three_model_macro"][method][metric].append(pooled[method][metric])
    intervals = {model: {method: {metric: [percentile(values, .025), percentile(values, .975)]
                                   for metric, values in metrics_map.items()}
                          for method, metrics_map in methods_map.items()}
                 for model, methods_map in draws.items()}
    result = {"n_baseline_generations": len(records), "by_condition": by_condition,
              "by_model": by_model, "three_model_macro": three_model_macro,
              "baseline_minus_base_95pct_prompt_bootstrap_ci": intervals,
              "definitions": json.loads((OUT / "syntax_summary.json").read_text(encoding="utf-8"))["definitions"]}
    (OUT / "baseline_syntax_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for model in [m for m, _ in MODELS] + ["three_model_macro"]:
        print(model)
        for method in METHODS:
            value = by_model[model][method]["syntax_valid_rate"] if model != "three_model_macro" else three_model_macro[method]["syntax_valid_rate"]
            ci = intervals[model][method]["syntax_valid_rate"]
            print(method, f"{value:.4f}", "CI vs Base", [round(x, 4) for x in ci])


if __name__ == "__main__":
    main()
