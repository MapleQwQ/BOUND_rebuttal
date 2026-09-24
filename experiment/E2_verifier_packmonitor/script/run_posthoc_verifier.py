#!/usr/bin/env python3
"""Run the E2 small-scale post-hoc verifier on frozen existing generations.

This script deliberately does not query PyPI.  It reuses the package-level
model-cutoff labels already stored with the original evaluation outputs, so
the run is deterministic and does not confuse transient registry failures
with non-existent packages.  It is a post-hoc filtering baseline, not a
PackMonitor or a verifier-guided repair implementation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


MODELS = {
    "deepseekcoder": "2023-11-02",
    "qwen3-release": "2025-04-29",
    "llama3.1-release": "2024-07-23",
}
FOLDS = ("A", "B", "C", "D")


def json_load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sample(rows: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    def rank(row: dict[str, Any]) -> tuple[str, str]:
        prompt_id = str(row["id"])
        key = hashlib.sha256(f"{seed}:{prompt_id}".encode()).hexdigest()
        return key, prompt_id

    return sorted(rows, key=rank)[: min(n, len(rows))]


def unique(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def metric_row(model: str, fold: str, method: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(records)
    # Match the original metric denominator: standard-library names are not
    # third-party package candidates and therefore do not enter Package-HR.
    total_packages = sum(len(row["initial_valid"]) + len(row["initial_hallucinated"]) for row in records)
    total_hallucinated = sum(len(row["initial_hallucinated"]) for row in records)
    total_retained = sum(len(row["initial_valid"]) for row in records)
    return {
        "model": model,
        "fold": fold,
        "method": method,
        "n_prompts": len({str(row["prompt_id"]) for row in records}),
        "n_generations": n,
        "initial_sample_hr": sum(bool(row["initial_hallucinated"]) for row in records) / n,
        "initial_package_hr": total_hallucinated / total_packages if total_packages else 0.0,
        "postfilter_sample_hr": 0.0,
        "postfilter_package_hr": 0.0,
        "initial_avg_packages": total_packages / n,
        "verified_valid_retained_per_answer": total_retained / n,
        "invalid_removed_per_answer": total_hallucinated / n,
        "stdlib_passthrough_per_answer": sum(len(row["stdlib_passthrough"]) for row in records) / n,
        "postfilter_empty_rate": sum(not row["filtered_packages"] for row in records) / n,
        "answers_changed_rate": sum(bool(row["initial_hallucinated"]) for row in records) / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260923)
    args = parser.parse_args()
    if args.sample_size < 1 or args.sample_size > 100:
        raise SystemExit("E2 small-scale run requires 1 <= --sample-size <= 100")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_records: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "experiment": "E2 post-hoc verifier small-scale",
        "sampling": "stable SHA-256 ranking of prompt_id after fixing seed",
        "seed": args.seed,
        "requested_prompts_per_model": args.sample_size,
        "models": {},
        "label_scope": "cached model-cutoff validity from original evaluation",
        "not_implemented_here": ["deployment-snapshot relabeling", "one-shot repair", "PackMonitor"],
    }
    package_labels: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for model, cutoff in MODELS.items():
        fold_payloads: dict[str, dict[str, Any]] = {}
        source_files: dict[str, Any] = {}
        for fold in FOLDS:
            path = args.source_root / model / f"fold_{fold}" / "blast_50" / "eval_unseen_prompts.json"
            payload = json_load(path)
            fold_payloads[fold] = payload
            source_files[fold] = {"path": str(path), "sha256": sha256_file(path)}

        reference_rows = fold_payloads["A"]["details"]
        selected_rows = stable_sample(reference_rows, args.sample_size, args.seed)
        selected_ids = [str(row["id"]) for row in selected_rows]
        selected_set = set(selected_ids)
        manifest["models"][model] = {
            "model_cutoff": cutoff,
            "eligible_prompts": len(reference_rows),
            "selected_prompt_ids": selected_ids,
            "source_files": source_files,
        }

        baseline_reference: dict[str, Any] = {}
        for fold in FOLDS:
            rows = {str(row["id"]): row for row in fold_payloads[fold]["details"]}
            if not selected_set.issubset(rows):
                raise AssertionError(f"{model}/{fold}: selected prompts are not all present")
            for prompt_id in selected_ids:
                row = rows[prompt_id]
                baseline_trials = row["baseline"]["trials"]
                baseline_signature = [
                    (trial.get("answer"), unique(trial.get("packages", [])), unique(trial.get("valid", [])), unique(trial.get("hallucinated", [])))
                    for trial in baseline_trials
                ]
                if fold == "A":
                    baseline_reference[prompt_id] = baseline_signature
                elif baseline_signature != baseline_reference[prompt_id]:
                    raise AssertionError(f"{model}/{prompt_id}: Base differs across folds")

                conditions = []
                if fold == "A":
                    conditions.append(("base", "base", baseline_trials))
                conditions.append(("bound", f"bound_fold_{fold}", row["edited"]["trials"]))
                for condition, method, trials in conditions:
                    for trial_index, trial in enumerate(trials):
                        packages = unique(trial.get("packages", []))
                        valid = unique(trial.get("valid", []))
                        hallucinated = unique(trial.get("hallucinated", []))
                        overlap = set(valid) & set(hallucinated)
                        if overlap:
                            raise AssertionError(f"overlapping validity labels: {sorted(overlap)}")
                        # The historical classifier intentionally omits Python
                        # standard-library modules from both label lists.  The
                        # residue is preserved as an auditable passthrough; it
                        # is not silently counted as registry-valid.
                        stdlib_passthrough = sorted(set(packages) - set(valid) - set(hallucinated))
                        for package in valid:
                            package_labels[model][package].add("valid")
                        for package in hallucinated:
                            package_labels[model][package].add("hallucinated")
                        all_records.append(
                            {
                                "model": model,
                                "model_cutoff": cutoff,
                                "fold": "none" if condition == "base" else fold,
                                "condition": condition,
                                "method": method,
                                "prompt_id": row["id"],
                                "question": row["question"],
                                "generation_index": trial.get("generation", trial_index),
                                "initial_answer": trial.get("answer", ""),
                                "initial_packages": packages,
                                "source_initial_valid": valid,
                                "source_initial_hallucinated": hallucinated,
                                "source_stdlib_passthrough": stdlib_passthrough,
                                # Replaced below using one internally consistent
                                # per-model/cutoff snapshot.
                                "initial_valid": valid,
                                "initial_hallucinated": hallucinated,
                                "stdlib_passthrough": stdlib_passthrough,
                                "filtered_packages": unique([*valid, *stdlib_passthrough]),
                                "filter_terminal_state": (
                                    "all_candidates_removed"
                                    if not valid and not stdlib_passthrough
                                    else "verified_or_stdlib_candidates_retained"
                                ),
                                "validity_source": "pending_snapshot_reconciliation",
                            }
                        )

    conflicts = {
        model: {package: sorted(statuses) for package, statuses in labels.items() if len(statuses) > 1}
        for model, labels in package_labels.items()
    }
    # A successful historical PyPI lookup is positive evidence that the name
    # existed by the same fixed cutoff.  A failed lookup may be a transient
    # network failure.  Therefore valid wins when the old online labels
    # conflict.  The conflicts remain fully visible in registry_snapshot.json.
    reconciled_labels = {
        model: {
            package: ("valid" if "valid" in statuses else "hallucinated")
            for package, statuses in labels.items()
        }
        for model, labels in package_labels.items()
    }
    for row in all_records:
        labels = reconciled_labels[row["model"]]
        row["initial_valid"] = sorted(pkg for pkg in row["initial_packages"] if labels.get(pkg) == "valid")
        row["initial_hallucinated"] = sorted(
            pkg for pkg in row["initial_packages"] if labels.get(pkg) == "hallucinated"
        )
        row["stdlib_passthrough"] = sorted(pkg for pkg in row["initial_packages"] if pkg not in labels)
        row["filtered_packages"] = unique([*row["initial_valid"], *row["stdlib_passthrough"]])
        row["filter_terminal_state"] = (
            "all_candidates_removed"
            if not row["filtered_packages"]
            else "verified_or_stdlib_candidates_retained"
        )
        row["validity_source"] = "reconciled_cached_model_cutoff_snapshot_valid_wins"

    output_jsonl = args.output_dir / "posthoc_filter_results.jsonl"
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for row in all_records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    metric_rows: list[dict[str, Any]] = []
    for model in MODELS:
        base = [row for row in all_records if row["model"] == model and row["condition"] == "base"]
        metric_rows.append(metric_row(model, "none", "base", base))
        for fold in FOLDS:
            bound = [
                row
                for row in all_records
                if row["model"] == model and row["condition"] == "bound" and row["fold"] == fold
            ]
            metric_rows.append(metric_row(model, fold, f"bound_fold_{fold}", bound))

    summary_csv = args.output_dir / "posthoc_filter_summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)

    registry_snapshot = {
        "snapshot_type": "labels extracted from frozen source evaluations",
        "warning": "This is not a live or deployment-date PyPI snapshot.",
        "model_cutoffs": MODELS,
        "reconciliation_policy": "valid-wins: a successful lookup is positive evidence; old failed lookups may be transient",
        "labels": {model: dict(sorted(labels.items())) for model, labels in reconciled_labels.items()},
        "conflicts_within_model_cutoff": conflicts,
    }
    (args.output_dir / "registry_snapshot.json").write_text(
        json.dumps(registry_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "summary.json").write_text(
        json.dumps(metric_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# E2 小规模 post-hoc verifier 结果",
        "",
        f"固定抽样：每个模型 {args.sample_size} 个 prompt，每个条件 5 次已有生成；Base 一份，BOUND 四折。",
        f"抽样 seed：`{args.seed}`。本次共处理 {len(all_records)} 条回答。",
        "",
        "本阶段只验证 post-hoc filtering。包标签来自原评估中按各模型 cutoff 冻结的缓存标签；未重新查询 PyPI。",
        "它不是 PackMonitor、不是 one-shot repair，也不提供任务充分性结论。",
        "",
        "| 模型 | 条件 | 初始 Sample-HR | 初始 Package-HR | 过滤后空回答率 | 每回答保留真实包 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in metric_rows:
        lines.append(
            f"| {row['model']} | {row['method']} | {row['initial_sample_hr']:.3f} | "
            f"{row['initial_package_hr']:.3f} | {row['postfilter_empty_rate']:.3f} | "
            f"{row['verified_valid_retained_per_answer']:.3f} |"
        )
    lines += [
        "",
        "所有条件的过滤后 Sample-HR 与 Package-HR 按构造均为 0；这只说明无效候选被删除，不能解释为回答充分或任务成功。",
        "后续仍需补充 deployment-date snapshot、one-shot repair 和 PackMonitor 兼容性试运行。",
        "",
    ]
    (args.output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"records": len(all_records), "metric_rows": len(metric_rows), "output": str(args.output_dir)}))


if __name__ == "__main__":
    main()
