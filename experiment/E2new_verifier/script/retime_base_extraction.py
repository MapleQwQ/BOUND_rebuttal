#!/usr/bin/env python3
"""Replay deterministic package extraction on saved Base answers; no GPU/network."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from knowledgeEdit.package_edit_utils import split_recommendation_packages
from generate_base_timed import MODELS, RESULTS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    parser.add_argument("--repeats", type=int, default=11)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    source = RESULTS / f"base_timed_{args.model}.jsonl"
    output = RESULTS / f"base_extraction_timed_{args.model}.jsonl"
    if not source.exists():
        raise SystemExit(f"missing {source}")
    n = 0
    with source.open(encoding="utf-8") as upstream, output.open("w", encoding="utf-8") as downstream:
        for line in upstream:
            if not line.strip():
                continue
            row = json.loads(line)
            observations = []
            for _ in range(args.repeats):
                start = time.perf_counter_ns()
                packages = split_recommendation_packages(row["answer"], "Python")
                observations.append((time.perf_counter_ns() - start) / 1e9)
                if packages != row["packages"]:
                    raise ValueError(f"extraction mismatch: {args.model} {row['prompt_id']} {row['generation']}")
            downstream.write(json.dumps({"model": args.model, "prompt_id": row["prompt_id"],
                                         "generation": row["generation"],
                                         "extraction_seconds_median_replay": statistics.median(observations),
                                         "repeats": args.repeats}, ensure_ascii=False) + "\n")
            n += 1
    expected = MODELS[args.model][1] * 5
    if n != expected:
        raise ValueError(f"expected {expected} records, got {n}")
    print(f"complete {args.model}: {n} extraction replay records", flush=True)


if __name__ == "__main__":
    main()
