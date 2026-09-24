#!/usr/bin/env python3
"""从逐条 trials 重算 E3 小规模 Base/四折指标与 prompt bootstrap。"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path


def load_details(path: Path) -> dict[str, dict]:
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[str(row["id"])] = row
    return rows


def metrics(rows: list[dict]) -> dict:
    trials = [trial for row in rows for trial in row["edited"]["trials"]]
    n = len(trials)
    hall_responses = sum(bool(trial.get("hallucinated")) for trial in trials)
    hall_mentions = sum(len(trial.get("hallucinated", [])) for trial in trials)
    valid_mentions = sum(len(trial.get("valid", [])) for trial in trials)
    packages = [pkg for trial in trials for pkg in trial.get("packages", [])]
    counts = Counter(packages)
    empty = sum(not trial.get("packages") for trial in trials)
    top = counts.most_common(5)
    return {
        "n_prompts": len(rows),
        "n_generations": n,
        "sample_hr": hall_responses / n if n else None,
        "package_hr": hall_mentions / (hall_mentions + valid_mentions) if hall_mentions + valid_mentions else None,
        "hallucination_responses_per_1000": 1000 * hall_responses / n if n else None,
        "hallucinated_package_mentions_per_1000": 1000 * hall_mentions / n if n else None,
        "empty_rate": empty / n if n else None,
        "avg_packages": len(packages) / n if n else None,
        "distinct_packages_per_1000": 1000 * len(counts) / n if n else None,
        "top1_concentration": top[0][1] / len(packages) if packages and top else None,
        "top5_concentration": sum(value for _, value in top) / len(packages) if packages else None,
        "top5_packages": top,
    }


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    fraction = index - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-details", required=True)
    parser.add_argument("--fold-details", action="append", required=True, help="FOLD=path")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--model-name", default="DeepSeekCoder")
    args = parser.parse_args()

    base = load_details(Path(args.base_details))
    folds = {}
    for spec in args.fold_details:
        name, raw_path = spec.split("=", 1)
        folds[name] = load_details(Path(raw_path))
    common = sorted(set(base).intersection(*(set(rows) for rows in folds.values())))
    if not common:
        raise SystemExit("no common prompt IDs")
    for name, rows in {"base": base, **folds}.items():
        missing = len(set(common) - set(rows))
        if missing:
            raise SystemExit(f"{name} missing {missing} common prompts")

    condition_rows = {"base": [base[key] for key in common]}
    condition_rows.update({f"bound_{name}": [rows[key] for key in common] for name, rows in folds.items()})
    by_condition = {name: metrics(rows) for name, rows in condition_rows.items()}

    seed_mismatches = 0
    for key in common:
        base_seeds = [trial.get("seed") for trial in base[key]["edited"]["trials"]]
        for rows in folds.values():
            if base_seeds != [trial.get("seed") for trial in rows[key]["edited"]["trials"]]:
                seed_mismatches += 1

    fold_sample_hr = [by_condition[f"bound_{name}"]["sample_hr"] for name in folds]
    fold_package_hr = [by_condition[f"bound_{name}"]["package_hr"] for name in folds]
    aggregate = {
        "n_common_prompts": len(common),
        "bound_macro_sample_hr": sum(fold_sample_hr) / len(fold_sample_hr),
        "bound_macro_package_hr": sum(fold_package_hr) / len(fold_package_hr),
        "delta_sample_hr": sum(fold_sample_hr) / len(fold_sample_hr) - by_condition["base"]["sample_hr"],
        "delta_package_hr": sum(fold_package_hr) / len(fold_package_hr) - by_condition["base"]["package_hr"],
        "seed_schedule_mismatches": seed_mismatches,
    }

    rng = random.Random(args.seed)
    deltas = []
    for _ in range(args.bootstrap):
        sampled = [rng.choice(common) for _ in common]
        base_hr = metrics([base[key] for key in sampled])["sample_hr"]
        bound_hrs = [metrics([rows[key] for key in sampled])["sample_hr"] for rows in folds.values()]
        deltas.append(sum(bound_hrs) / len(bound_hrs) - base_hr)
    aggregate["delta_sample_hr_ci95"] = [percentile(deltas, 0.025), percentile(deltas, 0.975)]

    output = {
        "scope": f"{args.model_name} small100 preliminary exact-exclusion sample",
        "validity_label": "model_cutoff_only_pending_deployment_snapshot",
        "conditions": by_condition,
        "aggregate": aggregate,
    }
    Path(args.output_json).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = ["condition", "n_prompts", "n_generations", "sample_hr", "package_hr", "empty_rate", "avg_packages"]
    with Path(args.output_csv).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for condition, row in by_condition.items():
            writer.writerow({"condition": condition, **{key: row[key] for key in fields if key != "condition"}})

    lines = [
        f"# E3 {args.model_name} small100 初步结果",
        "",
        "> 仅适用于 preliminary exact-exclusion manifest 和 model-cutoff labels；deployment snapshot 与完整 near-duplicate audit 尚未完成。",
        "",
        "| 条件 | Sample-HR | Package-HR | Empty | Avg packages |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for condition, row in by_condition.items():
        lines.append(
            f"| {condition} | {row['sample_hr']:.3f} | {row['package_hr']:.3f} | {row['empty_rate']:.3f} | {row['avg_packages']:.3f} |"
        )
    lo, hi = aggregate["delta_sample_hr_ci95"]
    lines.extend(
        [
            "",
            f"四折 BOUND macro Sample-HR={aggregate['bound_macro_sample_hr']:.3f}；Base={by_condition['base']['sample_hr']:.3f}；绝对差={aggregate['delta_sample_hr']:.3f}，prompt bootstrap 95% CI=[{lo:.3f}, {hi:.3f}]。",
            f"Common-seed schedule mismatch count={seed_mismatches}。",
        ]
    )
    Path(args.output_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False))


if __name__ == "__main__":
    main()
