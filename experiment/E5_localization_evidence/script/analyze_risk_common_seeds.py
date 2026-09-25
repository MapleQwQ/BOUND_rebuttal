"""Paired analysis of full-risk versus hall-only generations on changed-module folds."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

E5 = Path(__file__).resolve().parents[1]
ROOT = E5 / "results/02_risk_score/common_seed_eval/full"
METRICS = ("sample_hallucination_rate", "package_hallucination_rate", "sample_valid_rate")


def load(fold: str, condition: str) -> tuple[dict, dict[str, dict]]:
    folder = ROOT / f"fold_{fold}" / condition
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["status"] != "complete" or meta["n_prompts"] != 100 or meta["n_generations_per_prompt"] != 5:
        raise ValueError(f"Incomplete evaluation: {folder}")
    rows = {}
    with (folder / "per_prompt.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = row["prompt_id"]
            if key in rows:
                raise ValueError(f"Duplicate prompt: {folder}/{key}")
            rows[key] = row
    if len(rows) != 100:
        raise ValueError(f"Wrong row count: {folder}")
    return meta, rows


def main() -> None:
    rng = np.random.default_rng(20260924)
    rows = []
    matrices = {metric: [] for metric in METRICS}
    fold_summary = {}
    for fold in "BD":
        a_meta, a = load(fold, "full_risk")
        b_meta, b = load(fold, "hall_only")
        if a_meta["test100_sha256"] != b_meta["test100_sha256"] or a_meta["cutoff"] != b_meta["cutoff"]:
            raise ValueError(f"Input mismatch: {fold}")
        if set(a) != set(b):
            raise ValueError(f"Prompt ID mismatch: {fold}")
        ids = sorted(a, key=int)
        fold_metrics = {}
        for prompt_id in ids:
            full, hall = a[prompt_id], b[prompt_id]
            if [t["seed"] for t in full["trials"]] != [t["seed"] for t in hall["trials"]]:
                raise ValueError(f"Generation seed mismatch: {fold}/{prompt_id}")
            row = {"fold": fold, "prompt_id": prompt_id}
            for metric in METRICS:
                row[f"full_{metric}"] = full["summary"][metric]
                row[f"hall_only_{metric}"] = hall["summary"][metric]
                row[f"delta_{metric}"] = row[f"hall_only_{metric}"] - row[f"full_{metric}"]
            rows.append(row)
        selected = [row for row in rows if row["fold"] == fold]
        indices = rng.integers(0, 100, size=(10000, 100))
        for metric in METRICS:
            values = np.array([row[f"delta_{metric}"] for row in selected], dtype=float)
            matrices[metric].append(values)
            fold_metrics[metric] = {"delta_hall_minus_full": float(values.mean()),
                                    "ci95": np.quantile(values[indices].mean(axis=1), [0.025, 0.975]).tolist()}
        fold_summary[fold] = fold_metrics
    with (ROOT / "paired_per_prompt.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    combined = {}
    for metric in METRICS:
        matrix = np.stack(matrices[metric])
        indices = rng.integers(0, 100, size=(10000, 100))
        boot = matrix[:, indices].mean(axis=(0, 2))
        combined[metric] = {"delta_hall_minus_full": float(matrix.mean()),
                            "ci95": np.quantile(boot, [0.025, 0.975]).tolist()}
    result = {"status": "complete", "folds": fold_summary, "two_fold_macro": combined,
              "bootstrap_seed": 20260924, "bootstrap_resamples": 10000,
              "common_generation_seeds": True, "n_prompts_per_fold": 100, "n_generations_per_prompt": 5}
    (ROOT / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
