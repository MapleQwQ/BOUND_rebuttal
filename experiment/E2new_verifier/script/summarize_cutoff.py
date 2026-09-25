#!/usr/bin/env python3
"""Re-label fresh timed Base/BOV and reused BOUND with replica cutoff dates."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime

from run_existing_generations import FOLDS, MODELS, RESULTS, load, normalize, trials

CUTOFF = {"deepseekcoder": "2023-10-29", "qwen3-release": "2025-04-29",
          "llama3.1-release": "2023-12-31"}


def main() -> None:
    dates = {}
    date_file = RESULTS / "package_first_release_jsonapi.jsonl"
    if not date_file.exists():
        raise SystemExit("release-date evidence missing")
    with date_file.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                record = json.loads(line)
                if record["name"] in dates:
                    raise ValueError(f"duplicate release date: {record['name']}")
                dates[record["name"]] = record
    index = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    names_expected = set()
    for model in MODELS:
        with (RESULTS / f"base_timed_{model}.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    trial = json.loads(line)
                    names_expected.update(normalize(str(p)) for p in trial.get("packages", [])
                                          if str(p).strip() and str(p) not in sys.stdlib_module_names)
        for fold in FOLDS:
            _, data = load(model, fold)
            for row in data["details"]:
                for trial in trials(row, "edited"):
                    names_expected.update(normalize(str(p)) for p in trial.get("packages", [])
                                          if str(p).strip() and str(p) not in sys.stdlib_module_names)
    missing = (names_expected & index) - set(dates)
    if missing:
        raise SystemExit(f"release-date audit incomplete: {len(missing)} names missing")

    bmap = {}
    base_map = {}
    for model in MODELS:
        for label, target in (("base_timed", base_map), ("base_timed_verified", bmap)):
            with (RESULTS / f"{label}_{model}.jsonl").open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        row = json.loads(line)
                        key = model, str(row["prompt_id"]), row["generation"]
                        if key in target:
                            raise ValueError(f"duplicate {label}: {key}")
                        target[key] = row
    expected = sum(MODELS.values()) * 5
    if len(bmap) != expected or len(base_map) != expected or set(bmap) != set(base_map):
        raise SystemExit("fresh Base/BOV output incomplete")

    def classify(packages: list[str], cutoff: datetime) -> tuple[int, int, int, int, int, int]:
        names = {str(p).strip() for p in packages if str(p).strip()}
        third = {p for p in names if p not in sys.stdlib_module_names}
        pre = post = absent = unknown = 0
        for name in third:
            key = normalize(name)
            if key not in index:
                absent += 1
                continue
            record = dates[key]
            if record["status"] != "dated":
                unknown += 1
                continue
            first = datetime.fromisoformat(record["first_upload_utc"].replace("Z", "+00:00")).replace(tzinfo=None)
            if first <= cutoff:
                pre += 1
            else:
                post += 1
        return pre, post, absent, unknown, len(third), int(not names)

    output = []
    for model, n_prompts in MODELS.items():
        cutoff = datetime.fromisoformat(CUTOFF[model])
        folds = {fold: load(model, fold)[1]["details"] for fold in FOLDS}
        counts = defaultdict(list)
        for row in folds["A"]:
            for generation in range(5):
                key = model, str(row["id"]), generation
                counts["base"].append(classify(base_map[key]["packages"], cutoff))
                counts["bov"].append(classify(bmap[key]["retained_packages"], cutoff))
        for fold in FOLDS:
            for row in folds[fold]:
                for trial in trials(row, "edited"):
                    counts[f"bound_{fold}"].append(classify(trial["packages"], cutoff))
        for condition, records in counts.items():
            if len(records) != n_prompts * 5:
                raise ValueError(f"count mismatch: {model} {condition}")
            h_answers = sum(post + absent > 0 for pre, post, absent, unk, total, empty in records)
            unknown_answers = sum(unk > 0 for pre, post, absent, unk, total, empty in records)
            n = len(records)
            pre = sum(r[0] for r in records)
            post = sum(r[1] for r in records)
            absent = sum(r[2] for r in records)
            unknown = sum(r[3] for r in records)
            total = sum(r[4] for r in records)
            output.append({"model": model, "cutoff": CUTOFF[model], "condition": condition,
                           "n": n, "sample_hr_lower": h_answers / n,
                           "sample_hr_upper": (h_answers + sum(r[3] > 0 and not (r[1] + r[2] > 0) for r in records)) / n,
                           "package_hr_lower": (post + absent) / total if total else 0,
                           "package_hr_upper": (post + absent + unknown) / total if total else 0,
                           "valid_rate_confirmed": sum(r[0] > 0 for r in records) / n,
                           "unknown_answer_rate": unknown_answers / n,
                           "pre_cutoff_count": pre, "post_cutoff_count": post,
                           "absent_count": absent, "unknown_count": unknown, "package_count": total,
                           "empty_count": sum(r[5] for r in records)})
    with (RESULTS / "cutoff_by_fold.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    (RESULTS / "cutoff_summary.json").write_text(json.dumps({"cutoffs": CUTOFF,
        "date_evidence": str(date_file), "rows": output}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in output:
        print(row["model"], row["condition"], "sample_hr_range",
              f"{row['sample_hr_lower']:.4f}-{row['sample_hr_upper']:.4f}",
              "unknown", row["unknown_count"])


if __name__ == "__main__":
    main()
