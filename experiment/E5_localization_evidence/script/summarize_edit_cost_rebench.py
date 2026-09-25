"""Validate and summarize all 24 same-GPU cost benchmark cells."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
SOURCE = E5 / "results/01_all_module_lora/cost_rebench"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
CONDITIONS = ("BOUND", "wo_localization_all_lora")


def main() -> None:
    rows = []
    for model in MODELS:
        for fold in "ABCD":
            pair = {}
            for condition in CONDITIONS:
                folder = SOURCE / model / f"fold_{fold}" / condition
                data = json.loads((folder / "cost_metadata.json").read_text(encoding="utf-8"))
                if data["status"] != "complete" or data["model"] != model or data["fold"] != fold:
                    raise ValueError(f"Incomplete or mislabeled benchmark: {folder}")
                pair[condition] = data
                rows.append(data)
            bound, all_module = (pair[condition] for condition in CONDITIONS)
            if bound["edit_cases_sha256"] != all_module["edit_cases_sha256"]:
                raise ValueError(f"Edit case mismatch: {model}/{fold}")
            if bound["source_yaml_sha256"] != all_module["source_yaml_sha256"]:
                raise ValueError(f"Source config mismatch: {model}/{fold}")
            historical = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / model / f"fold_{fold}/blast_50/blast_config.json"
            original = json.loads(historical.read_text(encoding="utf-8"))
            if set(bound["resolved_target_modules"].split(",")) != set(original["resolved_target_modules"].split(",")):
                raise ValueError(f"BOUND module mismatch: {model}/{fold}")
    with (SOURCE / "per_fold.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [key for key in rows[0] if key != "resolved_target_modules"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    for model in MODELS:
        summary[model] = {}
        for condition in CONDITIONS:
            chosen = [row for row in rows if row["model"] == model and row["condition"] == condition]
            summary[model][condition] = {
                key: float(np.mean([row[key] for row in chosen]))
                for key in ("localization_seconds", "edit_seconds", "total_seconds",
                            "peak_localization_reserved_mib", "peak_edit_reserved_mib",
                            "n_edited_modules", "adapter_bytes")
            }
        a = summary[model]["BOUND"]
        b = summary[model]["wo_localization_all_lora"]
        summary[model]["all_minus_bound"] = {
            "edit_seconds": b["edit_seconds"] - a["edit_seconds"],
            "total_seconds": b["total_seconds"] - a["total_seconds"],
            "peak_edit_reserved_mib": b["peak_edit_reserved_mib"] - a["peak_edit_reserved_mib"],
            "adapter_size_ratio": b["adapter_bytes"] / a["adapter_bytes"],
        }
    payload = {"status": "complete", "n_cells": len(rows), "models": summary,
               "time_definition": "wall clock per fresh process; total includes model loads and adapter serialization",
               "peak_definition": "torch.cuda.max_memory_reserved per stage"}
    (SOURCE / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
