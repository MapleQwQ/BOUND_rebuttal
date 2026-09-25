#!/usr/bin/env python3
"""Summarize fresh timed Base/BOV and the archived four-fold BOUND answers."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict

import numpy as np

from run_existing_generations import FOLDS, MODELS, RESULTS, load, normalize, trials
from summarize_existing_generations import labels, metric, paired_ci


def read_unique(path, model):
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["model"] != model:
                raise ValueError(f"model mismatch in {path}")
            key = str(row["prompt_id"]), int(row["generation"])
            if key in rows:
                raise ValueError(f"duplicate {path}: {key}")
            rows[key] = row
    return rows


def timing_stats(values):
    array = np.asarray(values, dtype=float)
    return {"n": int(len(array)), "mean_seconds": float(array.mean()),
            "median_seconds": float(np.quantile(array, .5)),
            "p95_seconds": float(np.quantile(array, .95)),
            "sum_seconds": float(array.sum())}


def package_hr_ci(by_method, n_prompts, comparator):
    """Resample prompt blocks, then recompute pooled package ratios per fold."""
    rng = np.random.default_rng(20260924)
    draw = rng.integers(0, n_prompts, size=(10000, n_prompts))
    def ratio(name):
        records = np.asarray(by_method[name], dtype=float).reshape(n_prompts, 5, 5)
        h = records[:, :, 1].sum(axis=1)
        t = records[:, :, 2].sum(axis=1)
        return np.divide(h[draw].sum(axis=1), t[draw].sum(axis=1),
                         out=np.zeros(len(draw), dtype=float), where=t[draw].sum(axis=1) > 0)
    bound = np.mean([ratio(f"bound_{fold}") for fold in FOLDS], axis=0)
    diff = bound - ratio(comparator)
    def point(name):
        records = by_method[name]
        total = sum(row[2] for row in records)
        return sum(row[1] for row in records) / total if total else 0.0
    estimate = np.mean([point(f"bound_{fold}") for fold in FOLDS]) - point(comparator)
    return [float(estimate), float(np.quantile(diff, .025)), float(np.quantile(diff, .975))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), help="Write a model-only interim summary")
    args = parser.parse_args()
    snapshot = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    report = {"scope": "full original high-risk unseen prompts; fresh five-trial Base and its verifier; archived four-fold BOUND",
              "index": json.loads((RESULTS / "pypi_index_metadata.json").read_text(encoding="utf-8")),
              "models": {}}
    flat = []
    selected = [(args.model, MODELS[args.model])] if args.model else list(MODELS.items())
    for model, n_prompts in selected:
        base = read_unique(RESULTS / f"base_timed_{model}.jsonl", model)
        bov = read_unique(RESULTS / f"base_timed_verified_{model}.jsonl", model)
        expected = n_prompts * 5
        if len(base) != expected or len(bov) != expected or set(base) != set(bov):
            raise SystemExit(f"incomplete {model}: Base={len(base)} BOV={len(bov)} expected={expected}")
        folds = {fold: {str(row["id"]): row for row in load(model, fold)[1]["details"]} for fold in FOLDS}
        prompt_ids = sorted(folds["A"])
        if len(prompt_ids) != n_prompts or any(set(folds[f]) != set(prompt_ids) for f in FOLDS):
            raise ValueError(f"fold prompt mismatch: {model}")
        measured = defaultdict(list)
        per_prompt = defaultdict(list)
        by_method = defaultdict(list)
        checks = Counter()
        unknown_answers = 0
        snapshot_disagreement = 0
        verifier_exists_snapshot_absent = Counter()
        for prompt_id in prompt_ids:
            prompt_flags = defaultdict(list)
            for generation in range(5):
                key = prompt_id, generation
                a, v = base[key], bov[key]
                if sorted({str(p).strip() for p in a["packages"] if str(p).strip()}) != v["source_packages"]:
                    raise ValueError(f"package mismatch {model} {key}")
                if abs(a["base_generation_seconds"] + v["verify_total_seconds"] - v["bov_total_seconds"]) > 1e-7:
                    raise ValueError(f"timing mismatch {model} {key}")
                for name, packages in (("base", a["packages"]), ("bov", v["retained_packages"])):
                    result = labels(packages, snapshot)
                    by_method[name].append(result)
                    prompt_flags[name].append(result[0])
                measured["base"].append(a["base_generation_seconds"])
                measured["verify"].append(v["verify_total_seconds"])
                measured["bov"].append(v["bov_total_seconds"])
                measured["input_tokens"].append(a["input_tokens"])
                measured["output_tokens_reencoded"].append(a["output_tokens_reencoded"])
                unknown_answers += any(c["status"] == "unknown" for c in v["checks"])
                for c in v["checks"]:
                    checks[c["status"]] += 1
                    checks["http_attempts"] += len(c["attempts"]) if isinstance(c["attempts"], list) else 0
                    if c["status"] in ("absent", "unknown") and normalize(c["name"]) in snapshot:
                        snapshot_disagreement += 1
                    if c["status"] == "exists" and normalize(c["name"]) not in snapshot:
                        verifier_exists_snapshot_absent[c["name"]] += 1
            for fold in FOLDS:
                name = f"bound_{fold}"
                for trial in trials(folds[fold][prompt_id], "edited"):
                    result = labels(trial["packages"], snapshot)
                    by_method[name].append(result)
                    prompt_flags[name].append(result[0])
            for name, flags in prompt_flags.items():
                if len(flags) != 5:
                    raise ValueError(f"wrong number of trials: {model} {prompt_id} {name}")
                per_prompt[name].append(np.mean(flags))
        metrics = {name: metric(rows) for name, rows in by_method.items()}
        metrics["bound_macro"] = {field: float(np.mean([metrics[f"bound_{f}"][field] for f in FOLDS]))
                                  for field in ("sample_hr", "package_hr", "valid_rate", "empty_rate")}
        metrics["bound_macro"]["n_per_fold"] = expected
        for name, item in metrics.items():
            flat.append({"model": model, "condition": name, **item})
        macro = np.mean([per_prompt[f"bound_{fold}"] for fold in FOLDS], axis=0)
        report["models"][model] = {
            "n_prompts": n_prompts, "n_trials_per_condition": expected,
            "metrics": metrics,
            "paired_sample_hr_difference": {
                "bound_minus_base": paired_ci(np.asarray(per_prompt["base"]), macro),
                "bound_minus_bov": paired_ci(np.asarray(per_prompt["bov"]), macro),
                "bov_minus_base": paired_ci(np.asarray(per_prompt["base"]), np.asarray(per_prompt["bov"]))},
            "paired_package_hr_difference": {
                "bound_minus_base": package_hr_ci(by_method, n_prompts, "base"),
                "bound_minus_bov": package_hr_ci(by_method, n_prompts, "bov")},
            "timing": {name: timing_stats(measured[name]) for name in ("base", "verify", "bov")},
            "token_counts": {name: {"mean": float(np.mean(measured[name])),
                                    "sum": int(sum(measured[name]))}
                             for name in ("input_tokens", "output_tokens_reencoded")},
            "verifier": {"checks": dict(checks), "unknown_answer_count": unknown_answers,
                         "snapshot_exists_but_verifier_removed_count": snapshot_disagreement,
                         "verifier_exists_but_snapshot_absent": dict(verifier_exists_snapshot_absent)}}
    suffix = f"_{args.model}" if args.model else ""
    (RESULTS / f"full_timed_summary{suffix}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = list(dict.fromkeys(key for row in flat for key in row))
    with (RESULTS / f"full_timed_by_fold{suffix}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(flat)
    for model, data in report["models"].items():
        print(model, {x: round(data["metrics"][x]["sample_hr"], 4) for x in ("base", "bov", "bound_macro")},
              {x: round(data["timing"][x]["mean_seconds"], 3) for x in ("base", "verify", "bov")})


if __name__ == "__main__":
    main()
