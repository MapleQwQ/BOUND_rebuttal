"""Summarize paired E5 sequence margins, clustering bootstrap resamples by prompt."""

from __future__ import annotations

import csv
import json
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

E5 = Path(__file__).resolve().parents[1]
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = "ABCD"


def load_fold(root: Path, model: str, fold: str,
              allowed: set[tuple[str, str, str, str]] | None = None,
              score_field: str = "mean_logprob") -> dict[str, dict[str, float]]:
    folder = root / model / f"fold_{fold}"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (folder / "per_candidate.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) != meta["n_candidate_scores"]:
        raise ValueError(f"Count mismatch: {folder}")
    scores: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if allowed is not None and (model, str(row["prompt_id"]), row["label"], row["package"]) not in allowed:
            continue
        scores[(row["prompt_id"], row["condition"], row["label"])].append(row[score_field])
    result: dict[str, dict[str, float]] = {}
    for prompt in {key[0] for key in scores}:
        names = [(condition, label) for condition in ("Base", "BOUND")
                 for label in ("valid", "hallucinated")]
        if any(not scores.get((prompt, condition, label)) for condition, label in names):
            continue
        values = {f"{condition}_{label}": float(np.mean(scores[(prompt, condition, label)]))
                  for condition, label in names}
        values["base_margin"] = values["Base_valid"] - values["Base_hallucinated"]
        values["bound_margin"] = values["BOUND_valid"] - values["BOUND_hallucinated"]
        values["delta_margin"] = values["bound_margin"] - values["base_margin"]
        values["delta_valid"] = values["BOUND_valid"] - values["Base_valid"]
        values["delta_hallucinated"] = values["BOUND_hallucinated"] - values["Base_hallucinated"]
        result[prompt] = values
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-manifest", choices=("preliminary", "registry_screened", "cutoff_audited"),
                        default="registry_screened")
    parser.add_argument("--score-field", choices=("mean_logprob", "sum_logprob"), default="mean_logprob")
    parser.add_argument("--leading-space", action="store_true")
    args = parser.parse_args()
    if args.leading_space and args.candidate_manifest == "cutoff_audited":
        parser.error("leading-space cutoff-audited subset is not configured")
    base = E5 / "results/04_sequence_margin"
    presentation = "_leading_space" if args.leading_space else ""
    source = base / ("scores_preliminary" if args.candidate_manifest == "cutoff_audited"
                     else f"scores_{args.candidate_manifest}{presentation}")
    suffix = ("" if args.score_field == "mean_logprob" else "_sum_logprob") + presentation
    root = base / f"scores_{args.candidate_manifest}{suffix}"
    root.mkdir(parents=True, exist_ok=True)
    allowed = None
    if args.candidate_manifest == "cutoff_audited":
        audit = [json.loads(line) for line in (base / "candidate_date_audit.jsonl").read_text(encoding="utf-8").splitlines()]
        allowed = {(row["model"], str(row["prompt_id"]), row["label"], row["name"])
                   for row in audit if (row["label"] == "valid" and row["status"] == "pre_cutoff")
                   or (row["label"] == "hallucinated" and row["status"] in ("post_cutoff", "unknown_absent"))}
    data = {model: {fold: load_fold(source, model, fold, allowed, args.score_field) for fold in FOLDS} for model in MODELS}
    output_rows = []
    for model in MODELS:
        prompt_sets = [set(data[model][fold]) for fold in FOLDS]
        if any(prompt_sets[0] != item for item in prompt_sets[1:]):
            raise ValueError(f"Fold candidate prompt mismatch: {model}")
        for prompt in prompt_sets[0]:
            base = [data[model][fold][prompt]["base_margin"] for fold in FOLDS]
            if max(base) - min(base) > 1e-4:
                raise ValueError(f"Base mismatch across folds: {model}/{prompt}")
        for fold in FOLDS:
            records = list(data[model][fold].values())
            output_rows.append({"model": model, "fold": fold, "n_prompts": len(records),
                                **{metric: float(np.mean([row[metric] for row in records]))
                                   for metric in ("base_margin", "bound_margin", "delta_margin",
                                                  "delta_valid", "delta_hallucinated")},
                                "base_positive_fraction": float(np.mean([row["base_margin"] > 0 for row in records])),
                                "bound_positive_fraction": float(np.mean([row["bound_margin"] > 0 for row in records]))})
    with (root / "per_fold_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    rng = np.random.default_rng(20260924)
    n_boot = 10000
    boot_model: dict[str, np.ndarray] = {}
    model_summary = {}
    for model in MODELS:
        prompts = sorted(data[model]["A"])
        matrix = np.array([[data[model][fold][prompt]["delta_margin"] for fold in FOLDS]
                           for prompt in prompts], dtype=np.float64)
        indices = rng.integers(0, len(prompts), size=(n_boot, len(prompts)))
        boot_model[model] = matrix[indices].mean(axis=(1, 2))
        point = float(matrix.mean())
        model_summary[model] = {"n_paired_prompts": len(prompts), "delta_margin": point,
                                "ci95": np.quantile(boot_model[model], [0.025, 0.975]).tolist(),
                                "four_fold_macro": {metric: float(np.mean([row[metric] for row in output_rows
                                                                             if row["model"] == model]))
                                                    for metric in ("base_margin", "bound_margin", "delta_valid",
                                                                   "delta_hallucinated")}}
    overall_boot = np.mean(np.stack([boot_model[model] for model in MODELS]), axis=0)
    status = {"preliminary": "original_rq2_cutoff_labels", "registry_screened": "registry_screened_sensitivity",
              "cutoff_audited": "date_audited_sensitivity"}[args.candidate_manifest]
    result = {"status": status, "score_field": args.score_field,
              "candidate_presentation": "leading_space" if args.leading_space else "no_leading_space",
              "bootstrap_seed": 20260924,
              "bootstrap_resamples": n_boot, "models": model_summary,
              "three_model_macro": {"delta_margin": float(np.mean([model_summary[m]["delta_margin"] for m in MODELS])),
                                    "ci95": np.quantile(overall_boot, [0.025, 0.975]).tolist()}}
    (root / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
