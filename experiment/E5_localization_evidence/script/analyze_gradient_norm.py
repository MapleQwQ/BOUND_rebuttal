"""Audit and compare original BOUND with gradient-norm localization on RQ3."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
OUT = E5 / "results/06_gradient_norm"
OLD = ROOT / "knowledgeEdit/results/rq3_ablation_20260613"
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
METRICS = ("sample_hr", "package_hr", "valid_rate", "empty_rate", "no_package_rate")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prompt_counts(path: Path) -> dict[str, dict]:
    payload = read(path)
    rows = {}
    for row in payload["details"]:
        key = str(row["id"])
        if key in rows:
            raise ValueError(f"Duplicate prompt: {path}, {key}")
        trials = row["edited"]["trials"]
        if len(trials) != 5:
            raise ValueError(f"Expected five generations: {path}, {key}")
        rows[key] = {
            "question": row["question"],
            "sample_hall": sum(bool(t.get("hallucinated")) for t in trials),
            "valid_sample": sum(bool(t.get("valid")) for t in trials),
            "empty": sum(not str(t.get("answer") or "").strip() for t in trials),
            "no_package": sum(not t.get("packages") for t in trials),
            "hall_packages": sum(len(t.get("hallucinated") or []) for t in trials),
            "valid_packages": sum(len(t.get("valid") or []) for t in trials),
            "package_hr": float(row["edited"]["summary"]["package_hallucination_rate"]),
        }
    if len(rows) != 100:
        raise ValueError(f"Expected 100 RQ3 prompts: {path}")
    return rows


def rates(matrix: np.ndarray) -> dict[str, float]:
    # Columns: sample_hall, valid_sample, empty, no_package, hall_packages, valid_packages, prompt package_hr.
    means = matrix.sum(axis=0)
    return {
        "sample_hr": float(means[0] / (5 * len(matrix))),
        "package_hr": float(means[6] / len(matrix)),
        "valid_rate": float(means[1] / (5 * len(matrix))),
        "empty_rate": float(means[2] / (5 * len(matrix))),
        "no_package_rate": float(means[3] / (5 * len(matrix))),
    }


def bootstrap_rates(matrix: np.ndarray, indices: np.ndarray) -> dict[str, np.ndarray]:
    # matrix=(fold,prompt,7 features), indices=(replicate,prompt).
    selected = matrix[:, indices, :].sum(axis=2)  # fold, replicate, count channel
    # The previous line sums prompts; shape becomes (fold, replicate, channel).
    denom = 5 * indices.shape[1]
    sample = (selected[:, :, 0] / denom).mean(axis=0)
    valid = (selected[:, :, 1] / denom).mean(axis=0)
    empty = (selected[:, :, 2] / denom).mean(axis=0)
    no_package = (selected[:, :, 3] / denom).mean(axis=0)
    package = (selected[:, :, 6] / indices.shape[1]).mean(axis=0)
    return dict(zip(METRICS, (sample, package, valid, empty, no_package)))


def main(matched_budget: bool = False) -> None:
    rng = np.random.default_rng(20260925)
    fold_rows = []
    model_rows = {}
    for model in MODELS:
        control_arrays, gradient_arrays = [], []
        ids_reference = None
        for fold in "ABCD":
            parent = OUT / model / f"fold_{fold}"
            initial_overlap = read(parent / "module_overlap.json")
            mismatch = initial_overlap["selected_original_n"] != initial_overlap["selected_gradient_norm_n"]
            out = parent / "matched_budget" if matched_budget and mismatch else parent
            meta = read(out / "run_metadata.json")
            overlap = dict(initial_overlap)
            if matched_budget and mismatch:
                matched = read(out / "matched_selection.json")["matched_modules"]
                original = set(overlap["selected_original"])
                new = set(matched)
                overlap["selected_gradient_norm_n"] = len(new)
                overlap["selected_intersection"] = len(original & new)
                overlap["selected_jaccard"] = len(original & new) / len(original | new)
            paper_cfg = read(SOURCE / model / f"fold_{fold}/blast_50/blast_config.json")
            cfg = read(out / "experiment_config.json")
            if meta["status"] != "complete" or int(cfg["seed"]) != int(paper_cfg["seed"]):
                raise ValueError(f"Incomplete or seed-mismatched run: {out}")
            if not overlap["historical_control_matches_regenerated_selection"]:
                raise ValueError(f"Historical BOUND module selection not reproduced: {out}")
            if matched_budget and int(meta["n_edited_modules"]) != int(overlap["selected_original_n"]):
                raise ValueError(f"Matched-budget module count differs from BOUND: {out}")
            control = prompt_counts(OLD / model / f"fold_{fold}/BOUND/eval_unseen_prompts.json")
            gradient = prompt_counts(out / "eval_unseen_prompts.json")
            if set(control) != set(gradient):
                raise ValueError(f"Prompt IDs differ: {out}")
            ids = sorted(control, key=int)
            if ids_reference is None:
                ids_reference = ids
            elif ids != ids_reference:
                raise ValueError(f"Prompt IDs differ across folds: {out}")
            if any(control[i]["question"] != gradient[i]["question"] for i in ids):
                raise ValueError(f"Prompt text differs: {out}")
            keys = ("sample_hall", "valid_sample", "empty", "no_package", "hall_packages", "valid_packages", "package_hr")
            a = np.array([[control[i][k] for k in keys] for i in ids], dtype=np.float64)
            b = np.array([[gradient[i][k] for k in keys] for i in ids], dtype=np.float64)
            control_arrays.append(a)
            gradient_arrays.append(b)
            ar, br = rates(a), rates(b)
            row = {"model": model, "fold": fold, "prompts": 100, "generations": 500,
                   "top_k_overlap": overlap["top_k_intersection"],
                   "top_k_jaccard": overlap["top_k_jaccard"],
                   "selected_n_control": overlap["selected_original_n"],
                   "selected_n_gradient": overlap["selected_gradient_norm_n"],
                   "selected_overlap": overlap["selected_intersection"],
                   "selected_jaccard": overlap["selected_jaccard"]}
            for metric in METRICS:
                row[f"bound_{metric}"] = ar[metric]
                row[f"gradient_{metric}"] = br[metric]
                row[f"delta_{metric}"] = br[metric] - ar[metric]
            fold_rows.append(row)
        control_matrix = np.stack(control_arrays)
        gradient_matrix = np.stack(gradient_arrays)
        indices = rng.integers(0, 100, size=(10000, 100))
        a_boot = bootstrap_rates(control_matrix, indices)
        b_boot = bootstrap_rates(gradient_matrix, indices)
        summary = {}
        for metric in METRICS:
            subset = [r for r in fold_rows if r["model"] == model]
            delta_boot = b_boot[metric] - a_boot[metric]
            summary[metric] = {
                "bound_four_fold_macro": float(np.mean([r[f"bound_{metric}"] for r in subset])),
                "gradient_four_fold_macro": float(np.mean([r[f"gradient_{metric}"] for r in subset])),
                "delta_gradient_minus_bound": float(np.mean([r[f"delta_{metric}"] for r in subset])),
                "ci95_prompt_paired_bootstrap": np.quantile(delta_boot, [0.025, 0.975]).tolist(),
            }
        subset = [r for r in fold_rows if r["model"] == model]
        summary["module_overlap"] = {
            "top_k_jaccard_macro": float(np.mean([r["top_k_jaccard"] for r in subset])),
            "selected_jaccard_macro": float(np.mean([r["selected_jaccard"] for r in subset])),
            "same_final_count_folds": int(sum(r["selected_n_control"] == r["selected_n_gradient"] for r in subset)),
        }
        model_rows[model] = summary
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "_matched_budget" if matched_budget else ""
    with (OUT / f"paired_rq3_per_fold{suffix}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fold_rows[0]))
        writer.writeheader()
        writer.writerows(fold_rows)
    result = {"status": "complete", "comparison": "GradientNorm+BOUND-edit minus BOUND",
              "matched_budget": matched_budget,
              "models": model_rows, "n_prompts_per_fold": 100, "n_generations_per_prompt": 5,
              "n_folds_per_model": 4, "bootstrap_resamples": 10000,
              "bootstrap_seed": 20260925,
              "bootstrap_unit": "paired prompt; fold fixed; folds macro-averaged",
              "package_hr_definition": "original RQ3 mean over prompts of within-prompt hallucinated package ratio",
              "empty_rate_definition": "fraction of generations whose raw answer is blank after stripping whitespace",
              "no_package_rate_definition": "fraction of generations with no extracted package, including None"}
    (OUT / f"paired_rq3_summary{suffix}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--matched-budget", action="store_true")
    main(parser.parse_args().matched_budget)
