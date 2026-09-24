#!/usr/bin/env python3
"""揭盲并分析 E1 最终匿名双标仲裁结果。"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


FOLDS = "ABCD"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def answer_metrics(rows: list[dict]) -> dict[str, float | int]:
    n = len(rows)
    candidates = [candidate for row in rows for candidate in row.get("candidates", [])]
    relevant = [
        candidate
        for candidate in candidates
        if candidate.get("registry_status") == "exists_at_audit_date"
        and candidate.get("task_role") in {"core_function_support", "optional_support"}
    ]
    strict_core = [candidate for candidate in candidates if candidate.get("registry_status") == "exists_at_audit_date" and candidate.get("task_role") == "core_function_support"]
    unknown = [
        candidate
        for candidate in candidates
        if candidate.get("registry_status") == "registry_cannot_determine" or candidate.get("task_role") == "cannot_judge"
    ]
    defined_coverage = [float(row["slot_coverage"]) for row in rows if row.get("slot_coverage") is not None]
    return {
        "answers": n,
        "adequacy_rate": sum(row["adequacy"] == "adequate" for row in rows) / n,
        "partial_rate": sum(row["adequacy"] == "partially_adequate_with_clear_omission" for row in rows) / n,
        "inadequate_rate": sum(row["adequacy"] == "inadequate" for row in rows) / n,
        "cannot_judge_rate": sum(bool(row.get("cannot_judge")) for row in rows) / n,
        "mean_slot_coverage": sum(defined_coverage) / len(defined_coverage) if defined_coverage else 1.0,
        "empty_rate": sum(not row.get("candidates") for row in rows) / n,
        "avg_candidates": len(candidates) / n,
        "relevant_hit_rate": sum(
            any(
                candidate.get("registry_status") == "exists_at_audit_date"
                and candidate.get("task_role") in {"core_function_support", "optional_support"}
                for candidate in row.get("candidates", [])
            )
            for row in rows
        )
        / n,
        "inclusive_precision": len(relevant) / len(candidates) if candidates else 0.0,
        "inclusive_precision_lower": len(relevant) / len(candidates) if candidates else 0.0,
        "inclusive_precision_upper": (len(relevant) + len(unknown)) / len(candidates) if candidates else 0.0,
        "strict_core_precision": len(strict_core) / len(candidates) if candidates else 0.0,
        "candidate_count": len(candidates),
        "candidate_unknown_count": len(unknown),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--margin", type=float, default=0.05)
    args = parser.parse_args()

    labels = {row["blind_answer_id"]: row for row in load_jsonl(args.labels)}
    key = json.loads(args.blind_key.read_text(encoding="utf-8"))
    if set(labels) != {row["blind_answer_id"] for row in key}:
        raise SystemExit("label/blind-key answer IDs differ")
    joined = []
    for info in key:
        label = labels[info["blind_answer_id"]]
        joined.append({**label, **{name: info[name] for name in ("model", "prompt_id", "condition", "fold", "generation")}})

    grouped: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for row in joined:
        condition = "base" if row["condition"] == "base" else f"fold{row['fold']}"
        grouped[row["model"]][str(row["prompt_id"])][condition] = row
    for model, prompts in grouped.items():
        if len(prompts) != 20:
            raise SystemExit(f"{model}: expected 20 prompts, got {len(prompts)}")
        for prompt_id, conditions in prompts.items():
            if set(conditions) != {"base", "foldA", "foldB", "foldC", "foldD"}:
                raise SystemExit(f"{model}/{prompt_id}: incomplete conditions")

    per_model = {}
    flat_rows = []
    for model, prompts in sorted(grouped.items()):
        base_rows = [conditions["base"] for conditions in prompts.values()]
        fold_rows = {fold: [conditions[f"fold{fold}"] for conditions in prompts.values()] for fold in FOLDS}
        base_metrics = answer_metrics(base_rows)
        fold_metrics = {fold: answer_metrics(rows) for fold, rows in fold_rows.items()}
        bound_macro = {
            metric: sum(fold_metrics[fold][metric] for fold in FOLDS) / 4
            for metric in (
                "adequacy_rate", "partial_rate", "inadequate_rate", "cannot_judge_rate", "mean_slot_coverage",
                "empty_rate", "avg_candidates", "relevant_hit_rate", "inclusive_precision", "strict_core_precision"
            )
        }
        delta = bound_macro["adequacy_rate"] - base_metrics["adequacy_rate"]
        rng = random.Random(args.seed + sum(ord(char) for char in model))
        prompt_ids = sorted(prompts)
        boot = []
        for _ in range(args.bootstrap):
            sample = [rng.choice(prompt_ids) for _ in prompt_ids]
            base_rate = sum(prompts[prompt_id]["base"]["adequacy"] == "adequate" for prompt_id in sample) / len(sample)
            bound_rate = sum(
                sum(prompts[prompt_id][f"fold{fold}"]["adequacy"] == "adequate" for fold in FOLDS) / 4
                for prompt_id in sample
            ) / len(sample)
            boot.append(bound_rate - base_rate)
        ci = [percentile(boot, 0.025), percentile(boot, 0.975)]
        per_model[model] = {
            "n_prompts": len(prompts),
            "base": base_metrics,
            "folds": fold_metrics,
            "bound_macro": bound_macro,
            "delta_adequacy": delta,
            "delta_adequacy_ci95": ci,
            "noninferior_margin": args.margin,
            "noninferior": ci[0] > -args.margin,
        }
        for condition, metrics_row in [("base", base_metrics), *[(f"fold{fold}", fold_metrics[fold]) for fold in FOLDS]]:
            flat_rows.append({"model": model, "condition": condition, **metrics_row})

    rng = random.Random(args.seed)
    model_names = sorted(grouped)
    macro_boot = []
    for _ in range(args.bootstrap):
        deltas = []
        for model in model_names:
            prompts = grouped[model]
            prompt_ids = sorted(prompts)
            sample = [rng.choice(prompt_ids) for _ in prompt_ids]
            base_rate = sum(prompts[prompt_id]["base"]["adequacy"] == "adequate" for prompt_id in sample) / len(sample)
            bound_rate = sum(
                sum(prompts[prompt_id][f"fold{fold}"]["adequacy"] == "adequate" for fold in FOLDS) / 4
                for prompt_id in sample
            ) / len(sample)
            deltas.append(bound_rate - base_rate)
        macro_boot.append(sum(deltas) / len(deltas))
    macro_delta = sum(row["delta_adequacy"] for row in per_model.values()) / len(per_model)
    macro_ci = [percentile(macro_boot, 0.025), percentile(macro_boot, 0.975)]
    macro = {
        "delta_adequacy": macro_delta,
        "delta_adequacy_ci95": macro_ci,
        "noninferior_margin": args.margin,
        "noninferior": macro_ci[0] > -args.margin,
        "base_adequacy": sum(row["base"]["adequacy_rate"] for row in per_model.values()) / len(per_model),
        "bound_adequacy": sum(row["bound_macro"]["adequacy_rate"] for row in per_model.values()) / len(per_model),
        "base_slot_coverage": sum(row["base"]["mean_slot_coverage"] for row in per_model.values()) / len(per_model),
        "bound_slot_coverage": sum(row["bound_macro"]["mean_slot_coverage"] for row in per_model.values()) / len(per_model),
        "base_inclusive_precision": sum(row["base"]["inclusive_precision"] for row in per_model.values()) / len(per_model),
        "bound_inclusive_precision": sum(row["bound_macro"]["inclusive_precision"] for row in per_model.values()) / len(per_model),
        "base_empty_rate": sum(row["base"]["empty_rate"] for row in per_model.values()) / len(per_model),
        "bound_empty_rate": sum(row["bound_macro"]["empty_rate"] for row in per_model.values()) / len(per_model),
    }
    output = {
        "scope": "E1 final anonymous-task, method-blind, adjudicated formal audit",
        "n_models": len(per_model),
        "n_prompts": sum(row["n_prompts"] for row in per_model.values()),
        "n_answers": len(joined),
        "per_model": per_model,
        "equal_weight_macro": macro,
        "bootstrap": {"replicates": args.bootstrap, "seed": args.seed, "cluster": "prompt within model"},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "relevance_metrics_by_model_fold.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "relevance_metrics_by_model_fold.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    lines = [
        "# E1 正式匿名双标结果",
        "",
        "范围：每模型20个high-risk unseen prompts，Base与四个BOUND folds各一条generation-0，共300条回答。任务ID、模型、方法和fold在独立标注及仲裁完成前均隐藏。",
        "",
        "| 模型 | Base Adequacy | BOUND四折 | 差值 | 95% CI | 非劣性(δ=5pp) | Base/BOUND slot coverage | Base/BOUND empty |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for model, row in per_model.items():
        lo, hi = row["delta_adequacy_ci95"]
        lines.append(
            f"| {model} | {row['base']['adequacy_rate']:.3f} | {row['bound_macro']['adequacy_rate']:.3f} | "
            f"{row['delta_adequacy']:+.3f} | [{lo:+.3f},{hi:+.3f}] | {'支持' if row['noninferior'] else '不支持/证据不足'} | "
            f"{row['base']['mean_slot_coverage']:.3f}/{row['bound_macro']['mean_slot_coverage']:.3f} | "
            f"{row['base']['empty_rate']:.3f}/{row['bound_macro']['empty_rate']:.3f} |"
        )
    lo, hi = macro_ci
    lines += [
        f"| 三模型等权macro | {macro['base_adequacy']:.3f} | {macro['bound_adequacy']:.3f} | {macro_delta:+.3f} | [{lo:+.3f},{hi:+.3f}] | {'支持' if macro['noninferior'] else '不支持/证据不足'} | {macro['base_slot_coverage']:.3f}/{macro['bound_slot_coverage']:.3f} | {macro['base_empty_rate']:.3f}/{macro['bound_empty_rate']:.3f} |",
        "",
        f"Inclusive Task-Relevant Precision（三模型等权）：Base={macro['base_inclusive_precision']:.3f}，BOUND={macro['bound_inclusive_precision']:.3f}。",
        "",
        "非劣性只在95%区间下界严格高于-0.05时成立；区间跨0或p值不显著不自动证明保持。包级unknown没有静默删除，逐条件上下界与unknown计数保存在JSON/CSV。",
    ]
    (args.output_dir / "relevance_summary_formal.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(macro, ensure_ascii=False))


if __name__ == "__main__":
    main()
