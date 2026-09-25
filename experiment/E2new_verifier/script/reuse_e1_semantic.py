#!/usr/bin/env python3
"""Exploratory semantic comparison using exact E1 annotated answers.

BOV labels are derived from E1 candidate-level evidence and frozen slots,
not independently re-annotated. This is intentionally not the E2new 30-task
confirmatory quality sample.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from run_existing_generations import RESULTS, normalize

E1 = RESULTS.parents[1] / "E1_task_relevance" / "results"


def jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> None:
    keys = json.loads((E1 / "formal_unblinded_key.json").read_text(encoding="utf-8"))
    labels = {row["blind_answer_id"]: row for row in jsonl(E1 / "adjudicated_labels.jsonl")}
    slots = {row["task_id"]: row for row in jsonl(E1 / "frozen_requirement_slots.jsonl")}
    bmap = {}
    for row in jsonl(RESULTS / "online_verifier_answers.jsonl"):
        bmap[row["model"], str(row["prompt_id"]), row["generation"]] = row
    rows = []
    for item in keys:
        label = labels[item["blind_answer_id"]]
        original = {normalize(c["candidate_name"]) for c in label["candidates"]}
        if item["condition"] == "base":
            bov = bmap.get((item["model"], item["prompt_id"], item["generation"]))
            if bov is None:
                continue
            if original != {normalize(name) for name in bov["source_packages"]}:
                raise ValueError(f"E1 candidate mismatch: {item['blind_answer_id']}")
            retained = {normalize(name) for name in bov["retained_packages"]}
            necessary = {slot["slot_id"] for slot in slots[item["task_id"]]["slots"]}
            covered = {slot for candidate in label["candidates"]
                       if normalize(candidate["candidate_name"]) in retained
                       and candidate["registry_status"] == "exists_at_audit_date"
                       and candidate["task_role"] == "core_function_support"
                       for slot in candidate["covered_slots"]}
            no_third = slots[item["task_id"]]["no_third_party_dependency_needed"]
            # Filtering cannot invent a missing capability; only preserve or lose it.
            base_adequate = label["adequacy"] == "adequate"
            derived = base_adequate and necessary.issubset(covered) and bool(retained)
            if no_third:
                # The output is a bare filtered list; do not credit an empty list as
                # an explicit explanation that no dependency is needed.
                derived = False
            rows.append({"model": item["model"], "prompt_id": item["prompt_id"],
                         "method": "bov_derived", "adequate": int(derived),
                         "unknown": int(label["cannot_judge"]),
                         "needed_slots": len(necessary), "covered_slots": len(covered & necessary),
                         "candidate_count": len(retained),
                         "label_basis": "derived_from_E1_adjudicated_candidate_slots"})
        rows.append({"model": item["model"], "prompt_id": item["prompt_id"],
                     "method": "base" if item["condition"] == "base" else f"bound_{item['fold']}",
                     "adequate": int(label["adequacy"] == "adequate"),
                     "unknown": int(label["cannot_judge"]),
                     "needed_slots": len(slots[item["task_id"]]["slots"]),
                     "covered_slots": len(label["covered_slots"]),
                     "candidate_count": len(label["candidates"]),
                     "label_basis": "E1_independent_adjudicated"})
    if len(rows) != 360:
        raise SystemExit(f"E1/BOV semantic set incomplete: {len(rows)}/360 records")
    with (RESULTS / "e1_reuse_semantic_rows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = defaultdict(dict)
    for model in sorted({r["model"] for r in rows}):
        for method in ("base", "bound_A", "bound_B", "bound_C", "bound_D", "bov_derived"):
            subset = [r for r in rows if r["model"] == model and r["method"] == method]
            if len(subset) != 20:
                raise ValueError(f"E1 size mismatch {model} {method} {len(subset)}")
            summary[model][method] = {"n": len(subset), "adequacy_rate": sum(r["adequate"] for r in subset) / len(subset),
                                      "unknown_count": sum(r["unknown"] for r in subset)}
        summary[model]["bound_macro"] = {"adequacy_rate": sum(summary[model][f"bound_{f}"]["adequacy_rate"]
                                                             for f in "ABCD") / 4}
    report = {"scope": "exploratory exact E1 20-prompt/model reuse; generation 0",
              "caveat": "BOV adequacy is deterministic slot-preservation derivation, not new independent annotation",
              "models": summary}
    (RESULTS / "e1_reuse_semantic_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
