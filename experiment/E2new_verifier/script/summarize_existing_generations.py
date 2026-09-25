#!/usr/bin/env python3
"""Summarize full E2new registry-existence outcomes at the prompt grain."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from run_existing_generations import FOLDS, MODELS, RESULTS, load, normalize, trials


def labels(packages: list[str], index: set[str]) -> tuple[int, int, int, int, int]:
    names = {str(p).strip() for p in packages if str(p).strip()}
    third = {p for p in names if p not in sys.stdlib_module_names}
    exists = sum(normalize(p) in index for p in third)
    absent = len(third) - exists
    return int(absent > 0), absent, len(third), int(exists > 0), int(not names)


def metric(rows: list[tuple[int, int, int, int, int]]) -> dict:
    n = len(rows)
    h_answers = sum(r[0] for r in rows)
    h_packages = sum(r[1] for r in rows)
    total_packages = sum(r[2] for r in rows)
    return {"n": n, "sample_hr": h_answers / n, "package_hr": h_packages / total_packages if total_packages else 0,
            "valid_rate": sum(r[3] for r in rows) / n, "empty_rate": sum(r[4] for r in rows) / n,
            "hallucinated_package_count": h_packages, "package_count": total_packages,
            "empty_count": sum(r[4] for r in rows)}


def paired_ci(base: np.ndarray, bound: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    # Entries are prompt means across five trials; bound additionally averages four folds.
    delta = bound - base
    rng = np.random.default_rng(20260924)
    sampled = rng.integers(0, len(delta), size=(n_boot, len(delta)))
    means = delta[sampled].mean(axis=1)
    return float(delta.mean()), *[float(x) for x in np.quantile(means, [0.025, 0.975])]


def main() -> None:
    index_path = RESULTS / "pypi_index_names.txt"
    if not index_path.exists():
        raise SystemExit("missing frozen PyPI index")
    index = set(index_path.read_text(encoding="utf-8").splitlines())
    expected = sum(MODELS.values()) * 5
    bpath = RESULTS / "online_verifier_answers.jsonl"
    bmap = {}
    with bpath.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            key = row["model"], str(row["prompt_id"]), row["generation"]
            if key in bmap:
                raise ValueError(f"duplicate BOV record {key}")
            bmap[key] = row
    if len(bmap) != expected:
        raise SystemExit(f"BOV incomplete: {len(bmap)}/{expected}; full summary requires all pairs")

    summaries = {}
    output_rows = []
    for model, n_prompts in MODELS.items():
        folds = {fold: {str(x["id"]): x for x in load(model, fold)[1]["details"]} for fold in FOLDS}
        ids = sorted(folds["A"])
        if len(ids) != n_prompts or any(set(folds[fold]) != set(ids) for fold in FOLDS):
            raise ValueError(f"fold mismatch {model}")
        by_method: dict[str, list] = defaultdict(list)
        prompt_flags: dict[str, list] = defaultdict(list)
        timing = []
        unknown_answer_count = 0
        false_removal = 0
        query_counts = Counter()
        for pid in ids:
            pflags: dict[str, list[int]] = defaultdict(list)
            row = folds["A"][pid]
            for trial in trials(row, "baseline"):
                key = model, pid, trial["generation"]
                bov = bmap[key]
                if sorted({str(x).strip() for x in trial["packages"] if str(x).strip()}) != bov["source_packages"]:
                    raise ValueError(f"Base package mismatch {key}")
                for method, packages in (("base", trial["packages"]), ("bov", bov["retained_packages"])):
                    result = labels(packages, index)
                    by_method[method].append(result)
                    pflags[method].append(result[0])
                timing.append(bov["verify_total_seconds"])
                checks = bov["checks"]
                unknown_answer_count += any(c["status"] == "unknown" for c in checks)
                false_removal += sum(c["status"] in ("absent", "unknown") and normalize(c["name"]) in index for c in checks)
                for check in checks:
                    query_counts[check["status"]] += 1
                    if isinstance(check["attempts"], list):
                        query_counts["http_attempts"] += len(check["attempts"])
            for fold in FOLDS:
                method = f"bound_{fold}"
                for trial in trials(folds[fold][pid], "edited"):
                    result = labels(trial["packages"], index)
                    by_method[method].append(result)
                    pflags[method].append(result[0])
            for method, flags in pflags.items():
                prompt_flags[method].append(sum(flags) / 5)
        rows = {method: metric(values) for method, values in by_method.items()}
        for method, value in rows.items():
            output_rows.append({"model": model, "condition": method, **value})
        bound = np.mean(np.array([prompt_flags[f"bound_{f}"] for f in FOLDS]), axis=0)
        base = np.array(prompt_flags["base"])
        bov = np.array(prompt_flags["bov"])
        rows["bound_macro"] = {field: float(np.mean([rows[f"bound_{f}"][field] for f in FOLDS]))
                               for field in ("sample_hr", "package_hr", "valid_rate", "empty_rate")}
        rows["bound_macro"]["n_per_fold"] = n_prompts * 5
        summaries[model] = {"conditions": rows,
                            "paired_sample_hr_diff_bound_minus_bov": paired_ci(bov, bound),
                            "paired_sample_hr_diff_bound_minus_base": paired_ci(base, bound),
                            "paired_sample_hr_diff_bov_minus_base": paired_ci(base, bov),
                            "verifier": {"mean_seconds": float(np.mean(timing)),
                                         "p50_seconds": float(np.quantile(timing, 0.5)),
                                         "p95_seconds": float(np.quantile(timing, 0.95)),
                                         "unknown_answer_count": unknown_answer_count,
                                         "snapshot_exists_but_verifier_removed_count": false_removal,
                                         "query_counts": dict(query_counts)}}
    metadata = json.loads((RESULTS / "pypi_index_metadata.json").read_text(encoding="utf-8"))
    report = {"scope": "full original high-risk held-out prompts, five trials, four BOUND folds",
              "registry_index": metadata,
              "timing_boundary": "verifier latency measured; original per-answer generation latency absent; BOV total unavailable",
              "models": summaries}
    (RESULTS / "current_existence_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (RESULTS / "current_existence_by_fold.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(json.dumps({m: {"n": x["conditions"]["base"]["n"],
                          "sample_hr": {k: round(x["conditions"][k]["sample_hr"], 4) for k in ("base", "bov", "bound_macro")},
                          "mean_verify_seconds": round(x["verifier"]["mean_seconds"], 3)}
                      for m, x in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
