#!/usr/bin/env python3
"""比较 E1 round-2 双盲标签并在两人完成后生成揭盲审计。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(left == right for left, right in pairs) / n
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    labels = set(left_counts) | set(right_counts)
    expected = sum((left_counts[x] / n) * (right_counts[x] / n) for x in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def package_rows(row: dict) -> dict[str, dict]:
    items = row.get("packages", row.get("package_labels", []))
    return {str(item["raw_name"]).strip().lower(): item for item in items}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotator-1", required=True)
    parser.add_argument("--annotator-2", required=True)
    parser.add_argument("--blind-key", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--unblinded-key-output", required=True)
    args = parser.parse_args()

    ann1 = {row["blind_answer_id"]: row for row in load_jsonl(Path(args.annotator_1))}
    ann2 = {row["blind_answer_id"]: row for row in load_jsonl(Path(args.annotator_2))}
    shared = sorted(set(ann1) & set(ann2))
    if set(ann1) != set(ann2):
        raise SystemExit("annotator blind_answer_id sets differ")

    adequacy_pairs = [(ann1[key]["adequacy"], ann2[key]["adequacy"]) for key in shared]
    registry_pairs: list[tuple[str, str]] = []
    role_pairs: list[tuple[str, str]] = []
    answer_disagreements = []
    package_disagreements = []
    for key in shared:
        left = ann1[key]
        right = ann2[key]
        if left["adequacy"] != right["adequacy"]:
            answer_disagreements.append(
                {
                    "blind_answer_id": key,
                    "prompt_id": left["prompt_id"],
                    "annotator_1": left["adequacy"],
                    "annotator_2": right["adequacy"],
                }
            )
        left_packages = package_rows(left)
        right_packages = package_rows(right)
        if set(left_packages) != set(right_packages):
            raise SystemExit(f"package sets differ for {key}")
        for package in sorted(left_packages):
            lp = left_packages[package]
            rp = right_packages[package]
            registry_pairs.append((lp["registry_status"], rp["registry_status"]))
            role_pairs.append((lp["task_role"], rp["task_role"]))
            if lp["registry_status"] != rp["registry_status"] or lp["task_role"] != rp["task_role"]:
                package_disagreements.append(
                    {
                        "blind_answer_id": key,
                        "raw_name": package,
                        "annotator_1_registry": lp["registry_status"],
                        "annotator_2_registry": rp["registry_status"],
                        "annotator_1_role": lp["task_role"],
                        "annotator_2_role": rp["task_role"],
                    }
                )

    report = {
        "round": "pilot_round2",
        "n_answers": len(shared),
        "n_package_candidates": len(registry_pairs),
        "adequacy_exact_agreement": sum(a == b for a, b in adequacy_pairs) / len(adequacy_pairs),
        "adequacy_cohen_kappa": kappa(adequacy_pairs),
        "registry_exact_agreement": sum(a == b for a, b in registry_pairs) / len(registry_pairs),
        "registry_cohen_kappa": kappa(registry_pairs),
        "task_role_exact_agreement": sum(a == b for a, b in role_pairs) / len(role_pairs),
        "task_role_cohen_kappa": kappa(role_pairs),
        "answer_disagreements": answer_disagreements,
        "package_disagreements": package_disagreements,
        "note": "slot schemas/granularity differed; slot agreement requires adjudication after atomic-slot guideline revision",
    }
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    blind_key = json.loads(Path(args.blind_key).read_text(encoding="utf-8"))
    Path(args.unblinded_key_output).write_text(
        json.dumps(blind_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if not key.endswith("disagreements")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
