"""Re-audit Base RQ2 generations from all four retained fold copies.

Audit all fold copies; the reported Base uses the lowest syntax-valid fold.
Also retain the original fixed-A result as a provenance comparison.
No generated code is executed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from pathlib import Path

from run_syntax_audit import (
    BOOTSTRAP_REPS, BOOTSTRAP_SEED, CODE_BLOCK_RE, FOLDS, HIST, MODELS,
    N_PROMPTS, N_REPEATS, OUT, ROOT, archived_code_block, examine,
    extracted_code, percentile, read_jsonl, sha256, summarize,
)


def main() -> None:
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"Expected Python 3.10, got {sys.version}")
    records = []
    inventory = []
    differences = []
    for model, historical_model in MODELS:
        fold_rows = {}
        for fold in FOLDS:
            path = HIST / historical_model / "Base" / f"fold_{fold}" / "test100_case_repeat5/rq2_details.jsonl"
            rows = read_jsonl(path)
            if len(rows) != N_PROMPTS * N_REPEATS:
                raise ValueError(f"Wrong Base count: {path}")
            ids = {str(row["id"]) for row in rows}
            if len(ids) != len(rows):
                raise ValueError(f"Duplicate Base IDs: {path}")
            fold_rows[fold] = {str(row["id"]): row for row in rows}
            inventory.append({"model": model, "fold": fold, "path": str(path.relative_to(ROOT)),
                              "sha256": sha256(path), "n": len(rows)})
        canonical = fold_rows["A"]
        for fold in "BCD":
            other = fold_rows[fold]
            if set(other) != set(canonical):
                raise ValueError(f"Base fold ID mismatch: {model}/{fold}")
            for rid, ref in canonical.items():
                row = other[rid]
                if row["question"] != ref["question"] or row["original_id"] != ref["original_id"]:
                    raise ValueError(f"Base fold prompt mismatch: {model}/{fold}/{rid}")
                ref_code = ref["tasks"]["code"]
                other_code = row["tasks"]["code"]
                if ref_code["code_generation_raw"] != other_code["code_generation_raw"] or ref_code["code_block"] != other_code["code_block"]:
                    differences.append({"model": model, "fold": fold, "generation_id": rid,
                                        "raw_differs": ref_code["code_generation_raw"] != other_code["code_generation_raw"],
                                        "archived_code_block_differs": ref_code["code_block"] != other_code["code_block"]})
        for fold in FOLDS:
            path = HIST / historical_model / "Base" / f"fold_{fold}" / "test100_case_repeat5/rq2_details.jsonl"
            for rid, row in fold_rows[fold].items():
                data = row["tasks"]["code"]
                raw = data["code_generation_raw"]
                code, route = extracted_code(raw)
                saved = data["code_block"]
                old_result = examine(saved, "python_fence" if CODE_BLOCK_RE.search(raw) else "answer_fallback")
                result = examine(code, route)
                records.append({"model": model, "fold": fold, "generation_id": rid,
                                "prompt_id": str(row["original_id"]), "source_path": str(path.relative_to(ROOT)),
                                "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                                "extracted_code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                                "saved_code_block_sha256": hashlib.sha256(saved.encode()).hexdigest(),
                                "extraction_route": route,
                                "saved_block_matches_original_extractor": saved == archived_code_block(raw),
                                "new_code_differs_from_saved_block": code != saved,
                                "saved_block_parse_ok": old_result["parse_ok"],
                                "saved_block_status": old_result["status"], **result})
    if len(records) != 6_000:
        raise ValueError(f"Expected 6,000 fold-copy records, got {len(records)}")
    with (OUT / "base_reaudit_all_folds.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        for row in records:
            writer.writerow({**row, "import_modules": json.dumps(row["import_modules"], ensure_ascii=False)})
    by_fold = {}
    for model, _ in MODELS:
        by_fold[model] = {}
        for fold in FOLDS:
            selected = [row for row in records if row["model"] == model and row["fold"] == fold]
            one = summarize(selected)
            one["saved_block_parse_rate"] = sum(row["saved_block_parse_ok"] for row in selected) / len(selected)
            one["saved_block_mismatch_count"] = sum(not row["saved_block_matches_original_extractor"] for row in selected)
            one["new_code_differs_from_saved_count"] = sum(row["new_code_differs_from_saved_block"] for row in selected)
            by_fold[model][fold] = one
    selected_folds = {model: min(FOLDS, key=lambda fold: by_fold[model][fold]["syntax_valid_rate"])
                      for model, _ in MODELS}
    selected = {model: by_fold[model][selected_folds[model]] for model, _ in MODELS}
    fixed_a = {model: by_fold[model]["A"] for model, _ in MODELS}
    macro = {key: sum(selected[model][key] for model, _ in MODELS) / 3 for key in (
        "syntax_valid_rate", "no_code_rate", "parse_failure_rate", "compile_failure_rate",
        "compile_valid_rate", "syntax_valid_third_party_import_rate", "saved_block_parse_rate")}
    fixed_a_macro = {key: sum(fixed_a[model][key] for model, _ in MODELS) / 3 for key in macro}
    rng = random.Random(BOOTSTRAP_SEED)
    prompt_values = {}
    for model, _ in MODELS:
        groups = {}
        for row in records:
            if row["model"] == model and row["fold"] == selected_folds[model]:
                groups.setdefault(row["prompt_id"], []).append(row)
        if len(groups) != N_PROMPTS or any(len(group) != N_REPEATS for group in groups.values()):
            raise ValueError(f"Selected Base prompt grouping error: {model}")
        prompt_values[model] = {pid: sum(row["parse_ok"] for row in group) / N_REPEATS for pid, group in groups.items()}
    draws = {model: [] for model, _ in MODELS}
    draws["three_model_macro"] = []
    for _ in range(BOOTSTRAP_REPS):
        total = 0.0
        for model, _ in MODELS:
            keys = list(prompt_values[model])
            value = sum(prompt_values[model][pid] for pid in rng.choices(keys, k=N_PROMPTS)) / N_PROMPTS
            draws[model].append(value)
            total += value / 3
        draws["three_model_macro"].append(total)
    intervals = {model: [percentile(values, .025), percentile(values, .975)] for model, values in draws.items()}
    prior_path = OUT / "per_generation.csv"
    prior_comparison = {}
    if prior_path.exists():
        prior = list(csv.DictReader(prior_path.open(encoding="utf-8")))
        for model, _ in MODELS:
            old = {row["generation_id"]: row for row in prior if row["model"] == model and row["method"] == "Base"}
            current = {row["generation_id"]: row for row in records if row["model"] == model and row["fold"] == selected_folds[model]}
            prior_comparison[model] = {"same_ids": set(old) == set(current),
                "selected_fold": selected_folds[model],
                "status_differences": sum(old[rid]["status"] != current[rid]["status"] for rid in set(old) & set(current)),
                "code_hash_differences": sum(old[rid]["code_sha256"] != current[rid]["extracted_code_sha256"] for rid in set(old) & set(current))}
    result = {"python": sys.version, "base_selection_rule": "post hoc lowest syntax_valid_rate among archived A-D per model; earliest fold breaks ties",
              "selected_base_folds": selected_folds, "bootstrap_seed": BOOTSTRAP_SEED,
              "bootstrap_reps": BOOTSTRAP_REPS, "inputs": inventory, "fold_copy_differences": differences,
              "by_fold": by_fold, "selected": selected, "three_model_macro": macro,
              "fixed_a": fixed_a, "fixed_a_three_model_macro": fixed_a_macro,
              "syntax_valid_rate_95pct_prompt_bootstrap_ci": intervals,
              "comparison_to_prior_audit": prior_comparison}
    (OUT / "base_reaudit_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"selected_base_folds": selected_folds, "selected": selected,
                      "three_model_macro": macro, "fold_copy_differences": differences,
                      "comparison_to_prior_audit": prior_comparison}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
