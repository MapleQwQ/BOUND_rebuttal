"""Prompt-paired RQ3 comparisons for the two existing E5 ablations."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = "ABCD"
SETTINGS = {
    "01_all_module_lora": "wo_localization_all_lora",
    "02_risk_score": "wo_valid_anchor",
}
METRICS = ("sample_hallucination_rate", "package_hallucination_rate", "sample_valid_rate")


def load(path: Path) -> dict[str, dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in data["details"]:
        key = str(row["id"])
        if key in result:
            raise ValueError(f"Duplicate prompt: {path}/{key}")
        result[key] = {metric: row["edited"]["summary"][metric] for metric in METRICS}
    if len(result) != 100:
        raise ValueError(f"Expected 100 prompts: {path}")
    return result


def main() -> None:
    rng = np.random.default_rng(20260924)
    for experiment, setting in SETTINGS.items():
        rows = []
        model_summary = {}
        for model in MODELS:
            fold_diff = {metric: [] for metric in METRICS}
            for fold in FOLDS:
                base = load(ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model /
                            f"fold_{fold}/BOUND/eval_unseen_prompts.json")
                ablation = load(ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model /
                                f"fold_{fold}/{setting}/eval_unseen_prompts.json")
                if set(base) != set(ablation):
                    raise ValueError(f"Prompt ID mismatch: {model}/{fold}/{setting}")
                ids = sorted(base, key=int)
                record = {"model": model, "fold": fold, "n_prompts": 100}
                for metric in METRICS:
                    base_values = np.array([base[key][metric] for key in ids])
                    ablation_values = np.array([ablation[key][metric] for key in ids])
                    difference = ablation_values - base_values
                    fold_diff[metric].append(difference)
                    record[f"bound_{metric}"] = float(base_values.mean())
                    record[f"ablation_{metric}"] = float(ablation_values.mean())
                    record[f"delta_{metric}"] = float(difference.mean())
                rows.append(record)
            indices = rng.integers(0, 100, size=(10000, 100))
            model_summary[model] = {}
            for metric in METRICS:
                matrix = np.stack(fold_diff[metric])
                boot = matrix[:, indices].mean(axis=(0, 2))
                model_summary[model][metric] = {"delta_ablation_minus_bound": float(matrix.mean()),
                                                "ci95": np.quantile(boot, [0.025, 0.975]).tolist()}
        output = E5 / "results" / experiment
        with (output / "paired_rq3_per_fold.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary = {"comparison": f"{setting} minus BOUND", "n_prompts_per_model_fold": 100,
                   "bootstrap_seed": 20260924, "bootstrap_resamples": 10000,
                   "unit": "prompt, paired within fold; four folds macro-averaged", "models": model_summary}
        (output / "paired_rq3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({experiment: model_summary}, indent=2))


if __name__ == "__main__":
    main()
