#!/usr/bin/env python3
"""比较 E1 两名标注者的正式盲标结果，不读取实验条件揭盲键。"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def normalize_slot_text(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text.lower())


def kappa_summary(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    if not pairs:
        return {
            "n": 0,
            "exact_agreements": 0,
            "exact_agreement": None,
            "expected_agreement": None,
            "cohen_kappa": None,
            "annotator_1_counts": {},
            "annotator_2_counts": {},
            "confusion": {},
        }
    n = len(pairs)
    labels = sorted({str(x) for pair in pairs for x in pair})
    c1 = Counter(str(a) for a, _ in pairs)
    c2 = Counter(str(b) for _, b in pairs)
    agreements = sum(str(a) == str(b) for a, b in pairs)
    observed = agreements / n
    expected = sum((c1[label] / n) * (c2[label] / n) for label in labels)
    kappa = None if math.isclose(expected, 1.0) else (observed - expected) / (1.0 - expected)
    confusion: dict[str, dict[str, int]] = {
        a: {b: 0 for b in labels} for a in labels
    }
    for a, b in pairs:
        confusion[str(a)][str(b)] += 1
    return {
        "n": n,
        "exact_agreements": agreements,
        "exact_agreement": observed,
        "expected_agreement": expected,
        "cohen_kappa": kappa,
        "annotator_1_counts": dict(sorted(c1.items())),
        "annotator_2_counts": dict(sorted(c2.items())),
        "confusion": confusion,
    }


def package_rows(row: dict[str, Any], annotator: int) -> list[dict[str, Any]]:
    return row.get("packages", []) if annotator == 1 else row.get("package_labels", [])


def package_map(row: dict[str, Any], annotator: int) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for package in package_rows(row, annotator):
        key = normalize_package_name(str(package.get("raw_name", "")))
        if not key:
            raise ValueError(f"empty raw_name in {row['blind_answer_id']}")
        if key in mapped:
            raise ValueError(f"duplicate candidate {key!r} in {row['blind_answer_id']}")
        mapped[key] = package
    return mapped


def answer_cannot_judge(row: dict[str, Any], annotator: int) -> bool:
    if annotator == 1:
        return row.get("adequacy") == "cannot_judge"
    return bool(row.get("cannot_judge")) or row.get("adequacy") == "cannot_judge"


def pct(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{100 * float(value):.2f}%"


def num(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.4f}"


def slot_comparison(
    slots1: list[dict[str, Any]], slots2: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_task1 = {row["task_id"]: row for row in slots1}
    by_task2 = {row["task_id"]: row for row in slots2}
    if len(by_task1) != len(slots1) or len(by_task2) != len(slots2):
        raise ValueError("duplicate task_id in slot files")
    tasks = sorted(set(by_task1) | set(by_task2))
    rows: list[dict[str, Any]] = []
    all_best_scores: list[float] = []
    for task_id in tasks:
        left = by_task1.get(task_id)
        right = by_task2.get(task_id)
        left_slots = [] if left is None else left.get("slots", [])
        right_slots = [] if right is None else right.get("slots", [])
        left_texts = [str(x.get("slot_text", "")) for x in left_slots]
        right_texts = [str(x.get("slot_text", "")) for x in right_slots]
        right_norm = [normalize_slot_text(x) for x in right_texts]
        exact_matches = len(set(normalize_slot_text(x) for x in left_texts) & set(right_norm))
        best_matches: list[dict[str, Any]] = []
        for slot in left_slots:
            source = normalize_slot_text(str(slot.get("slot_text", "")))
            candidates = [SequenceMatcher(None, source, target).ratio() for target in right_norm]
            if candidates:
                best_index = max(range(len(candidates)), key=candidates.__getitem__)
                best_score = candidates[best_index]
                best_text = right_texts[best_index]
                best_id = right_slots[best_index].get("slot_id")
                all_best_scores.append(best_score)
            else:
                best_index = None
                best_score = None
                best_text = None
                best_id = None
            best_matches.append(
                {
                    "annotator_1_slot_id": slot.get("slot_id"),
                    "annotator_1_slot_text": slot.get("slot_text"),
                    "annotator_2_best_slot_id": best_id,
                    "annotator_2_best_slot_text": best_text,
                    "normalized_sequence_similarity": best_score,
                }
            )
        rows.append(
            {
                "task_id": task_id,
                "annotator_1_slot_count": len(left_slots),
                "annotator_2_slot_count": len(right_slots),
                "slot_count_difference_a1_minus_a2": len(left_slots) - len(right_slots),
                "normalized_exact_text_matches": exact_matches,
                "annotator_1_slot_texts": left_texts,
                "annotator_2_slot_texts": right_texts,
                "annotator_1_to_annotator_2_best_text_matches": best_matches,
            }
        )
    summary = {
        "task_union_n": len(tasks),
        "task_intersection_n": len(set(by_task1) & set(by_task2)),
        "only_annotator_1_tasks": sorted(set(by_task1) - set(by_task2)),
        "only_annotator_2_tasks": sorted(set(by_task2) - set(by_task1)),
        "same_slot_count_tasks": sum(
            row["annotator_1_slot_count"] == row["annotator_2_slot_count"] for row in rows
        ),
        "different_slot_count_tasks": sum(
            row["annotator_1_slot_count"] != row["annotator_2_slot_count"] for row in rows
        ),
        "annotator_1_total_slots": sum(row["annotator_1_slot_count"] for row in rows),
        "annotator_2_total_slots": sum(row["annotator_2_slot_count"] for row in rows),
        "mean_a1_to_a2_best_normalized_sequence_similarity": (
            sum(all_best_scores) / len(all_best_scores) if all_best_scores else None
        ),
        "note": "文本相似度仅为可复核的词面描述，不代表语义一致性或仲裁结论。",
    }
    return rows, summary


def markdown_report(report: dict[str, Any], slot_rows: list[dict[str, Any]]) -> str:
    answer = report["answer_level"]
    candidate = report["candidate_level"]
    cannot = report["cannot_judge"]
    slot_summary = report["slot_comparison_summary"]
    lines = [
        "# E1 正式双标仲裁前一致性报告",
        "",
        "> 本报告只比较匿名回答与匿名候选标签，未读取实验条件盲化映射，也未进行仲裁。κ 为未加权 Cohen's κ。",
        "",
        "## 样本对齐",
        "",
        f"- 标注者 1 回答数：{report['alignment']['annotator_1_answers']}。",
        f"- 标注者 2 回答数：{report['alignment']['annotator_2_answers']}。",
        f"- 共同回答数：{report['alignment']['common_answers']}。",
        f"- 共同候选数：{report['alignment']['common_candidates']}。",
        f"- 候选集合不一致的回答数：{report['alignment']['answers_with_candidate_set_mismatch']}。",
        "",
        "## 仲裁前一致性",
        "",
        "| 层级/标签 | N | exact agreement | Cohen's κ |",
        "|---|---:|---:|---:|",
        f"| 回答 Adequacy | {answer['adequacy']['n']} | {pct(answer['adequacy']['exact_agreement'])} | {num(answer['adequacy']['cohen_kappa'])} |",
        f"| 候选 registry_status | {candidate['registry_status']['n']} | {pct(candidate['registry_status']['exact_agreement'])} | {num(candidate['registry_status']['cohen_kappa'])} |",
        f"| 候选 task_role | {candidate['task_role']['n']} | {pct(candidate['task_role']['exact_agreement'])} | {num(candidate['task_role']['cohen_kappa'])} |",
        f"| 候选 covered / not-covered | {candidate['covered_binary']['n']} | {pct(candidate['covered_binary']['exact_agreement'])} | {num(candidate['covered_binary']['cohen_kappa'])} |",
        "",
        "covered / not-covered 仅比较候选是否覆盖至少一个各自冻结的 slot；由于两名标注者独立拆分 slots，不比较 slot ID 是否完全相同。",
        "",
        "## cannot_judge 比例",
        "",
        f"- 回答级：标注者 1 为 {cannot['answer_level']['annotator_1_count']}/{cannot['answer_level']['n']} ({pct(cannot['answer_level']['annotator_1_rate'])})；标注者 2 为 {cannot['answer_level']['annotator_2_count']}/{cannot['answer_level']['n']} ({pct(cannot['answer_level']['annotator_2_rate'])})。",
        f"- 候选级 task_role：标注者 1 为 {cannot['candidate_task_role']['annotator_1_count']}/{cannot['candidate_task_role']['n']} ({pct(cannot['candidate_task_role']['annotator_1_rate'])})；标注者 2 为 {cannot['candidate_task_role']['annotator_2_count']}/{cannot['candidate_task_role']['n']} ({pct(cannot['candidate_task_role']['annotator_2_rate'])})。",
        "",
        "## Requirement slots 差异",
        "",
        f"- 共同任务数：{slot_summary['task_intersection_n']}；slot 数量相同：{slot_summary['same_slot_count_tasks']}；数量不同：{slot_summary['different_slot_count_tasks']}。",
        f"- 标注者 1 总 slots：{slot_summary['annotator_1_total_slots']}；标注者 2 总 slots：{slot_summary['annotator_2_total_slots']}。",
        f"- A1→A2 最佳规范化文本相似度均值：{num(slot_summary['mean_a1_to_a2_best_normalized_sequence_similarity'])}。该值只描述词面接近程度，不是语义一致性判断。",
        "",
        "逐任务完整机器可读结果见 `formal_slot_differences.jsonl`。以下保留逐任务数量与原始文本，便于人工仲裁：",
        "",
        "| task_id | A1 数量 | A2 数量 | A1 slot 文本 | A2 slot 文本 |",
        "|---|---:|---:|---|---|",
    ]
    for row in slot_rows:
        left = "；".join(row["annotator_1_slot_texts"]).replace("|", "\\|") or "—"
        right = "；".join(row["annotator_2_slot_texts"]).replace("|", "\\|") or "—"
        lines.append(
            f"| {row['task_id']} | {row['annotator_1_slot_count']} | "
            f"{row['annotator_2_slot_count']} | {left} | {right} |"
        )
    lines.extend(
        [
            "",
            "## 输出说明",
            "",
            "- `formal_disagreements.jsonl`：所有回答级 Adequacy 分歧、候选标签分歧与候选对齐异常。",
            "- `formal_interannotator_agreement.json`：完整统计、边际分布和混淆矩阵。",
            "- `formal_slot_differences.jsonl`：逐任务 slots 数量、文本和词面最佳匹配。",
            "- 本报告不包含方法条件，因此不能用于比较 Base 与 BOUND；须在仲裁完成后另行揭盲分析。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()
    results = args.results_dir.resolve()

    labels1 = read_jsonl(results / "annotator_1_formal_labels.jsonl")
    labels2 = read_jsonl(results / "annotator_2_formal_labels.jsonl")
    slots1 = read_jsonl(results / "annotator_1_formal_slots.jsonl")
    slots2 = read_jsonl(results / "annotator_2_formal_slots.jsonl")
    by_id1 = {row["blind_answer_id"]: row for row in labels1}
    by_id2 = {row["blind_answer_id"]: row for row in labels2}
    if len(by_id1) != len(labels1) or len(by_id2) != len(labels2):
        raise ValueError("duplicate blind_answer_id")

    common_ids = sorted(set(by_id1) & set(by_id2))
    adequacy_pairs: list[tuple[str, str]] = []
    registry_pairs: list[tuple[str, str]] = []
    role_pairs: list[tuple[str, str]] = []
    covered_pairs: list[tuple[bool, bool]] = []
    disagreements: list[dict[str, Any]] = []
    common_candidate_count = 0
    candidate_set_mismatch_answers = 0
    a1_candidate_cannot_judge = 0
    a2_candidate_cannot_judge = 0
    a1_answer_cannot_judge = 0
    a2_answer_cannot_judge = 0

    for answer_id in common_ids:
        row1 = by_id1[answer_id]
        row2 = by_id2[answer_id]
        if row1.get("task_id") != row2.get("task_id"):
            raise ValueError(f"task_id mismatch for {answer_id}")
        adequacy_pairs.append((row1.get("adequacy"), row2.get("adequacy")))
        cj1 = answer_cannot_judge(row1, 1)
        cj2 = answer_cannot_judge(row2, 2)
        a1_answer_cannot_judge += cj1
        a2_answer_cannot_judge += cj2
        if row1.get("adequacy") != row2.get("adequacy"):
            disagreements.append(
                {
                    "record_type": "answer",
                    "blind_answer_id": answer_id,
                    "task_id": row1.get("task_id"),
                    "annotator_1": {
                        "adequacy": row1.get("adequacy"),
                        "slot_coverage": row1.get("slot_coverage"),
                        "covered_slots": row1.get("covered_slots", []),
                        "cannot_judge": cj1,
                        "rationale": row1.get("adequacy_reason"),
                    },
                    "annotator_2": {
                        "adequacy": row2.get("adequacy"),
                        "slot_coverage": row2.get("slot_coverage"),
                        "covered_slots": row2.get("covered_slots", []),
                        "cannot_judge": cj2,
                        "rationale": row2.get("rationale"),
                    },
                }
            )

        packages1 = package_map(row1, 1)
        packages2 = package_map(row2, 2)
        keys1, keys2 = set(packages1), set(packages2)
        if keys1 != keys2:
            candidate_set_mismatch_answers += 1
            disagreements.append(
                {
                    "record_type": "candidate_alignment",
                    "blind_answer_id": answer_id,
                    "task_id": row1.get("task_id"),
                    "only_annotator_1": sorted(keys1 - keys2),
                    "only_annotator_2": sorted(keys2 - keys1),
                }
            )
        for key in sorted(keys1 & keys2):
            package1, package2 = packages1[key], packages2[key]
            common_candidate_count += 1
            registry1, registry2 = package1.get("registry_status"), package2.get("registry_status")
            role1, role2 = package1.get("task_role"), package2.get("task_role")
            covered1 = bool(package1.get("covered_slots", []))
            covered2 = bool(package2.get("covered_slots", []))
            registry_pairs.append((registry1, registry2))
            role_pairs.append((role1, role2))
            covered_pairs.append((covered1, covered2))
            a1_candidate_cannot_judge += role1 == "cannot_judge"
            a2_candidate_cannot_judge += role2 == "cannot_judge"
            differing_fields = []
            if registry1 != registry2:
                differing_fields.append("registry_status")
            if role1 != role2:
                differing_fields.append("task_role")
            if covered1 != covered2:
                differing_fields.append("covered_binary")
            if differing_fields:
                disagreements.append(
                    {
                        "record_type": "package",
                        "blind_answer_id": answer_id,
                        "task_id": row1.get("task_id"),
                        "raw_name": package1.get("raw_name"),
                        "differing_fields": differing_fields,
                        "annotator_1": {
                            "registry_status": registry1,
                            "task_role": role1,
                            "covered": covered1,
                            "covered_slots": package1.get("covered_slots", []),
                            "evidence": package1.get("evidence"),
                        },
                        "annotator_2": {
                            "registry_status": registry2,
                            "task_role": role2,
                            "covered": covered2,
                            "covered_slots": package2.get("covered_slots", []),
                            "evidence": package2.get("evidence"),
                        },
                    }
                )

    slot_rows, slot_summary = slot_comparison(slots1, slots2)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_stage": "pre_adjudication",
        "blinding_status": "method condition key not read",
        "alignment": {
            "annotator_1_answers": len(labels1),
            "annotator_2_answers": len(labels2),
            "common_answers": len(common_ids),
            "only_annotator_1_answers": sorted(set(by_id1) - set(by_id2)),
            "only_annotator_2_answers": sorted(set(by_id2) - set(by_id1)),
            "common_candidates": common_candidate_count,
            "answers_with_candidate_set_mismatch": candidate_set_mismatch_answers,
        },
        "answer_level": {"adequacy": kappa_summary(adequacy_pairs)},
        "candidate_level": {
            "registry_status": kappa_summary(registry_pairs),
            "task_role": kappa_summary(role_pairs),
            "covered_binary": kappa_summary(covered_pairs),
        },
        "cannot_judge": {
            "answer_level": {
                "n": len(common_ids),
                "annotator_1_count": a1_answer_cannot_judge,
                "annotator_1_rate": a1_answer_cannot_judge / len(common_ids) if common_ids else None,
                "annotator_2_count": a2_answer_cannot_judge,
                "annotator_2_rate": a2_answer_cannot_judge / len(common_ids) if common_ids else None,
            },
            "candidate_task_role": {
                "n": common_candidate_count,
                "annotator_1_count": a1_candidate_cannot_judge,
                "annotator_1_rate": a1_candidate_cannot_judge / common_candidate_count if common_candidate_count else None,
                "annotator_2_count": a2_candidate_cannot_judge,
                "annotator_2_rate": a2_candidate_cannot_judge / common_candidate_count if common_candidate_count else None,
            },
        },
        "disagreement_records": {
            "total": len(disagreements),
            "by_record_type": dict(sorted(Counter(row["record_type"] for row in disagreements).items())),
            "path": "formal_disagreements.jsonl",
        },
        "slot_comparison_summary": slot_summary,
        "slot_comparison_path": "formal_slot_differences.jsonl",
    }

    write_jsonl(results / "formal_disagreements.jsonl", disagreements)
    write_jsonl(results / "formal_slot_differences.jsonl", slot_rows)
    with (results / "formal_interannotator_agreement.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    (results / "formal_interannotator_agreement.md").write_text(
        markdown_report(report, slot_rows), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
