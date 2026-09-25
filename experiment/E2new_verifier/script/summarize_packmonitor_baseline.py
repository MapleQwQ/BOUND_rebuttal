#!/usr/bin/env python3
"""Summarize native-install PackMonitor vs matched vanilla generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_base_timed import MODELS, RESULTS
from summarize_existing_generations import labels, metric


def timing(rows: list[dict], field: str) -> dict:
    values = np.asarray([row[field] for row in rows], dtype=float)
    return {"mean_seconds": float(values.mean()), "p50_seconds": float(np.quantile(values, .5)),
            "p95_seconds": float(np.quantile(values, .95))}


def main() -> None:
    snapshot = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    manifest = json.loads((ROOT / "BOUND_rebuttal/experiment/E2_verifier_packmonitor/results/manifest.json").read_text(encoding="utf-8"))
    report = {"scope": "native Markdown pip install protocol; frozen 100 prompts/model; 5 generations/prompt; Base/PackMonitor shared seeds; PackMonitor constrained with the E2new frozen current PyPI name snapshot and disclosed official grammar typo correction; same snapshot for metrics", "models": {}, "pending_models": []}
    for model in MODELS:
        path = RESULTS / f"packmonitor_native_{model}.jsonl"
        if model == "qwen3-release":
            nonthinking = RESULTS / "packmonitor_native_qwen3-release_nothink_full.jsonl"
            if nonthinking.exists() and sum(1 for _ in nonthinking.open(encoding="utf-8")) == 1000:
                path = nonthinking
            else:
                report["pending_models"].append(model)
                continue
        runtime = json.loads(path.with_name(path.stem + "_runtime_summary.json").read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        expected_ids = set(map(str, manifest["models"][model]["selected_prompt_ids"]))
        expected_keys = {(prompt_id, generation) for prompt_id in expected_ids for generation in range(5)}
        conditions = {}
        by_condition = {}
        anchor_path = RESULTS / f"packmonitor_native_bound_{model}.jsonl"
        if model == "qwen3-release" and path.name.endswith("_nothink_full.jsonl"):
            nonthinking_anchor = RESULTS / "packmonitor_native_bound_qwen3-release_nothink_full.jsonl"
            if nonthinking_anchor.exists() and sum(1 for _ in nonthinking_anchor.open(encoding="utf-8")) == 500:
                anchor_path = nonthinking_anchor
            else:
                anchor_path = RESULTS / "packmonitor_native_bound_qwen3-release_unavailable.jsonl"
        anchor_rows = [json.loads(line) for line in anchor_path.read_text(encoding="utf-8").splitlines() if line.strip()] if anchor_path.exists() else []
        if model == "qwen3-release" and anchor_rows:
            anchor_runtime = json.loads(anchor_path.with_name(anchor_path.stem + "_runtime_summary.json").read_text(encoding="utf-8"))
            if not anchor_runtime.get("disable_thinking", False):
                raise ValueError("Qwen3 BOUND anchor must use nonthinking protocol")
        condition_rows = {"base": [row for row in rows if row["condition"] == "base"],
                          "packmonitor": [row for row in rows if row["condition"] == "packmonitor"]}
        if len(anchor_rows) == 500:
            condition_rows["bound_fold_A"] = anchor_rows
        for condition, subset in condition_rows.items():
            keys = {(str(row["prompt_id"]), int(row["generation"])) for row in subset}
            if len(subset) != 500 or keys != expected_keys:
                raise ValueError(f"incomplete or duplicate {model} {condition}: {len(subset)} records")
            by_condition[condition] = {(str(row["prompt_id"]), int(row["generation"])): row for row in subset}
            if any(row["error"] is not None for row in subset):
                # Retain all failed answers in denominators; report error rate below.
                pass
            measured = metric([labels(row["packages"], snapshot) for row in subset])
            conditions[condition] = {
                **measured,
                "generation_error_rate": sum(row["error"] is not None for row in subset) / len(subset),
                "install_region_trigger_rate": sum(row["install_region_emitted"] for row in subset) / len(subset),
                "mean_decoded_tokens": float(np.mean([row["decoded_tokens"] for row in subset])),
                "cost": {stage: timing(subset, stage) for stage in ("generation_seconds", "extraction_seconds", "delivery_seconds")},
            }
        if any(by_condition["base"][key]["seed"] != by_condition["packmonitor"][key]["seed"] for key in expected_keys):
            raise ValueError(f"seed pairing failed: {model}")
        if "bound_fold_A" in condition_rows and any(by_condition["base"][key]["seed"] != by_condition["bound_fold_A"][key]["seed"] for key in expected_keys):
            raise ValueError(f"BOUND seed pairing failed: {model}")
        prompt_ids = sorted(expected_ids)
        per_prompt = {}
        for condition in condition_rows:
            per_prompt[condition] = np.asarray([
                np.asarray([labels(by_condition[condition][(prompt_id, generation)]["packages"], snapshot)[:3]
                            for generation in range(5)], dtype=float).sum(axis=0)
                for prompt_id in prompt_ids], dtype=float)
        rng = np.random.default_rng(20260924)
        sampled = rng.integers(0, len(prompt_ids), size=(5000, len(prompt_ids)))
        base_counts = per_prompt["base"]
        pm_counts = per_prompt["packmonitor"]
        sample_deltas = (pm_counts[sampled, 0] - base_counts[sampled, 0]).sum(axis=1) / (len(prompt_ids) * 5)
        pm_h = pm_counts[sampled, 1].sum(axis=1)
        pm_t = pm_counts[sampled, 2].sum(axis=1)
        base_h = base_counts[sampled, 1].sum(axis=1)
        base_t = base_counts[sampled, 2].sum(axis=1)
        package_deltas = np.divide(pm_h, pm_t, out=np.zeros_like(pm_h), where=pm_t > 0) - np.divide(base_h, base_t, out=np.zeros_like(base_h), where=base_t > 0)
        report["models"][model] = {"n_prompts": 100, "n_generations_per_condition": 500,
                                    "source_file": str(path),
                                    "anchor_source_file": str(anchor_path) if "bound_fold_A" in condition_rows else None,
                                    "disable_thinking": runtime.get("disable_thinking", False),
                                    "conditions": conditions,
                                    "one_time_cost": {key: runtime[key] for key in ("model_load_seconds", "warmup_generation_seconds", "matcher_build_seconds")},
                                    "paired_differences": {
                                        "packmonitor_minus_base_sample_hr": conditions["packmonitor"]["sample_hr"] - conditions["base"]["sample_hr"],
                                        "sample_hr_prompt_bootstrap_ci95": [float(x) for x in np.quantile(sample_deltas, (.025, .975))],
                                        "packmonitor_minus_base_package_hr": conditions["packmonitor"]["package_hr"] - conditions["base"]["package_hr"],
                                        "package_hr_prompt_bootstrap_ci95": [float(x) for x in np.quantile(package_deltas, (.025, .975))]}}
    shared_conditions = set.intersection(*(set(item["conditions"]) for item in report["models"].values()))
    macro = {
        condition: {field: float(np.mean([report["models"][model]["conditions"][condition][field] for model in MODELS]))
                    for field in ("sample_hr", "package_hr", "valid_rate", "empty_rate", "generation_error_rate", "install_region_trigger_rate")}
        | {"delivery_mean_seconds": float(np.mean([report["models"][model]["conditions"][condition]["cost"]["delivery_seconds"]["mean_seconds"] for model in MODELS]))}
        for condition in ("base", "packmonitor", "bound_fold_A") if condition in shared_conditions} if len(report["models"]) == len(MODELS) else {}
    if macro:
        report["three_model_equal_mean"] = macro
    output = RESULTS / "packmonitor_native_metrics_summary.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "pending_models": report["pending_models"],
                      "three_model_equal_mean": report.get("three_model_equal_mean")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
