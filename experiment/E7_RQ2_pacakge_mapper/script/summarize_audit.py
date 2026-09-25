"""Summarize strict-AST mapper quality and fold-aggregated RQ2 sensitivity."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "results"


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def main():
    rows = list(csv.DictReader((OUT / "per_generation_audit.csv").open()))
    original = list(csv.DictReader((OUT / "generations.csv").open()))
    keys = {(r["model"], r["method"], r["fold"], r["generation_id"]): r for r in original}
    strict = [r for r in rows if r["extraction"] == "full_ast"]
    strict_known = [r for r in strict if r["mapping_known"] == "1"]
    strict_nonempty_known = [r for r in strict_known if json.loads(r["import_paths"])]
    strict_label_known = [r for r in strict if r["label_known"] == "1"]
    strict_nonempty_label_known = [r for r in strict_label_known if json.loads(r["import_paths"])]
    per_top = defaultdict(list)
    for row in strict_nonempty_known:
        original_row = keys[(row["model"], row["method"], row["fold"], row["generation_id"])]
        old_input = json.loads(original_row["mapper_input"])
        paths = json.loads(row["import_paths"])
        if len(old_input) == 1 and {p.split(".", 1)[0] for p in paths} == {old_input[0]}:
            per_top[old_input[0]].append(int(row["mapping_correct"]))
    unique_macro = mean([mean(x) for x in per_top.values()])
    occurrence_weighted = sum(sum(x) for x in per_top.values()) / sum(len(x) for x in per_top.values())
    signature_groups = defaultdict(list)
    for row in strict_nonempty_known:
        signature_groups[tuple(json.loads(row["import_paths"]))].append(int(row["mapping_correct"]))
    mapping_quality = dict(
        n_all_generations=len(rows), n_full_ast=len(strict), n_full_ast_mapping_known=len(strict_known),
        n_full_ast_nonempty_mapping_known=len(strict_nonempty_known),
        n_unique_single_import_top_keys=len(per_top),
        n_single_import_answer_occurrences=sum(len(x) for x in per_top.values()),
        unique_mapping_accuracy_single_import_macro=unique_macro,
        occurrence_weighted_accuracy_single_import=occurrence_weighted,
        n_unique_full_import_signatures=len(signature_groups),
        unique_signature_mapping_accuracy=mean([mean(x) for x in signature_groups.values()]),
        answer_weighted_exact_mapping_accuracy=sum(int(r["mapping_correct"]) for r in strict_nonempty_known)/len(strict_nonempty_known),
        n_strict_label_known=len(strict_label_known),
        n_strict_nonempty_label_known=len(strict_nonempty_label_known),
        exact_package_label_set_agreement=sum(int(r["label_agree"]) for r in strict_label_known)/len(strict_label_known),
        exact_package_label_set_agreement_nonempty=sum(int(r["label_agree"]) for r in strict_nonempty_label_known)/len(strict_nonempty_label_known),
        answer_level_valid_hall_flag_agreement=sum(
            int(bool(json.loads(r["original_valid"])) == bool(json.loads(r["audited_valid"])) and
                bool(json.loads(r["original_hallucinated"])) == bool(json.loads(r["audited_hallucinated"])))
            for r in strict_label_known)/len(strict_label_known),
        answer_level_valid_hall_flag_agreement_nonempty=sum(
            int(bool(json.loads(r["original_valid"])) == bool(json.loads(r["audited_valid"])) and
                bool(json.loads(r["original_hallucinated"])) == bool(json.loads(r["audited_hallucinated"])))
            for r in strict_nonempty_label_known)/len(strict_nonempty_label_known),
    )
    fold_rows = list(csv.DictReader((OUT / "rq2_metric_bounds_by_fold.csv").open()))
    by_condition = defaultdict(list)
    for r in fold_rows:
        by_condition[(r["model"], r["method"])].append(r)
    condition_rows = []
    average_fields = ("archived_sample_hr", "archived_package_hr", "archived_valid_rate",
                      "audited_sample_hr_lower", "audited_sample_hr_upper", "audited_sample_hr_tokenizer_scenario_upper",
                      "audited_package_hr_one_slot_min", "audited_package_hr_one_slot_max",
                      "audited_valid_rate_lower", "audited_valid_rate_upper", "audited_valid_rate_tokenizer_scenario_upper")
    for (model, method), group in sorted(by_condition.items()):
        condition_rows.append(dict(model=model, method=method, folds=len(group), n_per_fold=500,
                                   ast_failure_per_fold=mean([int(r["ast_failure"]) for r in group]),
                                   unknown_answers_per_fold=mean([int(r["unknown_answers"]) for r in group]),
                                   **{field: mean([float(r[field]) for r in group]) for field in average_fields}))
    with (OUT / "rq2_metric_bounds_by_condition.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(condition_rows[0]))
        writer.writeheader(); writer.writerows(condition_rows)
    (OUT / "mapper_quality_summary.json").write_text(json.dumps(mapping_quality, indent=2) + "\n")
    print(json.dumps(mapping_quality, indent=2))


if __name__ == "__main__":
    main()
