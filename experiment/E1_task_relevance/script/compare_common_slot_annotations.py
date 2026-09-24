#!/usr/bin/env python3
"""比较 E1 两名标注者在共同冻结 requirement slots 下的正式盲标结果。"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compare_formal_annotations import (
    answer_cannot_judge,
    kappa_summary,
    normalize_package_name,
    package_map,
    pct,
    read_jsonl,
    write_jsonl,
)


def normalized_slot_set(values: list[str]) -> tuple[str, ...]:
    """共同 slots 已使用同一 ID；排序后用于集合级精确比较。"""
    return tuple(sorted(set(values)))


def json_scalar(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def numeric_coverage_summary(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    comparable = [
        (float(a), float(b)) for a, b in pairs if a is not None and b is not None
    ]
    exact = sum(math.isclose(a, b, abs_tol=1e-12) for a, b in comparable)
    return {
        "n_all_answers": len(pairs),
        "n_comparable_numeric": len(comparable),
        "n_with_null_either_side": len(pairs) - len(comparable),
        "exact_agreements": exact,
        "exact_agreement": exact / len(comparable) if comparable else None,
        "mean_absolute_difference": (
            sum(abs(a - b) for a, b in comparable) / len(comparable) if comparable else None
        ),
        "max_absolute_difference": max((abs(a - b) for a, b in comparable), default=None),
    }


def lean_kappa_summary(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    """高基数集合标签只保存核心统计，避免输出稠密全零混淆矩阵。"""
    full = kappa_summary(pairs)
    return {
        "n": full["n"],
        "exact_agreements": full["exact_agreements"],
        "exact_agreement": full["exact_agreement"],
        "expected_agreement": full["expected_agreement"],
        "cohen_kappa": full["cohen_kappa"],
        "annotator_1_unique_label_count": len(full["annotator_1_counts"]),
        "annotator_2_unique_label_count": len(full["annotator_2_counts"]),
    }


def fmt_rate(value: Any) -> str:
    return "NA" if value is None else f"{100 * float(value):.2f}%"


def fmt_num(value: Any) -> str:
    return "NA" if value is None else f"{float(value):.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()
    results = args.results_dir.resolve()

    labels1 = read_jsonl(results / "annotator_1_formal_labels.jsonl")
    labels2 = read_jsonl(results / "annotator_2_formal_labels_common_slots.jsonl")
    shared_slots = read_jsonl(results / "frozen_requirement_slots.jsonl")
    by_id1 = {row["blind_answer_id"]: row for row in labels1}
    by_id2 = {row["blind_answer_id"]: row for row in labels2}
    if len(by_id1) != len(labels1) or len(by_id2) != len(labels2):
        raise ValueError("duplicate blind_answer_id")
    common_ids = sorted(set(by_id1) & set(by_id2))

    allowed_slots = {
        row["task_id"]: {slot["slot_id"] for slot in row.get("slots", [])}
        for row in shared_slots
    }
    if len(allowed_slots) != len(shared_slots):
        raise ValueError("duplicate task_id in frozen_requirement_slots.jsonl")

    adequacy_pairs: list[tuple[Any, Any]] = []
    registry_pairs: list[tuple[Any, Any]] = []
    role_pairs: list[tuple[Any, Any]] = []
    candidate_covered_pairs: list[tuple[bool, bool]] = []
    candidate_slot_set_pairs: list[tuple[str, str]] = []
    answer_slot_set_pairs: list[tuple[str, str]] = []
    answer_numeric_coverage_pairs: list[tuple[Any, Any]] = []
    disagreements: list[dict[str, Any]] = []
    answer_ids_with_any_disagreement: set[str] = set()
    answer_ids_with_adequacy_disagreement: set[str] = set()
    answer_ids_with_coverage_disagreement: set[str] = set()
    candidate_set_mismatch_answers = 0
    common_candidates = 0
    a1_answer_cannot = a2_answer_cannot = 0
    a1_candidate_cannot = a2_candidate_cannot = 0

    for answer_id in common_ids:
        row1, row2 = by_id1[answer_id], by_id2[answer_id]
        task_id = row1.get("task_id")
        if task_id != row2.get("task_id"):
            raise ValueError(f"task_id mismatch: {answer_id}")
        if task_id not in allowed_slots:
            raise ValueError(f"unknown task_id in shared slots: {task_id}")

        for annotator, row in ((1, row1), (2, row2)):
            answer_slots = set(row.get("covered_slots", []))
            if not answer_slots <= allowed_slots[task_id]:
                raise ValueError(
                    f"A{annotator} answer has out-of-vocabulary slot: {answer_id}"
                )

        adequacy1, adequacy2 = row1.get("adequacy"), row2.get("adequacy")
        adequacy_pairs.append((adequacy1, adequacy2))
        answer_slots1 = normalized_slot_set(row1.get("covered_slots", []))
        answer_slots2 = normalized_slot_set(row2.get("covered_slots", []))
        answer_slot_set_pairs.append((json.dumps(answer_slots1), json.dumps(answer_slots2)))
        answer_numeric_coverage_pairs.append((row1.get("slot_coverage"), row2.get("slot_coverage")))
        cj1, cj2 = answer_cannot_judge(row1, 1), answer_cannot_judge(row2, 2)
        a1_answer_cannot += cj1
        a2_answer_cannot += cj2

        answer_diff_fields: list[str] = []
        if adequacy1 != adequacy2:
            answer_diff_fields.append("adequacy")
            answer_ids_with_adequacy_disagreement.add(answer_id)
        if answer_slots1 != answer_slots2:
            answer_diff_fields.append("covered_slot_set")
            answer_ids_with_coverage_disagreement.add(answer_id)
        cov1, cov2 = row1.get("slot_coverage"), row2.get("slot_coverage")
        numeric_cov_equal = (
            cov1 is None and cov2 is None
        ) or (
            cov1 is not None and cov2 is not None and math.isclose(float(cov1), float(cov2), abs_tol=1e-12)
        )
        if not numeric_cov_equal:
            answer_diff_fields.append("slot_coverage")
            answer_ids_with_coverage_disagreement.add(answer_id)
        if answer_diff_fields:
            answer_ids_with_any_disagreement.add(answer_id)
            disagreements.append(
                {
                    "record_type": "answer",
                    "blind_answer_id": answer_id,
                    "task_id": task_id,
                    "differing_fields": answer_diff_fields,
                    "annotator_1": {
                        "adequacy": adequacy1,
                        "covered_slots": list(answer_slots1),
                        "slot_coverage": cov1,
                        "cannot_judge": cj1,
                        "rationale": row1.get("adequacy_reason"),
                    },
                    "annotator_2": {
                        "adequacy": adequacy2,
                        "covered_slots": list(answer_slots2),
                        "slot_coverage": cov2,
                        "cannot_judge": cj2,
                        "rationale": row2.get("rationale"),
                    },
                }
            )

        packages1, packages2 = package_map(row1, 1), package_map(row2, 2)
        keys1, keys2 = set(packages1), set(packages2)
        if keys1 != keys2:
            candidate_set_mismatch_answers += 1
            answer_ids_with_any_disagreement.add(answer_id)
            disagreements.append(
                {
                    "record_type": "candidate_alignment",
                    "blind_answer_id": answer_id,
                    "task_id": task_id,
                    "only_annotator_1": sorted(keys1 - keys2),
                    "only_annotator_2": sorted(keys2 - keys1),
                }
            )
        for key in sorted(keys1 & keys2):
            p1, p2 = packages1[key], packages2[key]
            common_candidates += 1
            slots1 = normalized_slot_set(p1.get("covered_slots", []))
            slots2 = normalized_slot_set(p2.get("covered_slots", []))
            if not set(slots1) <= allowed_slots[task_id] or not set(slots2) <= allowed_slots[task_id]:
                raise ValueError(f"candidate has out-of-vocabulary slot: {answer_id}/{key}")
            registry1, registry2 = p1.get("registry_status"), p2.get("registry_status")
            role1, role2 = p1.get("task_role"), p2.get("task_role")
            covered1, covered2 = bool(slots1), bool(slots2)
            registry_pairs.append((registry1, registry2))
            role_pairs.append((role1, role2))
            candidate_covered_pairs.append((covered1, covered2))
            candidate_slot_set_pairs.append((json.dumps(slots1), json.dumps(slots2)))
            a1_candidate_cannot += role1 == "cannot_judge"
            a2_candidate_cannot += role2 == "cannot_judge"
            differing_fields: list[str] = []
            if registry1 != registry2:
                differing_fields.append("registry_status")
            if role1 != role2:
                differing_fields.append("task_role")
            if covered1 != covered2:
                differing_fields.append("covered_binary")
            if slots1 != slots2:
                differing_fields.append("covered_slot_set")
            if differing_fields:
                answer_ids_with_any_disagreement.add(answer_id)
                disagreements.append(
                    {
                        "record_type": "package",
                        "blind_answer_id": answer_id,
                        "task_id": task_id,
                        "raw_name": p1.get("raw_name"),
                        "differing_fields": differing_fields,
                        "annotator_1": {
                            "registry_status": registry1,
                            "task_role": role1,
                            "covered": covered1,
                            "covered_slots": list(slots1),
                            "evidence": p1.get("evidence"),
                        },
                        "annotator_2": {
                            "registry_status": registry2,
                            "task_role": role2,
                            "covered": covered2,
                            "covered_slots": list(slots2),
                            "evidence": p2.get("evidence"),
                        },
                    }
                )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_stage": "pre_adjudication_common_frozen_slots",
        "blinding_status": "method condition key not read",
        "slot_basis": {
            "path": "frozen_requirement_slots.jsonl",
            "tasks": len(shared_slots),
            "slots": sum(len(row.get("slots", [])) for row in shared_slots),
        },
        "alignment": {
            "annotator_1_answers": len(labels1),
            "annotator_2_answers": len(labels2),
            "common_answers": len(common_ids),
            "only_annotator_1_answers": sorted(set(by_id1) - set(by_id2)),
            "only_annotator_2_answers": sorted(set(by_id2) - set(by_id1)),
            "common_candidates": common_candidates,
            "answers_with_candidate_set_mismatch": candidate_set_mismatch_answers,
        },
        "answer_level": {
            "adequacy": kappa_summary(adequacy_pairs),
            "covered_slot_set": lean_kappa_summary(answer_slot_set_pairs),
            "numeric_slot_coverage": numeric_coverage_summary(answer_numeric_coverage_pairs),
        },
        "candidate_level": {
            "registry_status": kappa_summary(registry_pairs),
            "task_role": kappa_summary(role_pairs),
            "covered_binary": kappa_summary(candidate_covered_pairs),
            "covered_slot_set": lean_kappa_summary(candidate_slot_set_pairs),
        },
        "cannot_judge": {
            "answer_level": {
                "n": len(common_ids),
                "annotator_1_count": a1_answer_cannot,
                "annotator_1_rate": a1_answer_cannot / len(common_ids) if common_ids else None,
                "annotator_2_count": a2_answer_cannot,
                "annotator_2_rate": a2_answer_cannot / len(common_ids) if common_ids else None,
            },
            "candidate_task_role": {
                "n": common_candidates,
                "annotator_1_count": a1_candidate_cannot,
                "annotator_1_rate": a1_candidate_cannot / common_candidates if common_candidates else None,
                "annotator_2_count": a2_candidate_cannot,
                "annotator_2_rate": a2_candidate_cannot / common_candidates if common_candidates else None,
            },
        },
        "disagreements": {
            "records_total": len(disagreements),
            "records_by_type": dict(sorted(Counter(x["record_type"] for x in disagreements).items())),
            "answers_with_any_reported_disagreement": len(answer_ids_with_any_disagreement),
            "answers_with_adequacy_disagreement": len(answer_ids_with_adequacy_disagreement),
            "answers_with_coverage_disagreement": len(answer_ids_with_coverage_disagreement),
            "path": "formal_common_slot_disagreements.jsonl",
        },
        "sensitivity_note": "此前 formal_interannotator_agreement.* 使用两名标注者各自拆分的 slots，保留为 slot 粒度敏感性分析；本文件为共同冻结 slots 下的主一致率。",
    }

    write_jsonl(results / "formal_common_slot_disagreements.jsonl", disagreements)
    with (results / "formal_common_slot_agreement.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    adequacy = report["answer_level"]["adequacy"]
    registry = report["candidate_level"]["registry_status"]
    role = report["candidate_level"]["task_role"]
    covered = report["candidate_level"]["covered_binary"]
    covered_set = report["candidate_level"]["covered_slot_set"]
    answer_covered = report["answer_level"]["covered_slot_set"]
    numeric_covered = report["answer_level"]["numeric_slot_coverage"]
    markdown = f"""# E1 共同 Requirement Slots 下的正式双标一致性

> 本报告是在方法条件仍盲化、正式仲裁尚未进行时生成。两名标注者均按共同冻结的 60 个任务、105 个 requirement slots 映射回答；原始独立 slots 一致率保留为敏感性分析。

## 对齐检查

- 两侧回答：{len(labels1)} / {len(labels2)}；共同回答：{len(common_ids)}。
- 共同候选：{common_candidates}；候选集合不一致的回答：{candidate_set_mismatch_answers}。
- 未读取方法盲化映射，未修改两份原始标签。

## 主一致率

| 层级/标签 | N | exact agreement | Cohen's κ |
|---|---:|---:|---:|
| 回答 Adequacy | {adequacy['n']} | {fmt_rate(adequacy['exact_agreement'])} | {fmt_num(adequacy['cohen_kappa'])} |
| 候选 registry_status | {registry['n']} | {fmt_rate(registry['exact_agreement'])} | {fmt_num(registry['cohen_kappa'])} |
| 候选 task_role | {role['n']} | {fmt_rate(role['exact_agreement'])} | {fmt_num(role['cohen_kappa'])} |
| 候选 covered/not-covered | {covered['n']} | {fmt_rate(covered['exact_agreement'])} | {fmt_num(covered['cohen_kappa'])} |
| 候选 covered slot 集合 | {covered_set['n']} | {fmt_rate(covered_set['exact_agreement'])} | {fmt_num(covered_set['cohen_kappa'])} |
| 回答 covered slot 集合 | {answer_covered['n']} | {fmt_rate(answer_covered['exact_agreement'])} | {fmt_num(answer_covered['cohen_kappa'])} |

回答级数值 slot coverage 在 {numeric_covered['n_comparable_numeric']} 条可比回答上的精确一致率为 {fmt_rate(numeric_covered['exact_agreement'])}，平均绝对差为 {fmt_num(numeric_covered['mean_absolute_difference'])}。

## 分歧规模

- Adequacy 分歧回答：{len(answer_ids_with_adequacy_disagreement)}/{len(common_ids)}。
- Coverage 分歧回答：{len(answer_ids_with_coverage_disagreement)}/{len(common_ids)}。
- 任一报告字段存在分歧的回答：{len(answer_ids_with_any_disagreement)}/{len(common_ids)}。
- 详细分歧共 {len(disagreements)} 条记录，保存于 `formal_common_slot_disagreements.jsonl`。

## 未知标签

- 回答级 `cannot_judge`：A1={a1_answer_cannot}/{len(common_ids)}，A2={a2_answer_cannot}/{len(common_ids)}。
- 候选级 `task_role=cannot_judge`：A1={a1_candidate_cannot}/{common_candidates}，A2={a2_candidate_cannot}/{common_candidates}。

## 解释边界

- 这里报告的是仲裁前独立判断的一致性，不是仲裁后结果。
- `formal_interannotator_agreement.json/.md` 使用各自独立拆分的 slots，应作为 slot 粒度敏感性结果保留，不覆盖本报告。
- 本报告没有实验条件字段，不能据此比较 Base 与 BOUND。
"""
    (results / "formal_common_slot_agreement.md").write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "adequacy": report["answer_level"]["adequacy"],
                "registry_status": report["candidate_level"]["registry_status"],
                "task_role": report["candidate_level"]["task_role"],
                "covered_binary": report["candidate_level"]["covered_binary"],
                "covered_slot_set_answer": report["answer_level"]["covered_slot_set"],
                "covered_slot_set_candidate": report["candidate_level"]["covered_slot_set"],
                "numeric_slot_coverage": report["answer_level"]["numeric_slot_coverage"],
                "disagreements": report["disagreements"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
