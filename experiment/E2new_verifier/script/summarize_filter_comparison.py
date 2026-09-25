#!/usr/bin/env python3
"""Compare frozen-snapshot filtering, empty answers, and verifier token overhead."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from generate_base_timed import MODELS, RESULTS
from run_existing_generations import normalize
from summarize_existing_generations import labels, metric


def read(path: Path, key_fields: tuple[str, ...]) -> dict[tuple, dict]:
    output = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            marker = tuple(str(row[field]) if field in ("model", "fold", "prompt_id") else int(row[field])
                           for field in key_fields)
            if marker in output:
                raise ValueError(f"duplicate key {marker} in {path}")
            output[marker] = row
    return output


def distribution(values: list[float]) -> dict:
    data = np.asarray(values, dtype=float)
    if not len(data) or not np.all(np.isfinite(data)):
        raise ValueError("empty or nonfinite distribution")
    return {"mean": float(data.mean()), "p50": float(np.quantile(data, .5)),
            "p95": float(np.quantile(data, .95))}


def filter_audit(original: dict, verified: dict, snapshot: set[str]) -> dict:
    source = sorted({str(name).strip() for name in original["packages"] if str(name).strip()})
    if source != verified["source_packages"] or original["answer"] != verified["answer"]:
        raise ValueError("source/verified answer or package mismatch")
    checks = verified["checks"]
    if [check["name"] for check in checks] != source:
        raise ValueError("verification checks are not one per source package")
    retained = [check["name"] for check in checks if check["status"] in ("exists", "stdlib")]
    if retained != verified["retained_packages"]:
        raise ValueError("retention mismatch")
    removed = [check for check in checks if check["status"] not in ("exists", "stdlib")]
    absent_current = lambda name: name not in sys.stdlib_module_names and normalize(name) not in snapshot
    return {"filtered_total": len(removed),
            "filtered_invalid_current": sum(absent_current(check["name"]) for check in removed),
            "filtered_unknown_online": sum(check["status"] == "unknown" for check in removed),
            "filtered_snapshot_valid": sum(not absent_current(check["name"]) for check in removed),
            "online_http_attempts": sum(len(check["attempts"]) if isinstance(check["attempts"], list) else 0 for check in checks),
            "online_candidate_count": sum(check["status"] != "stdlib" for check in checks),
            "source_package_count": len(source), "retained_package_count": len(retained),
            "filtered_empty": int(not retained),
            "source_empty": int(not source),
            "extra_llm_tokens": verified.get("extra_llm_tokens_from_verifier", 0)}


def summarize_verified(pairs: list[tuple[dict, dict]], snapshot: set[str],
                       generation_field: str, extraction_field: str, verify_field: str) -> dict:
    final_labels = [labels(verified["retained_packages"], snapshot) for _, verified in pairs]
    audits = [filter_audit(original, verified, snapshot) for original, verified in pairs]
    result = {"n": len(pairs), "final_quality": metric(final_labels),
              "filter": {field: float(np.mean([audit[field] for audit in audits]))
                         for field in audits[0]},
              "timing_seconds": {
                  "generation": distribution([float(verified[generation_field]) for _, verified in pairs]),
                  "extraction": distribution([float(verified[extraction_field]) for _, verified in pairs]),
                  "online_verify_filter": distribution([float(verified[verify_field]) for _, verified in pairs]),
                  "total_delivery": distribution([float(verified[generation_field]) + float(verified[extraction_field]) + float(verified[verify_field]) for _, verified in pairs])}}
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    snapshot = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    all_bound_verified = read(RESULTS / "bound_timed_verified_all.jsonl", ("model", "fold", "prompt_id", "generation"))
    report = {"scope": "same frozen high-risk tasks, online verifier outputs; current existence judged by frozen PyPI snapshot, not by runtime HTTP status", "models": {}}
    for model, (_, n_prompts, _) in MODELS.items():
        expected = n_prompts * 5
        base = read(RESULTS / f"base_timed_{model}.jsonl", ("prompt_id", "generation"))
        bov = read(RESULTS / f"base_timed_verified_{model}.jsonl", ("prompt_id", "generation"))
        if len(base) != expected or set(base) != set(bov):
            raise ValueError(f"incomplete Base+BOV {model}")
        extraction = read(RESULTS / f"base_extraction_timed_{model}.jsonl", ("prompt_id", "generation"))
        if set(base) != set(extraction):
            raise ValueError(f"incomplete Base extraction replay {model}")
        bov_pairs = []
        for key in base:
            row = dict(bov[key])
            row["extraction_seconds_median_replay"] = extraction[key]["extraction_seconds_median_replay"]
            row["extra_llm_tokens_from_verifier"] = 0
            bov_pairs.append((base[key], row))
        model_result = {"n_prompts": n_prompts,
                        "base": {"quality": metric([labels(row["packages"], snapshot) for row in base.values()]),
                                 "mean_input_tokens": float(np.mean([row["input_tokens"] for row in base.values()])),
                                 "mean_output_tokens_reencoded": float(np.mean([row["output_tokens_reencoded"] for row in base.values()])),
                                 "timing_seconds": {
                                     "generation": distribution([row["base_generation_seconds"] for row in base.values()]),
                                     "extraction": distribution([extraction[key]["extraction_seconds_median_replay"] for key in base]),
                                     "total_delivery": distribution([base[key]["base_generation_seconds"] + extraction[key]["extraction_seconds_median_replay"] for key in base])},
                                 "extra_verifier_llm_tokens": 0},
                        "base_online_verifier": summarize_verified(bov_pairs, snapshot, "base_generation_seconds", "extraction_seconds_median_replay", "verify_total_seconds"),
                        "bound_folds": {}, "bound_online_verifier_folds": {}}
        model_result["base_online_verifier"]["extra_verifier_llm_tokens"] = 0
        token_path = RESULTS / f"bound_tokens_reencoded_{model}.jsonl"
        token_rows = read(token_path, ("fold", "prompt_id", "generation")) if token_path.exists() else {}
        for fold in "ABCD":
            bound_path = RESULTS / f"bound_timed_{model}_fold_{fold}.jsonl"
            if not bound_path.exists():
                if args.allow_partial:
                    continue
                raise FileNotFoundError(bound_path)
            bound = read(bound_path, ("prompt_id", "generation"))
            selected = {(key[2], key[3]): row for key, row in all_bound_verified.items()
                        if key[:2] == (model, fold)}
            if not args.allow_partial and (len(bound) != expected or set(bound) != set(selected)):
                raise ValueError(f"incomplete BOUND+OV {model} fold {fold}: {len(bound)}/{len(selected)}/{expected}")
            common = sorted(set(bound) & set(selected))
            if not common:
                continue
            model_result["bound_folds"][fold] = {"n": len(bound),
                "quality": metric([labels(row["packages"], snapshot) for row in bound.values()]),
                "timing_seconds": {
                    "generation": distribution([row["generation_seconds"] for row in bound.values()]),
                    "extraction": distribution([row["extraction_seconds"] for row in bound.values()]),
                    "total_delivery": distribution([row["delivery_seconds"] for row in bound.values()])},
                "extra_verifier_llm_tokens": 0}
            if token_rows:
                selected_tokens = {key: token_rows[(fold, *key)] for key in bound}
                model_result["bound_folds"][fold]["mean_input_tokens"] = float(np.mean([row["input_tokens"] for row in selected_tokens.values()]))
                model_result["bound_folds"][fold]["mean_output_tokens_reencoded"] = float(np.mean([row["output_tokens_reencoded"] for row in selected_tokens.values()]))
                model_result["bound_folds"][fold]["mean_delta_output_tokens_vs_base"] = float(np.mean([row["delta_output_tokens_vs_base"] for row in selected_tokens.values()]))
            model_result["bound_online_verifier_folds"][fold] = summarize_verified(
                [(bound[key], selected[key]) for key in common], snapshot,
                "generation_seconds", "extraction_seconds", "online_verify_filter_seconds")
            model_result["bound_online_verifier_folds"][fold]["extra_verifier_llm_tokens"] = 0
        if (len(model_result["bound_folds"]) == 4 and len(model_result["bound_online_verifier_folds"]) == 4
                and all(model_result["bound_folds"][fold]["n"] == expected
                        and model_result["bound_online_verifier_folds"][fold]["n"] == expected
                        for fold in "ABCD")):
            fields = ("sample_hr", "package_hr", "valid_rate", "empty_rate")
            for source, target in (("bound_folds", "bound_four_fold_mean"),
                                   ("bound_online_verifier_folds", "bound_online_verifier_four_fold_mean")):
                block = model_result[source]
                nested = "quality" if source == "bound_folds" else "final_quality"
                model_result[target] = {
                    "quality": {field: float(np.mean([block[fold][nested][field] for fold in "ABCD"])) for field in fields},
                    "mean_delivery_seconds": float(np.mean([block[fold]["timing_seconds"]["total_delivery"]["mean"] for fold in "ABCD"]))}
                for stage in (("generation", "extraction") if source == "bound_folds" else ("generation", "extraction", "online_verify_filter")):
                    model_result[target][f"mean_{stage}_seconds"] = float(np.mean([block[fold]["timing_seconds"][stage]["mean"] for fold in "ABCD"]))
                if source == "bound_folds" and token_rows:
                    model_result[target]["mean_output_tokens_reencoded"] = float(np.mean([block[fold]["mean_output_tokens_reencoded"] for fold in "ABCD"]))
                    model_result[target]["mean_delta_output_tokens_vs_base"] = float(np.mean([block[fold]["mean_delta_output_tokens_vs_base"] for fold in "ABCD"]))
                if source == "bound_online_verifier_folds":
                    model_result[target]["filter"] = {field: float(np.mean([block[fold]["filter"][field] for fold in "ABCD"]))
                                                       for field in block["A"]["filter"]}
        report["models"][model] = model_result
    if all("bound_four_fold_mean" in item and "bound_online_verifier_four_fold_mean" in item for item in report["models"].values()):
        overview = {}
        for condition in ("base", "bound", "base_online_verifier", "bound_online_verifier"):
            rows = []
            for item in report["models"].values():
                if condition == "base":
                    source = item["base"]
                    row = {**source["quality"], "mean_delivery_seconds": source["timing_seconds"]["total_delivery"]["mean"],
                           "mean_generation_seconds": source["timing_seconds"]["generation"]["mean"],
                           "mean_extraction_seconds": source["timing_seconds"]["extraction"]["mean"],
                           "mean_output_tokens_reencoded": source["mean_output_tokens_reencoded"]}
                elif condition == "bound":
                    source = item["bound_four_fold_mean"]
                    row = {**source["quality"], **{key: value for key, value in source.items() if key != "quality"}}
                elif condition == "base_online_verifier":
                    source = item["base_online_verifier"]
                    row = {**source["final_quality"], "mean_delivery_seconds": source["timing_seconds"]["total_delivery"]["mean"],
                           "mean_generation_seconds": source["timing_seconds"]["generation"]["mean"],
                           "mean_extraction_seconds": source["timing_seconds"]["extraction"]["mean"],
                           "mean_online_verify_filter_seconds": source["timing_seconds"]["online_verify_filter"]["mean"],
                           "mean_output_tokens_reencoded": item["base"]["mean_output_tokens_reencoded"],
                           "filtered_invalid_current_per_answer": source["filter"]["filtered_invalid_current"],
                           "filtered_unknown_online_per_answer": source["filter"]["filtered_unknown_online"]}
                else:
                    source = item["bound_online_verifier_four_fold_mean"]
                    row = {**source["quality"], **{key: value for key, value in source.items() if key not in ("quality", "filter")},
                           "filtered_invalid_current_per_answer": source["filter"]["filtered_invalid_current"],
                           "filtered_unknown_online_per_answer": source["filter"]["filtered_unknown_online"]}
                    if "mean_output_tokens_reencoded" in item["bound_four_fold_mean"]:
                        row["mean_output_tokens_reencoded"] = item["bound_four_fold_mean"]["mean_output_tokens_reencoded"]
                rows.append(row)
            fields = ("sample_hr", "package_hr", "valid_rate", "empty_rate", "mean_delivery_seconds",
                      "mean_generation_seconds", "mean_extraction_seconds", "mean_output_tokens_reencoded")
            if condition.endswith("verifier"):
                fields += ("mean_online_verify_filter_seconds", "filtered_invalid_current_per_answer", "filtered_unknown_online_per_answer")
            overview[condition] = {field: float(np.mean([row[field] for row in rows])) for field in fields if all(field in row for row in rows)}
            overview[condition]["extra_verifier_llm_tokens_per_answer"] = 0 if condition.endswith("verifier") else None
        report["three_model_equal_mean"] = overview
    output = RESULTS / ("filter_comparison_interim.json" if args.allow_partial else "filter_comparison_summary.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "verified_records": len(all_bound_verified),
                      "folds": {model: list(item["bound_online_verifier_folds"]) for model, item in report["models"].items()}}))


if __name__ == "__main__":
    main()
