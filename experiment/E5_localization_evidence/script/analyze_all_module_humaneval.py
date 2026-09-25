"""Compare the 12 single-sample All-module HumanEval runs with historical single-sample runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
NEW = E5 / "results/01_all_module_lora/humaneval"
OLD = ROOT / "knowledgeEdit/results/humaneval_paper3_20260608"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = "ABCD"


def load(folder: Path) -> tuple[dict, dict[str, int]]:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if summary["n_tasks"] != 164 or summary["num_samples_per_task"] != 1:
        raise ValueError(f"Not a full one-sample run: {folder}")
    results = {}
    with (folder / "samples.jsonl_results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["task_id"] in results:
                raise ValueError(f"Duplicate task: {folder}/{row['task_id']}")
            results[row["task_id"]] = int(row["passed"])
    if len(results) != 164:
        raise ValueError(f"Incomplete task results: {folder}")
    return summary, results


def main() -> None:
    rows = []
    model_results = {}
    rng = np.random.default_rng(20260924)
    for model in MODELS:
        _, base = load(OLD / model / "base")
        task_ids = sorted(base, key=lambda name: int(name.split("/")[-1]))
        bound_matrix, all_matrix = [], []
        for fold in FOLDS:
            old_summary, bound = load(OLD / model / f"fold_{fold}/BLAST-50")
            new_summary, all_module = load(NEW / model / f"fold_{fold}/All-module-LoRA")
            if set(base) != set(bound) or set(base) != set(all_module):
                raise ValueError(f"Task ID mismatch: {model}/{fold}")
            for key in ("max_new_tokens", "temperature", "top_p", "seed"):
                if old_summary["generation_config"][key] != new_summary["generation_config"][key]:
                    raise ValueError(f"Generation config mismatch: {model}/{fold}/{key}")
            bound_values = np.array([bound[name] for name in task_ids], dtype=float)
            all_values = np.array([all_module[name] for name in task_ids], dtype=float)
            bound_matrix.append(bound_values)
            all_matrix.append(all_values)
            rows.append({"model": model, "fold": fold, "n_tasks": 164,
                         "base_pass1": np.mean(list(base.values())),
                         "bound_pass1": bound_values.mean(), "all_module_pass1": all_values.mean(),
                         "delta_all_minus_bound": (all_values - bound_values).mean(),
                         "all_module_generation_seconds": new_summary["timing_seconds"]["generation"]})
        diff = np.stack(all_matrix) - np.stack(bound_matrix)
        indices = rng.integers(0, 164, size=(10000, 164))
        boot = diff[:, indices].mean(axis=(0, 2))
        model_results[model] = {
            "base_pass1": float(np.mean(list(base.values()))),
            "bound_fold_macro_pass1": float(np.stack(bound_matrix).mean()),
            "all_module_fold_macro_pass1": float(np.stack(all_matrix).mean()),
            "delta_all_minus_bound": float(diff.mean()),
            "delta_ci95_task_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist(),
            "all_module_fold_pass1": [float(row["all_module_pass1"]) for row in rows if row["model"] == model],
        }
    output = E5 / "results/01_all_module_lora"
    with (output / "humaneval_single_sample_per_fold.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"status": "single_sample_audit_not_paper_protocol", "bootstrap_seed": 20260924,
               "bootstrap_resamples": 10000, "historical_comparator": str(OLD.relative_to(ROOT)),
               "models": model_results}
    (output / "humaneval_single_sample_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
