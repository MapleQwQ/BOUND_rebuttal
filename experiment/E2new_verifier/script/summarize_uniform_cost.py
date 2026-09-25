#!/usr/bin/env python3
"""Summarize per-answer three-stage BOV and two-stage BOUND timing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from generate_base_timed import MODELS, RESULTS, generation_seed
from summarize_existing_generations import labels, metric


def read(path: Path, key_fields=("prompt_id", "generation")) -> dict[tuple, dict]:
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            key = tuple(str(row[field]) if field == "prompt_id" else int(row[field]) for field in key_fields)
            if key in rows:
                raise ValueError(f"duplicate key {key} in {path}")
            rows[key] = row
    return rows


def stat(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    if not len(array) or not np.all(np.isfinite(array)) or np.any(array < 0):
        raise ValueError("missing/nonfinite/negative time")
    return {"n": len(array), "mean_seconds": float(array.mean()),
            "p50_seconds": float(np.quantile(array, .5)),
            "p95_seconds": float(np.quantile(array, .95)),
            "total_seconds": float(array.sum())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    summary = {"scope": "fixed high-risk unseen prompts; Base generation and verifier original measured stages, Base extraction median 11x deterministic replay, BOUND new GPU0/1 timing", "models": {}}
    snapshot = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    for model, (_, n_prompts, _) in MODELS.items():
        base = read(RESULTS / f"base_timed_{model}.jsonl")
        extracted = read(RESULTS / f"base_extraction_timed_{model}.jsonl")
        verified = read(RESULTS / f"base_timed_verified_{model}.jsonl")
        expected = n_prompts * 5
        if len(base) != expected or set(base) != set(extracted) or set(base) != set(verified):
            raise ValueError(f"incomplete/misaligned Base+BOV for {model}")
        stage = {"generation": [], "extraction_replay": [], "verification_filter": [], "delivery_total": []}
        bov_total_by_key = {}
        for key in base:
            a, e, v = base[key], extracted[key], verified[key]
            if a["answer"] != v["answer"]:
                raise ValueError(f"answer mismatch {model} {key}")
            generate = float(a["base_generation_seconds"])
            parse = float(e["extraction_seconds_median_replay"])
            verify = float(v["verify_total_seconds"])
            stage["generation"].append(generate)
            stage["extraction_replay"].append(parse)
            stage["verification_filter"].append(verify)
            stage["delivery_total"].append(generate + parse + verify)
            bov_total_by_key[key] = generate + parse + verify
        model_summary = {"base_verifier": {key: stat(value) for key, value in stage.items()}, "bound_folds": {}}
        model_summary["quality_metrics"] = {
            "base": metric([labels(base[key]["packages"], snapshot) for key in base]),
            "base_verifier": metric([labels(verified[key]["retained_packages"], snapshot) for key in base]),
            "bound_folds": {}}
        model_summary["base_verifier"]["empty_package_answer_rate"] = sum(not row["packages"] for row in base.values()) / expected
        model_summary["base_verifier"]["mean_unique_packages"] = float(np.mean([len(set(row["packages"])) for row in base.values()]))
        bound_total_by_fold = {}
        for fold in "ABCD":
            path = RESULTS / f"bound_timed_{model}_fold_{fold}.jsonl"
            if not path.exists():
                if args.allow_partial:
                    continue
                raise FileNotFoundError(path)
            bound = read(path)
            if len(bound) != expected and not args.allow_partial:
                raise ValueError(f"incomplete {model} fold {fold}: {len(bound)}/{expected}")
            if not bound:
                continue
            if not set(bound).issubset(set(base)):
                raise ValueError(f"BOUND task IDs mismatch {model} fold {fold}")
            bstage = {"generation": [], "extraction": [], "delivery_total": []}
            bound_total_by_fold[fold] = {}
            for key, row in bound.items():
                if row["model"] != model or row["fold"] != fold or int(row["seed"]) != generation_seed(model, *key):
                    raise ValueError(f"BOUND identity/seed mismatch {model} fold {fold} {key}")
                if abs(float(row["generation_seconds"]) + float(row["extraction_seconds"]) - float(row["delivery_seconds"])) > 1e-7:
                    raise ValueError(f"BOUND stage sum mismatch {model} fold {fold} {key}")
                bstage["generation"].append(float(row["generation_seconds"]))
                bstage["extraction"].append(float(row["extraction_seconds"]))
                bstage["delivery_total"].append(float(row["delivery_seconds"]))
                bound_total_by_fold[fold][key] = float(row["delivery_seconds"])
            model_summary["bound_folds"][fold] = {key: stat(value) for key, value in bstage.items()}
            model_summary["bound_folds"][fold]["empty_package_answer_rate"] = sum(not row["packages"] for row in bound.values()) / len(bound)
            model_summary["bound_folds"][fold]["mean_unique_packages"] = float(np.mean([len(set(row["packages"])) for row in bound.values()]))
            model_summary["quality_metrics"]["bound_folds"][fold] = metric([labels(row["packages"], snapshot) for row in bound.values()])
        if len(model_summary["bound_folds"]) == 4:
            model_summary["bound_four_fold_mean"] = {
                key: {"mean_seconds": float(np.mean([model_summary["bound_folds"][fold][key]["mean_seconds"] for fold in "ABCD"])),
                      "p95_seconds_fold_mean_descriptive": float(np.mean([model_summary["bound_folds"][fold][key]["p95_seconds"] for fold in "ABCD"]))}
                for key in ("generation", "extraction", "delivery_total")}
            model_summary["quality_metrics"]["bound_four_fold_mean"] = {
                field: float(np.mean([model_summary["quality_metrics"]["bound_folds"][fold][field] for fold in "ABCD"]))
                for field in ("sample_hr", "package_hr", "valid_rate", "empty_rate")}
            if not args.allow_partial:
                prompt_ids = sorted({key[0] for key in base})
                differences = np.asarray([
                    np.mean([bound_total_by_fold[fold][(prompt_id, generation)] for fold in "ABCD" for generation in range(5)])
                    - np.mean([bov_total_by_key[(prompt_id, generation)] for generation in range(5)])
                    for prompt_id in prompt_ids], dtype=float)
                rng = np.random.default_rng(20260924)
                sampled = rng.integers(0, len(differences), size=(10000, len(differences)))
                draws = differences[sampled].mean(axis=1)
                model_summary["paired_cost_difference"] = {
                    "bound_minus_bov_mean_seconds_per_answer": float(differences.mean()),
                    "prompt_bootstrap_ci95": [float(x) for x in np.quantile(draws, (.025, .975))],
                    "n_prompts": len(prompt_ids),
                    "uncertainty_scope": "resampled prompt composition conditional on fixed hardware, networks and adapters"}
        summary["models"][model] = model_summary
    if all("bound_four_fold_mean" in item for item in summary["models"].values()):
        summary["three_model_equal_mean"] = {
            "base_verifier": {key: float(np.mean([item["base_verifier"][key]["mean_seconds"] for item in summary["models"].values()])) for key in ("generation", "extraction_replay", "verification_filter", "delivery_total")},
            "bound": {key: float(np.mean([item["bound_four_fold_mean"][key]["mean_seconds"] for item in summary["models"].values()])) for key in ("generation", "extraction", "delivery_total")}}
    output = RESULTS / ("uniform_cost_interim.json" if args.allow_partial else "uniform_cost_summary.json")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "three_model_equal_mean": summary.get("three_model_equal_mean"),
                      "bound_records": {model: {fold: data["generation"]["n"] for fold, data in item["bound_folds"].items()} for model, item in summary["models"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
