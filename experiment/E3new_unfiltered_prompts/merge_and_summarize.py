#!/usr/bin/env python3
"""Merge historic Base and new/reused BOUND trials in replication-package format."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from getHallucinationPackage.build_edit_examples import (  # noqa: E402
    check_std_package,
    classify_packages_by_pypi,
    clean_extracted_package_name,
    normalize,
)


BASE_FILES = {
    "deepseekcoder": "getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl",
    "qwen3": "getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl",
    "llama31": "getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def release_cache_from_file(path: Path) -> tuple[dict, dict]:
    cache = {}
    statuses = {}
    for row in read_jsonl(path):
        name = str(row["name"])
        raw_date = row.get("first_upload_utc")
        cache[name] = dt.datetime.fromisoformat(raw_date.replace("Z", "+00:00")).replace(tzinfo=None) if raw_date else None
        statuses[name] = row.get("status", "unknown")
    return cache, statuses


def relabel(trials: list[dict], cutoff: dt.datetime, release_cache: dict, statuses: dict, audit: dict) -> list[dict]:
    output = []
    for source in trials:
        trial = dict(source)
        for raw in trial.get("packages", []):
            name = clean_extracted_package_name(normalize(raw, "Python"))
            if name and not check_std_package(name):
                if name not in release_cache:
                    raise ValueError(f"missing release date lookup for {name}")
                if statuses[name] == "query_unknown":
                    audit["query_unknown_candidate_mentions"] += 1
        valid, hall = classify_packages_by_pypi(trial.get("packages", []), language="Python", cutoff=cutoff, release_cache=release_cache)
        if sorted(trial.get("valid", [])) != valid or sorted(trial.get("hallucinated", [])) != hall:
            audit["provisional_label_changed_responses"] += 1
        trial["valid"] = valid
        trial["hallucinated"] = hall
        output.append(trial)
    return output


def summarize_trials(trials: list[dict]) -> dict:
    """Match replication package's per-prompt summary exactly."""
    valid = sum(len(row.get("valid", []) or []) for row in trials)
    hall = sum(len(row.get("hallucinated", []) or []) for row in trials)
    n = len(trials)
    return {
        "n_trials": n,
        "total_valid": valid,
        "total_hallucinated": hall,
        "package_hallucination_rate": hall / max(valid + hall, 1),
        "sample_hallucination_rate": sum(bool(row.get("hallucinated")) for row in trials) / max(n, 1),
        "sample_valid_rate": sum(bool(row.get("valid")) for row in trials) / max(n, 1),
        "avg_packages_per_trial": (valid + hall) / max(n, 1),
        "avg_valid_per_trial": valid / max(n, 1),
        "avg_hallucinated_per_trial": hall / max(n, 1),
    }


def paper_summary(details: list[dict]) -> dict:
    """Match replication package summarize_eval_pairs: average prompt-level rates."""
    def avg(side: str, key: str) -> float:
        return sum(row[side]["summary"][key] for row in details) / len(details)

    return {
        "n_prompts": len(details),
        "baseline_sample_hallucination_rate": avg("baseline", "sample_hallucination_rate"),
        "edited_sample_hallucination_rate": avg("edited", "sample_hallucination_rate"),
        "baseline_package_hallucination_rate": avg("baseline", "package_hallucination_rate"),
        "edited_package_hallucination_rate": avg("edited", "package_hallucination_rate"),
        "baseline_sample_valid_rate": avg("baseline", "sample_valid_rate"),
        "edited_sample_valid_rate": avg("edited", "sample_valid_rate"),
    }


def pooled(details: list[dict]) -> dict:
    base = [trial for row in details for trial in row["baseline"]["trials"]]
    bound = [trial for row in details for trial in row["edited"]["trials"]]

    def one(trials: list[dict]) -> dict:
        n = len(trials)
        hall = sum(bool(trial.get("hallucinated")) for trial in trials)
        valid = sum(bool(trial.get("valid")) for trial in trials)
        hall_mentions = sum(len(trial.get("hallucinated", []) or []) for trial in trials)
        valid_mentions = sum(len(trial.get("valid", []) or []) for trial in trials)
        no_packages = sum(not trial.get("packages") for trial in trials)
        return {
            "n_generations": n,
            "sample_hr": hall / n,
            "package_hr": hall_mentions / max(hall_mentions + valid_mentions, 1),
            "valid_rate": valid / n,
            "no_extracted_package_rate": no_packages / n,
            "hallucination_responses_per_1000": 1000 * hall / n,
            "hallucinated_package_mentions_per_1000": 1000 * hall_mentions / n,
            "avg_packages": sum(len(trial.get("packages", []) or []) for trial in trials) / n,
        }

    return {"base": one(base), "bound": one(bound)}


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = quantile * (len(ordered) - 1)
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def expected_seed(prompt_id: int, generation: int) -> int:
    return int.from_bytes(hashlib.sha256(f"20260926|{prompt_id}|{generation}".encode()).digest()[:4], "big")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--reused-old-e3", action="store_true", help="Only set when protocol-compatible old E3 rows were prefilled")
    parser.add_argument("--release-cache", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_jsonl(args.manifest)
    if len(manifest) != 1000 or len({int(row["id"]) for row in manifest}) != 1000:
        raise ValueError("manifest must have exactly 1000 unique prompts")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    release_cache, statuses = release_cache_from_file(args.release_cache)
    cutoff_by_model = {"deepseekcoder": dt.datetime(2024, 1, 1), "qwen3": dt.datetime(2025, 4, 29), "llama31": dt.datetime(2024, 7, 23)}
    label_audit = {"query_unknown_candidate_mentions": 0, "provisional_label_changed_responses": 0}
    old_ids = {int(row["id"]) for row in read_jsonl(args.repo / "BOUND_rebuttal/experiment/E3_unfiltered_shared_prompts/results/shared_prompt_manifest_confirmatory200.jsonl")} if args.reused_old_e3 else set()
    rows_by_model_fold: dict[tuple[str, str], list[dict]] = {}
    summary_rows = []

    for model, base_path in BASE_FILES.items():
        baseline = defaultdict(list)
        wanted = {int(row["id"]) for row in manifest}
        for trial in read_jsonl(args.repo / base_path):
            prompt_id = int(trial["id"])
            if prompt_id in wanted:
                baseline[prompt_id].append(trial)
        for fold in "ABCD":
            path = args.raw_dir / f"{model}_fold{fold}.details.jsonl"
            edited = {int(row["id"]): row for row in read_jsonl(path)}
            if len(edited) != len(manifest) or set(edited) != wanted:
                raise ValueError(f"missing or duplicate prompts: {path}, got {len(edited)}")
            details = []
            for source in manifest:
                prompt_id = int(source["id"])
                question = source["question"]
                base_trials = sorted(baseline[prompt_id], key=lambda row: int(row["generation"]))
                if len(base_trials) != 5 or [int(row["generation"]) for row in base_trials] != list(range(5)) or any(row["question"] != question for row in base_trials):
                    raise ValueError(f"historical Base mismatch: {model}/{prompt_id}")
                generation_row = edited[prompt_id]
                edit_trials = sorted(generation_row["edited"]["trials"], key=lambda row: int(row["generation"]))
                if generation_row["question"] != question or len(edit_trials) != 5 or [int(row["generation"]) for row in edit_trials] != list(range(5)):
                    raise ValueError(f"BOUND mismatch: {model}/{fold}/{prompt_id}")
                if any(trial.get("seed") != expected_seed(prompt_id, gen) for gen, trial in enumerate(edit_trials)):
                    raise ValueError(f"BOUND seed mismatch: {model}/{fold}/{prompt_id}")
                edit_trials = relabel(edit_trials, cutoff_by_model[model], release_cache, statuses, label_audit)
                details.append({
                    "id": prompt_id,
                    "question": question,
                    "baseline": {"summary": summarize_trials(base_trials), "trials": base_trials},
                    "edited": {"summary": summarize_trials(edit_trials), "trials": edit_trials},
                    "source": {"baseline": "original_screening", "edited": "reused_old_E3" if prompt_id in old_ids else "new_E3", "risk": source[f"{model}_risk"]},
                })
            summary = paper_summary(details)
            target = args.output_dir / model / f"fold_{fold}" / "BOUND"
            target.mkdir(parents=True, exist_ok=True)
            (target / "eval_unfiltered_prompts.json").write_text(json.dumps({"summary": summary, "details": details}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            rows_by_model_fold[(model, fold)] = details
            extra = pooled(details)
            (target / "additional_metrics.json").write_text(json.dumps(extra, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            summary_rows.append({"model": model, "fold": fold, **summary, "base_no_package": extra["base"]["no_extracted_package_rate"], "bound_no_package": extra["bound"]["no_extracted_package_rate"]})

    with (args.output_dir / "paper_style_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    # Preserve prompt-level pairing; Base is shared across folds, never copied as independent evidence.
    rng = random.Random(20260924)
    model_results = {}
    all_prompt_deltas = {}
    base_relabel_sensitivity = {}
    for model in BASE_FILES:
        folds = [rows_by_model_fold[(model, fold)] for fold in "ABCD"]
        base_summary = paper_summary(folds[0])
        fold_summaries = [paper_summary(rows) for rows in folds]
        metric_names = ("sample_hallucination_rate", "package_hallucination_rate", "sample_valid_rate")
        macro_metrics = {}
        for name in metric_names:
            base_value = base_summary[f"baseline_{name}"]
            bound_value = sum(item[f"edited_{name}"] for item in fold_summaries) / 4
            macro_metrics[name] = {"base": base_value, "bound_four_fold_macro": bound_value, "difference": bound_value - base_value}
        base = macro_metrics["sample_hallucination_rate"]["base"]
        bound = macro_metrics["sample_hallucination_rate"]["bound_four_fold_macro"]
        prompt_deltas = [sum(folds[j][i]["edited"]["summary"]["sample_hallucination_rate"] for j in range(4)) / 4 - folds[0][i]["baseline"]["summary"]["sample_hallucination_rate"] for i in range(1000)]
        all_prompt_deltas[model] = prompt_deltas
        bootstrap = [sum(prompt_deltas[rng.randrange(1000)] for _ in range(1000)) / 1000 for _ in range(args.bootstrap)]
        by_risk = {}
        for risk_name in ("clean", "low", "high"):
            indices = [i for i, row in enumerate(manifest) if row[f"{model}_risk"] == risk_name]
            by_risk[risk_name] = {
                "n_prompts": len(indices),
                "base_sample_hr": sum(folds[0][i]["baseline"]["summary"]["sample_hallucination_rate"] for i in indices) / len(indices),
                "bound_four_fold_macro_sample_hr": sum(sum(folds[j][i]["edited"]["summary"]["sample_hallucination_rate"] for j in range(4)) / 4 for i in indices) / len(indices),
            }
        for item in by_risk.values():
            item["difference"] = item["bound_four_fold_macro_sample_hr"] - item["base_sample_hr"]
        model_results[model] = {"metrics": macro_metrics, "delta_sample_hr_ci95": [percentile(bootstrap, 0.025), percentile(bootstrap, 0.975)], "by_historical_risk": by_risk, "reused_old_e3_prompts": sum(int(row["id"]) in old_ids for row in manifest)}
        sensitivity_audit = {"query_unknown_candidate_mentions": 0, "provisional_label_changed_responses": 0}
        relabeled_summaries = [summarize_trials(relabel(row["baseline"]["trials"], cutoff_by_model[model], release_cache, statuses, sensitivity_audit)) for row in folds[0]]
        base_relabel_sensitivity[model] = {
            "original_sample_hr": base_summary["baseline_sample_hallucination_rate"],
            "relabeled_sample_hr": sum(item["sample_hallucination_rate"] for item in relabeled_summaries) / 1000,
            "original_package_hr": base_summary["baseline_package_hallucination_rate"],
            "relabeled_package_hr": sum(item["package_hallucination_rate"] for item in relabeled_summaries) / 1000,
            "original_valid_rate": base_summary["baseline_sample_valid_rate"],
            "relabeled_valid_rate": sum(item["sample_valid_rate"] for item in relabeled_summaries) / 1000,
            "changed_responses": sensitivity_audit["provisional_label_changed_responses"],
            "query_unknown_candidate_mentions": sensitivity_audit["query_unknown_candidate_mentions"],
        }
    metric_names = ("sample_hallucination_rate", "package_hallucination_rate", "sample_valid_rate")
    overall = {
        name: {
            key: sum(model_results[model]["metrics"][name][key] for model in BASE_FILES) / 3
            for key in ("base", "bound_four_fold_macro", "difference")
        }
        for name in metric_names
    }
    rng_macro = random.Random(20260925)
    macro_prompt_deltas = [sum(all_prompt_deltas[model][i] for model in BASE_FILES) / 3 for i in range(1000)]
    boot_macro = [sum(macro_prompt_deltas[rng_macro.randrange(1000)] for _ in range(1000)) / 1000 for _ in range(args.bootstrap)]
    payload = {"models": model_results, "three_model_equal_weight_macro": overall, "three_model_macro_delta_sample_hr_ci95": [percentile(boot_macro, 0.025), percentile(boot_macro, 0.975)], "aggregation": "replication package: first mean of per-prompt rates, then four-fold mean, then equal-weight model mean"}
    (args.output_dir / "four_fold_macro.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "relabel_audit.json").write_text(json.dumps(label_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "baseline_relabel_sensitivity.json").write_text(json.dumps(base_relabel_sensitivity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
