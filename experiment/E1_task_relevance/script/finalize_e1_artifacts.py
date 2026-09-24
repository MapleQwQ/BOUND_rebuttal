#!/usr/bin/env python3
"""生成 E1 设计中约定的最终标准文件名与provenance交付物。"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    task_key = {row["anonymous_task_id"]: row["original_task_id"] for row in json.loads((RES / "formal_task_unblinded_key.json").read_text(encoding="utf-8"))}
    prompts = read_jsonl(RES / "formal_prompt_manifest_anonymous.jsonl")
    adjudicated = read_jsonl(RES / "final_blind_adjudicated_labels.jsonl")

    shutil.copyfile(RES / "formal_prompt_manifest_anonymous.jsonl", RES / "formal_sample_manifest.jsonl")
    shutil.copyfile(RES / "final_blind_annotator_a_labels.jsonl", RES / "annotator_1_raw_labels.jsonl")
    shutil.copyfile(RES / "final_blind_annotator_b_labels.jsonl", RES / "annotator_2_raw_labels.jsonl")
    shutil.copyfile(RES / "final_blind_adjudicated_labels.jsonl", RES / "adjudicated_labels.jsonl")
    shutil.copyfile(RES / "relevance_summary_formal.md", RES / "relevance_summary.md")

    provenance = []
    for row in prompts:
        original = task_key[row["anonymous_task_id"]]
        model, prompt_id = original.split(":", 1)
        provenance.append(
            {
                "anonymous_task_id": row["anonymous_task_id"],
                "model": model,
                "prompt_id": prompt_id,
                "ground_truth_status": "unavailable",
                "prompt_explicit_anchor": "not_used_as_complete_ground_truth",
                "reference_dependency_recall_eligible": "false",
                "reason": "official artifact does not publish prompt-to-source-package/reference-dependency mapping",
            }
        )
    with (RES / "prompt_ground_truth_provenance.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(provenance[0]))
        writer.writeheader()
        writer.writerows(provenance)

    (RES / "source_association_recovery.md").write_text(
        "# 来源包关联恢复结果\n\n"
        "正式60个任务中，`official_prompt_mapping=0`、`verified_reconstruction=0`、"
        "`unavailable=60`。公开Spracklen数据只提供prompt文本；PyPI名称全集不是prompt级标签，"
        "本仓库`valid_reference`又来自模型输出，不能反推来源真值。因此本实验没有计算"
        "Source-Package Hit或Reference Dependency Recall，只报告人工slot覆盖。"
        "逐任务状态见 `prompt_ground_truth_provenance.csv`。\n",
        encoding="utf-8",
    )

    calibration = [
        {"case_id": "same_popular_package", "expected": "不适用任务上的相关性和Adequacy下降"},
        {"case_id": "remove_unique_required_package", "expected": "slot coverage与Adequacy下降"},
        {"case_id": "add_real_irrelevant_package", "expected": "precision下降但原覆盖不变"},
        {"case_id": "documented_alternative", "expected": "合理替代覆盖同一slot，不因名称不同判错"},
        {"case_id": "add_nonexistent_extra", "expected": "存在性风险上升，已有完整Adequacy不自动归零"},
    ]
    write_jsonl(RES / "calibration_cases.jsonl", calibration)
    with (RES / "pilot_timing_and_disagreement.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["phase", "metric", "value", "timing_status"])
        writer.writeheader()
        writer.writerows(
            [
                {"phase": "round2", "metric": "adequacy_exact_agreement", "value": "0.900", "timing_status": "per-item timing not recorded"},
                {"phase": "round2", "metric": "adequacy_kappa", "value": "0.838710", "timing_status": "per-item timing not recorded"},
                {"phase": "round2", "metric": "task_role_exact_agreement", "value": "0.621622", "timing_status": "per-item timing not recorded"},
                {"phase": "formal_final_blind", "metric": "adequacy_exact_agreement", "value": "0.893333", "timing_status": "per-item timing not recorded"},
                {"phase": "formal_final_blind", "metric": "adequacy_kappa", "value": "0.834", "timing_status": "per-item timing not recorded"},
            ]
        )

    evidence: dict[str, dict] = {}
    for row in adjudicated:
        for candidate in row.get("candidates", []):
            name = candidate["candidate_name"]
            evidence.setdefault(
                name,
                {
                    "candidate_name": name,
                    "candidate_type": candidate.get("candidate_type"),
                    "registry_status": candidate.get("registry_status"),
                    "evidence": candidate.get("evidence", []),
                    "note": "shared factual registry/document evidence; task_role remains task-specific",
                },
            )
    write_jsonl(RES / "shared_evidence_registry.jsonl", [evidence[name] for name in sorted(evidence)])
    print(json.dumps({"tasks": len(prompts), "answers": len(adjudicated), "unique_evidence_names": len(evidence)}))


if __name__ == "__main__":
    main()
