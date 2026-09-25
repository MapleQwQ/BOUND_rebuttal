#!/usr/bin/env python3
"""Freeze an outcome-blind paired subset for clean verifier timing."""

import csv
import hashlib

from run_existing_generations import MODELS, RESULTS, load


def main() -> None:
    rows = []
    for model in MODELS:
        _, payload = load(model, "A")
        ids = [str(row["id"]) for row in payload["details"]]
        ranked = sorted(ids, key=lambda pid: (hashlib.sha256(f"E2new-timing-20260924:{model}:{pid}".encode()).hexdigest(), pid))
        for pid in ranked[:30]:
            trial_hash = hashlib.sha256(f"E2new-trial-20260924:{model}:{pid}".encode()).digest()
            rows.append({"model": model, "prompt_id": pid, "generation": int.from_bytes(trial_hash[:4], "big") % 5})
    path = RESULTS / "timing_subset_manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("model", "prompt_id", "generation"))
        writer.writeheader()
        writer.writerows(rows)
    print(f"frozen {len(rows)} model-prompt-trial records: {path}")


if __name__ == "__main__":
    main()
