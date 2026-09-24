#!/usr/bin/env python3
"""汇总 E3 三模型 small-100 结果，并按共享 prompt 做联合 bootstrap。"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from summarize_small_e3 import load_details, metrics, percentile


MODELS = {
    "DeepSeekCoder": "deepseekcoder",
    "Qwen3": "qwen3",
    "Llama-3.1": "llama31",
}
FOLDS = ("A", "B", "C", "D")


def load_model(results_dir: Path, stem: str) -> tuple[dict, dict[str, dict]]:
    base = load_details(results_dir / f"{stem}_base_small100_seed42.details.jsonl")
    folds = {
        fold: load_details(results_dir / f"{stem}_fold{fold}_bound_small100_seed42.details.jsonl")
        for fold in FOLDS
    }
    return base, folds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260923)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    loaded = {name: load_model(results_dir, stem) for name, stem in MODELS.items()}
    id_sets = []
    for base, folds in loaded.values():
        id_sets.append(set(base))
        id_sets.extend(set(rows) for rows in folds.values())
    common = sorted(set.intersection(*id_sets))
    if not common:
        raise SystemExit("三模型没有共同 prompt ID")
    if any(ids != set(common) for ids in id_sets):
        raise SystemExit("至少一个条件的 prompt ID 集与共同 manifest 不一致")

    per_model = {}
    total_seed_mismatches = 0
    for model, (base, folds) in loaded.items():
        base_metrics = metrics([base[key] for key in common])
        fold_metrics = {fold: metrics([rows[key] for key in common]) for fold, rows in folds.items()}
        bound_sample_hr = sum(row["sample_hr"] for row in fold_metrics.values()) / len(FOLDS)
        bound_package_hr = sum(row["package_hr"] for row in fold_metrics.values()) / len(FOLDS)
        bound_empty = sum(row["empty_rate"] for row in fold_metrics.values()) / len(FOLDS)
        mismatches = 0
        for key in common:
            expected = [trial.get("seed") for trial in base[key]["edited"]["trials"]]
            for rows in folds.values():
                if expected != [trial.get("seed") for trial in rows[key]["edited"]["trials"]]:
                    mismatches += 1
        total_seed_mismatches += mismatches
        per_model[model] = {
            "base_sample_hr": base_metrics["sample_hr"],
            "bound_macro_sample_hr": bound_sample_hr,
            "delta_sample_hr": bound_sample_hr - base_metrics["sample_hr"],
            "base_package_hr": base_metrics["package_hr"],
            "bound_macro_package_hr": bound_package_hr,
            "delta_package_hr": bound_package_hr - base_metrics["package_hr"],
            "base_empty_rate": base_metrics["empty_rate"],
            "bound_macro_empty_rate": bound_empty,
            "delta_empty_rate": bound_empty - base_metrics["empty_rate"],
            "seed_schedule_mismatches": mismatches,
        }

    rng = random.Random(args.seed)
    boot_deltas = []
    for _ in range(args.bootstrap):
        sampled = [rng.choice(common) for _ in common]
        model_deltas = []
        for base, folds in loaded.values():
            base_hr = metrics([base[key] for key in sampled])["sample_hr"]
            fold_hrs = [metrics([rows[key] for key in sampled])["sample_hr"] for rows in folds.values()]
            model_deltas.append(sum(fold_hrs) / len(FOLDS) - base_hr)
        boot_deltas.append(sum(model_deltas) / len(model_deltas))

    macro = {
        "base_sample_hr": sum(row["base_sample_hr"] for row in per_model.values()) / len(per_model),
        "bound_sample_hr": sum(row["bound_macro_sample_hr"] for row in per_model.values()) / len(per_model),
        "delta_sample_hr": sum(row["delta_sample_hr"] for row in per_model.values()) / len(per_model),
        "base_package_hr": sum(row["base_package_hr"] for row in per_model.values()) / len(per_model),
        "bound_package_hr": sum(row["bound_macro_package_hr"] for row in per_model.values()) / len(per_model),
        "delta_package_hr": sum(row["delta_package_hr"] for row in per_model.values()) / len(per_model),
        "base_empty_rate": sum(row["base_empty_rate"] for row in per_model.values()) / len(per_model),
        "bound_empty_rate": sum(row["bound_macro_empty_rate"] for row in per_model.values()) / len(per_model),
        "delta_empty_rate": sum(row["delta_empty_rate"] for row in per_model.values()) / len(per_model),
        "delta_sample_hr_ci95": [percentile(boot_deltas, 0.025), percentile(boot_deltas, 0.975)],
        "seed_schedule_mismatches": total_seed_mismatches,
    }
    output = {
        "scope": "three-model small100 preliminary exact-exclusion shared sample",
        "n_shared_prompts": len(common),
        "n_models": len(MODELS),
        "n_generation_trials": len(common) * len(MODELS) * (1 + len(FOLDS)) * 5,
        "validity_label": "model_cutoff_only_pending_deployment_snapshot",
        "per_model": per_model,
        "equal_weight_macro": macro,
        "bootstrap": {
            "replicates": args.bootstrap,
            "seed": args.seed,
            "cluster": "shared_prompt_id; same resample indices for every model/method/fold",
        },
    }
    Path(args.output_json).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# E3 三模型 small100 初步综合结果",
        "",
        "> 仅适用于 preliminary exact-exclusion manifest 和各模型 cutoff labels；完整近重复排除与共同 deployment snapshot 尚未完成。",
        "",
        "| 模型 | Base Sample-HR | BOUND 四折 macro | 差值（BOUND−Base） | Base Empty | BOUND Empty macro |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model, row in per_model.items():
        lines.append(
            f"| {model} | {row['base_sample_hr']:.4f} | {row['bound_macro_sample_hr']:.4f} | "
            f"{row['delta_sample_hr']:+.4f} | {row['base_empty_rate']:.4f} | {row['bound_macro_empty_rate']:.4f} |"
        )
    lo, hi = macro["delta_sample_hr_ci95"]
    lines.extend(
        [
            f"| 三模型等权 macro | {macro['base_sample_hr']:.4f} | {macro['bound_sample_hr']:.4f} | "
            f"{macro['delta_sample_hr']:+.4f} | {macro['base_empty_rate']:.4f} | {macro['bound_empty_rate']:.4f} |",
            "",
            f"共享 prompt 配对 bootstrap（{args.bootstrap:,} 次）的三模型 macro Sample-HR 差值 95% CI 为 "
            f"`[{lo:+.4f}, {hi:+.4f}]`。正值表示 BOUND 的幻觉回答比例更高。",
            "",
            f"Package-HR 的三模型等权 macro：Base={macro['base_package_hr']:.4f}，BOUND={macro['bound_package_hr']:.4f}，"
            f"差值={macro['delta_package_hr']:+.4f}。Empty rate 的对应差值为 {macro['delta_empty_rate']:+.4f}。",
            "",
            f"15 个条件合计 {output['n_generation_trials']:,} 次生成；common-seed mismatch={total_seed_mismatches}。",
            "",
            "解释：两个模型的 Sample-HR 点估计上升，仅 Qwen3 下降；联合结果不能支持“BOUND 在未筛选共同提示集上降低幻觉”的主张。该结果仍是 small-100 preliminary evidence，不能代表真实开发者分布，也不能替代完成 leakage audit 后的确认性 E3。",
        ]
    )
    Path(args.output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(macro, ensure_ascii=False))


if __name__ == "__main__":
    main()
