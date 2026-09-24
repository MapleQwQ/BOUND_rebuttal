#!/usr/bin/env python3
"""汇总 E3 confirmatory200、历史clean回归与双registry口径。"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from getHallucinationPackage.build_edit_examples import check_std_package
from summarize_small_e3 import load_details, metrics, percentile


MODELS = {
    "DeepSeekCoder": ("deepseekcoder", "getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl"),
    "Qwen3": ("qwen3", "getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl"),
    "Llama-3.1": ("llama31", "getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl"),
}
FOLDS = "ABCD"


def norm(value: str) -> str:
    return re.sub(r"[-_.]+", "-", str(value).strip().lower())


def load_model(results_dir: Path, stem: str) -> tuple[dict, dict[str, dict]]:
    base = load_details(results_dir / f"confirm200_{stem}_base_seed20260926.details.jsonl")
    folds = {
        fold: load_details(results_dir / f"confirm200_{stem}_fold{fold}_seed20260926.details.jsonl")
        for fold in FOLDS
    }
    return base, folds


def historical_risk(repo_root: Path, relative: str) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for line in (repo_root / relative).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            grouped.setdefault(str(row["id"]), []).append(row)
    output = {}
    for prompt_id, rows in grouped.items():
        n = len(rows)
        events = sum(bool(row.get("hallucinated")) for row in rows)
        rate = events / n if n else 0.0
        output[prompt_id] = {
            "n": n,
            "sample_hr": rate,
            "stratum": "clean" if rate == 0 else ("low_or_moderate" if rate <= 0.5 else "high"),
        }
    return output


def trial_flags(row: dict) -> list[bool]:
    return [bool(trial.get("hallucinated")) for trial in row["edited"]["trials"]]


def trial_empty(row: dict) -> list[bool]:
    return [not trial.get("packages") for trial in row["edited"]["trials"]]


def snapshot_metrics(rows: list[dict], registry: set[str]) -> dict[str, float]:
    total_responses = total_packages = missing_packages = responses_missing = 0
    for row in rows:
        for trial in row["edited"]["trials"]:
            packages = {str(value).strip() for value in trial.get("packages", []) if str(value).strip()}
            missing = {value for value in packages if not check_std_package(value) and norm(value) not in registry}
            total_responses += 1
            total_packages += len(packages)
            missing_packages += len(missing)
            responses_missing += bool(missing)
    return {
        "response_not_listed_rate": responses_missing / total_responses if total_responses else 0.0,
        "package_not_listed_rate": missing_packages / total_packages if total_packages else 0.0,
        "responses": total_responses,
        "packages": total_packages,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args()

    registry = {norm(value) for value in json.loads(args.registry.read_text(encoding="utf-8"))}
    loaded = {name: load_model(args.results_dir, stem) for name, (stem, _) in MODELS.items()}
    id_sets = []
    for base, folds in loaded.values():
        id_sets += [set(base), *(set(rows) for rows in folds.values())]
    common = sorted(set.intersection(*id_sets), key=lambda value: int(value))
    if len(common) != 200 or any(ids != set(common) for ids in id_sets):
        raise SystemExit("confirmatory conditions do not contain identical 200 prompt IDs")

    per_model = {}
    risk_rows = []
    total_seed_mismatch = 0
    for model, (stem, historical_path) in MODELS.items():
        base, folds = loaded[model]
        hist = historical_risk(args.repo_root, historical_path)
        clean = [prompt_id for prompt_id in common if hist.get(prompt_id, {}).get("stratum") == "clean"]
        base_m = metrics([base[prompt_id] for prompt_id in common])
        fold_m = {fold: metrics([rows[prompt_id] for prompt_id in common]) for fold, rows in folds.items()}
        snapshot_base = snapshot_metrics([base[prompt_id] for prompt_id in common], registry)
        snapshot_folds = {fold: snapshot_metrics([rows[prompt_id] for prompt_id in common], registry) for fold, rows in folds.items()}
        seed_mismatch = 0
        for prompt_id in common:
            base_seeds = [trial.get("seed") for trial in base[prompt_id]["edited"]["trials"]]
            for rows in folds.values():
                seed_mismatch += base_seeds != [trial.get("seed") for trial in rows[prompt_id]["edited"]["trials"]]
        total_seed_mismatch += seed_mismatch

        clean_base_flags = [flag for prompt_id in clean for flag in trial_flags(base[prompt_id])]
        clean_base_empty = [flag for prompt_id in clean for flag in trial_empty(base[prompt_id])]
        induced = {}
        transition = {}
        clean_empty = {}
        for fold, rows in folds.items():
            flags = [flag for prompt_id in clean for flag in trial_flags(rows[prompt_id])]
            empty = [flag for prompt_id in clean for flag in trial_empty(rows[prompt_id])]
            pairs = [
                (base_flag, bound_flag)
                for prompt_id in clean
                for base_flag, bound_flag in zip(trial_flags(base[prompt_id]), trial_flags(rows[prompt_id]))
            ]
            induced[fold] = sum(flags) / len(flags) if flags else None
            transition[fold] = sum((not left) and right for left, right in pairs) / len(pairs) if pairs else None
            clean_empty[fold] = sum(empty) / len(empty) if empty else None

        row = {
            "base": base_m,
            "folds": fold_m,
            "bound_macro_sample_hr": sum(value["sample_hr"] for value in fold_m.values()) / 4,
            "bound_macro_package_hr": sum(value["package_hr"] for value in fold_m.values()) / 4,
            "bound_macro_empty": sum(value["empty_rate"] for value in fold_m.values()) / 4,
            "delta_sample_hr": sum(value["sample_hr"] for value in fold_m.values()) / 4 - base_m["sample_hr"],
            "snapshot_base": snapshot_base,
            "snapshot_folds": snapshot_folds,
            "snapshot_bound_macro_response_not_listed_rate": sum(value["response_not_listed_rate"] for value in snapshot_folds.values()) / 4,
            "historical_clean_prompts": len(clean),
            "historical_clean_base_fresh_sample_hr": sum(clean_base_flags) / len(clean_base_flags) if clean_base_flags else None,
            "historical_clean_base_empty": sum(clean_base_empty) / len(clean_base_empty) if clean_base_empty else None,
            "induced_hallucination_by_fold": induced,
            "clean_to_hallucinated_transition_by_fold": transition,
            "historical_clean_empty_by_fold": clean_empty,
            "seed_schedule_mismatches": seed_mismatch,
        }
        per_model[model] = row
        for prompt_id in common:
            risk_rows.append({"model": model, "prompt_id": prompt_id, **hist.get(prompt_id, {"n": 0, "sample_hr": None, "stratum": "missing"})})

    rng = random.Random(args.seed)
    boot = []
    for _ in range(args.bootstrap):
        sampled = [rng.choice(common) for _ in common]
        deltas = []
        for base, folds in loaded.values():
            base_hr = metrics([base[prompt_id] for prompt_id in sampled])["sample_hr"]
            bound_hr = sum(metrics([rows[prompt_id] for prompt_id in sampled])["sample_hr"] for rows in folds.values()) / 4
            deltas.append(bound_hr - base_hr)
        boot.append(sum(deltas) / 3)

    macro = {
        "base_sample_hr": sum(row["base"]["sample_hr"] for row in per_model.values()) / 3,
        "bound_sample_hr": sum(row["bound_macro_sample_hr"] for row in per_model.values()) / 3,
        "delta_sample_hr": sum(row["delta_sample_hr"] for row in per_model.values()) / 3,
        "delta_sample_hr_ci95": [percentile(boot, 0.025), percentile(boot, 0.975)],
        "base_package_hr": sum(row["base"]["package_hr"] for row in per_model.values()) / 3,
        "bound_package_hr": sum(row["bound_macro_package_hr"] for row in per_model.values()) / 3,
        "base_empty": sum(row["base"]["empty_rate"] for row in per_model.values()) / 3,
        "bound_empty": sum(row["bound_macro_empty"] for row in per_model.values()) / 3,
        "snapshot_base_response_not_listed_rate": sum(row["snapshot_base"]["response_not_listed_rate"] for row in per_model.values()) / 3,
        "snapshot_bound_response_not_listed_rate": sum(row["snapshot_bound_macro_response_not_listed_rate"] for row in per_model.values()) / 3,
        "seed_schedule_mismatches": total_seed_mismatch,
    }
    output = {
        "scope": "confirmatory200 corrected unfiltered shared manifest",
        "n_prompts": 200,
        "n_generation_trials": 15000,
        "per_model": per_model,
        "equal_weight_macro": macro,
        "bootstrap": {"replicates": args.bootstrap, "seed": args.seed, "cluster": "shared prompt"},
        "deployment_snapshot_interpretation": "not-listed is a common-snapshot risk flag, not proof of never-existing",
    }
    (args.results_dir / "confirmatory200_metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.results_dir / "metrics_by_historical_risk.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["model", "prompt_id", "n", "sample_hr", "stratum"])
        writer.writeheader()
        writer.writerows(risk_rows)

    lines = [
        "# E3 confirmatory200 综合结果",
        "",
        "该集合从纠正后的未按风险筛选 eligible pool 简单随机抽取；完整排除审计见 `exclusion_audit_confirmatory200.json`。",
        "",
        "| 模型 | Base Sample-HR | BOUND四折 | 差值 | Base Empty | BOUND Empty | historical clean prompts |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model, row in per_model.items():
        lines.append(
            f"| {model} | {row['base']['sample_hr']:.4f} | {row['bound_macro_sample_hr']:.4f} | {row['delta_sample_hr']:+.4f} | "
            f"{row['base']['empty_rate']:.4f} | {row['bound_macro_empty']:.4f} | {row['historical_clean_prompts']} |"
        )
    lo, hi = macro["delta_sample_hr_ci95"]
    lines += [
        f"| 三模型等权macro | {macro['base_sample_hr']:.4f} | {macro['bound_sample_hr']:.4f} | {macro['delta_sample_hr']:+.4f} | {macro['base_empty']:.4f} | {macro['bound_empty']:.4f} | — |",
        "",
        f"共享prompt bootstrap 95% CI：`[{lo:+.4f}, {hi:+.4f}]`；common-seed mismatch={total_seed_mismatch}。",
        f"Package-HR：Base={macro['base_package_hr']:.4f}，BOUND={macro['bound_package_hr']:.4f}。",
        f"共同snapshot未列名回答率：Base={macro['snapshot_base_response_not_listed_rate']:.4f}，BOUND={macro['snapshot_bound_response_not_listed_rate']:.4f}；未列名不自动等于现实中从未存在。",
        "",
        "历史clean回归的逐模型/逐折 induced hallucination、clean→hallucinated transition 和empty guardrail保存在JSON中；risk strata逐prompt表见 `metrics_by_historical_risk.csv`。",
    ]
    (args.results_dir / "confirmatory200_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(macro))


if __name__ == "__main__":
    main()
