#!/usr/bin/env python3
"""Interim Base/BOUND current-registry results from reused answers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from run_existing_generations import FOLDS, MODELS, RESULTS, load, normalize, trials


def measure(rows: list[dict], index: set[str]) -> dict:
    sample_h = pkg_h = pkg_total = valid_hits = empty = 0
    for trial in rows:
        names = {str(p).strip() for p in trial.get("packages", []) if str(p).strip()}
        third = {p for p in names if p not in sys.stdlib_module_names}
        h = sum(normalize(p) not in index for p in third)
        v = len(third) - h
        sample_h += h > 0
        pkg_h += h
        pkg_total += len(third)
        valid_hits += v > 0
        empty += not names
    n = len(rows)
    return {"n": n, "sample_hr": sample_h / n,
            "package_hr": pkg_h / pkg_total if pkg_total else 0,
            "valid_rate": valid_hits / n, "empty_rate": empty / n,
            "hallucinated_packages": pkg_h, "total_packages": pkg_total}


def main() -> None:
    index = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    report = {"index_metadata": json.loads((RESULTS / "pypi_index_metadata.json").read_text(encoding="utf-8")),
              "status": "interim raw Base/BOUND current-existence; online BOV and cutoff not complete",
              "models": {}}
    for model, n_prompts in MODELS.items():
        _, first = load(model, "A")
        base = [trial for row in first["details"] for trial in trials(row, "baseline")]
        rows = {"base": measure(base, index)}
        for fold in FOLDS:
            _, data = load(model, fold)
            edited = [trial for row in data["details"] for trial in trials(row, "edited")]
            rows[f"bound_{fold}"] = measure(edited, index)
        rows["bound_macro"] = {field: sum(rows[f"bound_{fold}"][field] for fold in FOLDS) / 4
                               for field in ("sample_hr", "package_hr", "valid_rate", "empty_rate")}
        report["models"][model] = rows
    (RESULTS / "raw_current_interim.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for model, rows in report["models"].items():
        print(model, "Base", rows["base"], "BOUND fourfold", rows["bound_macro"])


if __name__ == "__main__":
    main()
