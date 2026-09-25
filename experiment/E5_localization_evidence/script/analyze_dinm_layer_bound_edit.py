"""Prompt-paired RQ3 analysis for original DINM localization plus BOUND edit."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
OUT = E5 / "results/05_dinm_localization_bound_edit"
OLD = ROOT / "knowledgeEdit/results/rq3_ablation_20260613"
ORIGINAL_DINM = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
METRICS = ("sample_hallucination_rate", "package_hallucination_rate", "sample_valid_rate", "empty_rate")


def load(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = {}
    for row in payload["details"]:
        key = str(row["id"])
        if key in rows:
            raise ValueError(f"Duplicate prompt ID: {path}/{key}")
        trials = row["edited"]["trials"]
        if len(trials) != 5 or row["edited"]["summary"]["n_trials"] != 5:
            raise ValueError(f"Expected five generations: {path}/{key}")
        values = {metric: float(row["edited"]["summary"][metric]) for metric in METRICS[:-1]}
        values["empty_rate"] = sum(not trial.get("packages") for trial in trials) / 5
        values["question"] = row["question"]
        rows[key] = values
    if len(rows) != 100:
        raise ValueError(f"Expected 100 unseen prompts: {path}")
    return rows


def main() -> None:
    rng = np.random.default_rng(20260925)
    per_fold = []
    costs = []
    models = {}
    for model in MODELS:
        differences = {metric: [] for metric in METRICS}
        dinm_differences = {metric: [] for metric in METRICS}
        bound_values = {metric: [] for metric in METRICS}
        dinm_values = {metric: [] for metric in METRICS}
        hybrid_values = {metric: [] for metric in METRICS}
        reference_ids = None
        for fold in "ABCD":
            out = OUT / model / f"fold_{fold}" / "DINM-layer+BOUND-edit"
            metadata = json.loads((out / "run_metadata.json").read_text())
            if metadata["status"] != "complete":
                raise ValueError(f"Incomplete hybrid run: {out}")
            config = json.loads((out / "experiment_config.json").read_text())
            paper_config = json.loads((ORIGINAL_DINM / model / f"fold_{fold}/blast_50/blast_config.json").read_text())
            if int(config["seed"]) != int(paper_config["seed"]):
                raise ValueError(f"Training seed differs from final paper BOUND adapter: {out}")
            if metadata.get("training_seed", config["seed"]) != config["seed"]:
                raise ValueError(f"Training seed metadata disagrees with config: {out}")
            loc = json.loads((out / "dinm_layer_selection.json").read_text())
            bound = load(OLD / model / f"fold_{fold}/BOUND/eval_unseen_prompts.json")
            hybrid = load(out / "eval_unseen_prompts.json")
            original_full = json.loads((ORIGINAL_DINM / model / f"fold_{fold}/dinm_50/eval_unseen_prompts.json").read_text())
            original_rows = {str(row["id"]): row for row in original_full["details"]}
            if set(bound) != set(hybrid):
                raise ValueError(f"Prompt IDs differ: {model}/{fold}")
            ids = sorted(bound, key=int)
            if any(key not in original_rows for key in ids):
                raise ValueError(f"Original DINM missing RQ3 prompt: {model}/{fold}")
            if reference_ids is None:
                reference_ids = ids
            elif reference_ids != ids:
                raise ValueError(f"Unseen prompt set differs across folds: {model}/{fold}")
            if any(bound[key]["question"] != hybrid[key]["question"] for key in ids):
                raise ValueError(f"Prompt text differs: {model}/{fold}")
            if any(bound[key]["question"] != original_rows[key]["question"] for key in ids):
                raise ValueError(f"Original DINM prompt text differs: {model}/{fold}")
            row = {"model": model, "fold": fold, "n_prompts": 100, "n_generations": 500,
                   "selected_layers": ",".join(map(str, loc["unique_layers"])),
                   "n_modules": metadata["n_edited_modules"]}
            for metric in METRICS:
                before = np.array([bound[key][metric] for key in ids])
                after = np.array([hybrid[key][metric] for key in ids])
                if metric == "empty_rate":
                    original = np.array([sum(not t.get("packages") for t in original_rows[key]["edited"]["trials"]) / 5 for key in ids])
                else:
                    original = np.array([float(original_rows[key]["edited"]["summary"][metric]) for key in ids])
                if any(len(original_rows[key]["edited"]["trials"]) != 5 for key in ids):
                    raise ValueError(f"Original DINM lacks five generations: {model}/{fold}")
                delta = after - before
                differences[metric].append(delta)
                dinm_differences[metric].append(after - original)
                bound_values[metric].append(before)
                dinm_values[metric].append(original)
                hybrid_values[metric].append(after)
                row[f"bound_{metric}"] = float(before.mean())
                row[f"original_dinm_{metric}"] = float(original.mean())
                row[f"hybrid_{metric}"] = float(after.mean())
                row[f"delta_{metric}"] = float(delta.mean())
            per_fold.append(row)
            costs.append({"model": model, "fold": fold, **{k: metadata[k] for k in (
                "gpu", "dinm_historical_localization_seconds", "edit_seconds", "eval_seconds",
                "peak_edit_reserved_mib", "n_edited_modules", "n_trainable_adapter_parameters",
                "adapter_bytes", "adapter_sha256", "dinm_report_sha256", "edit_cases_sha256")}})
        indices = rng.integers(0, 100, size=(10000, 100))
        models[model] = {}
        for metric in METRICS:
            matrix = np.stack(differences[metric])
            dinm_matrix = np.stack(dinm_differences[metric])
            boot = matrix[:, indices].mean(axis=(0, 2))
            dinm_boot = dinm_matrix[:, indices].mean(axis=(0, 2))
            models[model][metric] = {
                "bound_four_fold_macro": float(np.stack(bound_values[metric]).mean()),
                "original_dinm_four_fold_macro": float(np.stack(dinm_values[metric]).mean()),
                "hybrid_four_fold_macro": float(np.stack(hybrid_values[metric]).mean()),
                "delta_hybrid_minus_bound": float(matrix.mean()),
                "ci95_prompt_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist(),
                "delta_hybrid_minus_original_dinm": float(dinm_matrix.mean()),
                "ci95_hybrid_minus_original_dinm": np.quantile(dinm_boot, [0.025, 0.975]).tolist(),
            }
    with (OUT / "paired_rq3_per_fold.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_fold[0]))
        writer.writeheader()
        writer.writerows(per_fold)
    with (OUT / "cost_per_fold.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(costs[0]))
        writer.writeheader()
        writer.writerows(costs)
    summary = {"status": "complete", "comparison": "DINM-layer+BOUND-edit minus BOUND",
               "n_models": 3, "n_folds_per_model": 4, "n_prompts_per_fold": 100,
               "n_generations_per_prompt": 5, "bootstrap_seed": 20260925,
               "bootstrap_resamples": 10000, "bootstrap_unit": "prompt; folds fixed and macro-averaged",
               "models": models}
    (OUT / "paired_rq3_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
