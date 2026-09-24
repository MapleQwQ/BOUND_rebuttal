#!/usr/bin/env python3
"""将E1最终匿名双标、仲裁和揭盲元数据整理为单一回答级CSV。"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def index(rows: list[dict], key: str) -> dict[str, dict]:
    output = {str(row[key]): row for row in rows}
    if len(output) != len(rows):
        raise ValueError(f"duplicate {key} in input")
    return output


def compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.results_dir

    answers = index(read_jsonl(root / "blinded_answers_anonymous.jsonl"), "blind_answer_id")
    final = index(read_jsonl(root / "adjudicated_labels.jsonl"), "blind_answer_id")
    ann1 = index(read_jsonl(root / "annotator_1_raw_labels.jsonl"), "blind_answer_id")
    ann2 = index(read_jsonl(root / "annotator_2_raw_labels.jsonl"), "blind_answer_id")
    slots = index(read_jsonl(root / "frozen_requirement_slots_anonymous.jsonl"), "anonymous_task_id")
    answer_key = index(json.loads((root / "formal_unblinded_key.json").read_text(encoding="utf-8")), "blind_answer_id")
    task_key = index(json.loads((root / "formal_task_unblinded_key.json").read_text(encoding="utf-8")), "anonymous_task_id")

    expected = set(answers)
    for name, mapping in (("final", final), ("annotator_1", ann1), ("annotator_2", ann2), ("answer_key", answer_key)):
        if set(mapping) != expected:
            raise ValueError(f"{name} answer ids differ: missing={len(expected-set(mapping))}, extra={len(set(mapping)-expected)}")

    fields = [
        "blind_answer_id", "anonymous_task_id", "original_task_id", "model", "prompt_id",
        "condition", "fold", "generation", "question", "answer", "packages_json", "package_count",
        "is_empty_recommendation", "requirement_slots_json", "required_slot_ids_json",
        "no_third_party_dependency_needed", "non_dependency_constraints_json",
        "annotator_1_adequacy", "annotator_2_adequacy", "annotator_1_covered_slots_json",
        "annotator_2_covered_slots_json", "annotator_1_cannot_judge", "annotator_2_cannot_judge",
        "annotator_1_label_json", "annotator_2_label_json", "final_adequacy", "final_covered_slots_json",
        "final_slot_coverage", "final_cannot_judge", "final_cannot_judge_reason",
        "answer_adjudication_status", "candidate_count", "candidate_names_json",
        "candidate_registry_statuses_json", "candidate_task_roles_json", "candidate_covered_slots_json",
        "candidate_adjudication_statuses_json", "candidate_adjudication_reasons_json",
        "candidate_evidence_json", "final_candidates_json", "audit_date_utc", "source_relpath"
    ]

    rows = []
    for blind_id in sorted(expected):
        answer = answers[blind_id]
        label = final[blind_id]
        a1 = ann1[blind_id]
        a2 = ann2[blind_id]
        key = answer_key[blind_id]
        task = slots[answer["anonymous_task_id"]]
        original = task_key[answer["anonymous_task_id"]]["original_task_id"]
        candidates = label.get("candidates", [])
        source = Path(key["source"])
        try:
            source_relpath = str(source.relative_to(Path.cwd()))
        except ValueError:
            source_relpath = str(source)
        rows.append({
            "blind_answer_id": blind_id,
            "anonymous_task_id": answer["anonymous_task_id"],
            "original_task_id": original,
            "model": key["model"],
            "prompt_id": key["prompt_id"],
            "condition": key["condition"],
            "fold": key["fold"],
            "generation": key["generation"],
            "question": answer["question"],
            "answer": answer["answer"],
            "packages_json": compact(answer.get("packages", [])),
            "package_count": len(answer.get("packages", [])),
            "is_empty_recommendation": len(answer.get("packages", [])) == 0,
            "requirement_slots_json": compact(task.get("slots", [])),
            "required_slot_ids_json": compact([value["slot_id"] for value in task.get("slots", [])]),
            "no_third_party_dependency_needed": task.get("no_third_party_dependency_needed", False),
            "non_dependency_constraints_json": compact(task.get("non_dependency_constraints", [])),
            "annotator_1_adequacy": a1.get("adequacy"),
            "annotator_2_adequacy": a2.get("adequacy"),
            "annotator_1_covered_slots_json": compact(a1.get("covered_slots", [])),
            "annotator_2_covered_slots_json": compact(a2.get("covered_slots", [])),
            "annotator_1_cannot_judge": a1.get("cannot_judge", False),
            "annotator_2_cannot_judge": a2.get("cannot_judge", False),
            "annotator_1_label_json": compact(a1),
            "annotator_2_label_json": compact(a2),
            "final_adequacy": label["adequacy"],
            "final_covered_slots_json": compact(label.get("covered_slots", [])),
            "final_slot_coverage": label.get("slot_coverage"),
            "final_cannot_judge": label.get("cannot_judge", False),
            "final_cannot_judge_reason": label.get("cannot_judge_reason"),
            "answer_adjudication_status": label.get("adjudication_status"),
            "candidate_count": len(candidates),
            "candidate_names_json": compact([value.get("candidate_name") for value in candidates]),
            "candidate_registry_statuses_json": compact([value.get("registry_status") for value in candidates]),
            "candidate_task_roles_json": compact([value.get("task_role") for value in candidates]),
            "candidate_covered_slots_json": compact([value.get("covered_slots", []) for value in candidates]),
            "candidate_adjudication_statuses_json": compact([value.get("adjudication_status") for value in candidates]),
            "candidate_adjudication_reasons_json": compact([value.get("adjudication_reason") for value in candidates]),
            "candidate_evidence_json": compact([value.get("evidence", []) for value in candidates]),
            "final_candidates_json": compact(candidates),
            "audit_date_utc": label.get("audit_date_utc"),
            "source_relpath": source_relpath,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": str(args.output), "rows": len(rows), "columns": len(fields)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
