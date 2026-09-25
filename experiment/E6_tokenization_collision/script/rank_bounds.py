#!/usr/bin/env python3
"""Exact Spearman bounds from legacy top-200 and a complete new ranking.

The unreported legacy modules occupy ranks 201..N in unknown order. Spearman's
denominator is constant over their permutations, so rearrangement gives exact
minimum/maximum by reversing/aligning their order with the new ranking.
"""
from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

from scipy.stats import rankdata, spearmanr

E6 = Path(__file__).resolve().parent.parent
RESULTS = E6 / "results"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def bounds(old: list[dict], new: list[dict]) -> tuple[float, float]:
    old_names = [x["module"] for x in old]
    new_names = [x["module"] for x in new]
    if len(old_names) != len(set(old_names)) or len(new_names) != len(set(new_names)):
        raise ValueError("duplicate module name")
    if not set(old_names).issubset(new_names):
        raise ValueError("legacy top modules missing from new ranking")
    if len({x["score"] for x in old}) != len(old) or len({x["score"] for x in new}) != len(new):
        raise ValueError("tied scores need a separate tie-aware bound")
    new_rank = dict(zip(new_names, rankdata([-x["score"] for x in new])))
    fixed = {name: i + 1 for i, name in enumerate(old_names)}
    missing = sorted((name for name in new_names if name not in fixed), key=new_rank.get)

    def rho(tail):
        candidate = fixed | {name: len(old) + i + 1 for i, name in enumerate(tail)}
        return float(spearmanr([candidate[name] for name in new_names],
                               [new_rank[name] for name in new_names]).statistic)

    return rho(missing[::-1]), rho(missing)


def self_test():
    # Exhaust all 4! possible hidden tails to check the rearrangement bound.
    old = [{"module": f"m{i}", "score": 9-i} for i in range(3)]
    new = [{"module": name, "score": 10-i} for i, name in enumerate(("m0", "m1", "m2", "m5", "m3", "m6", "m4"))]
    low, high = bounds(old, new)
    names = [r["module"] for r in new]
    rank = {name: i + 1 for i, name in enumerate(names)}
    values = []
    for tail in itertools.permutations(("m3", "m4", "m5", "m6")):
        old_rank = {"m0": 1, "m1": 2, "m2": 3} | {name: i+4 for i, name in enumerate(tail)}
        values.append(float(spearmanr([old_rank[n] for n in names], [rank[n] for n in names]).statistic))
    assert abs(low - min(values)) < 1e-12 and abs(high - max(values)) < 1e-12


def main():
    self_test()
    rows = []
    for model in MODELS:
        for fold in "ABCD":
            folder = RESULTS / model / f"fold_{fold}"
            old = json.loads((folder / "first_token/localization_report.json").read_text())["layer_scores"]
            new = json.loads((folder / "full_sequence/localization_report.json").read_text())["layer_scores"]
            low, high = bounds(old, new)
            rows.append({"model": model, "fold": fold, "legacy_reported_modules": len(old),
                         "all_modules": len(new), "legacy_unreported_modules": len(new)-len(old),
                         "full_rank_spearman_lower_bound": low,
                         "full_rank_spearman_upper_bound": high})
    out = RESULTS / "full_rank_spearman_bounds.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"verified exact permutation bounds for {len(rows)} folds -> {out}")


if __name__ == "__main__":
    main()
