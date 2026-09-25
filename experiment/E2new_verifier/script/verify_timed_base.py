#!/usr/bin/env python3
"""Online PyPI verifier for freshly timed Base generations.

Can follow a GPU producer's append-only JSONL and resume from unique keys.
Each answer's end-to-end latency is its own generation time plus verification.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import requests

from run_existing_generations import MODELS, RESULTS, query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    source = RESULTS / f"base_timed_{args.model}.jsonl"
    output = RESULTS / f"base_timed_verified_{args.model}.jsonl"
    expected = MODELS[args.model] * 5
    completed = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if line:
                record = json.loads(line)
                key = str(record["prompt_id"]), record["generation"]
                if key in completed:
                    raise ValueError(f"duplicate verified record: {key}")
                completed.add(key)
    if len(completed) == expected:
        print(f"already complete: {args.model} {expected}", flush=True)
        return
    if not source.exists() and not args.follow:
        raise SystemExit(f"missing Base source: {source}")
    while not source.exists():
        time.sleep(1)
    session = requests.Session()
    session.headers.update({"User-Agent": "BOUND-E2new-online-verifier/1.0 (research evaluation)"})
    added = 0
    seen_source = set()
    with source.open(encoding="utf-8") as upstream, output.open("a", encoding="utf-8") as downstream:
        while len(completed) + added < expected:
            offset = upstream.tell()
            line = upstream.readline()
            if not line:
                if not args.follow:
                    break
                time.sleep(0.5)
                continue
            if not line.endswith("\n"):
                upstream.seek(offset)
                time.sleep(0.2)
                continue
            fresh = json.loads(line)
            key = str(fresh["prompt_id"]), fresh["generation"]
            if key in seen_source:
                raise ValueError(f"duplicate Base generation: {key}")
            seen_source.add(key)
            if key in completed:
                continue
            if fresh["model"] != args.model:
                raise ValueError(f"source model mismatch: {fresh['model']}")
            if fresh.get("base_generation_seconds") is None:
                raise ValueError(f"missing measured T_Base: {key}")
            verify_start = time.perf_counter()
            names = sorted({str(p).strip() for p in fresh.get("packages", []) if str(p).strip()})
            parse_seconds = time.perf_counter() - verify_start
            checks = [query(session, name, 0.0) for name in names]
            retained = [item["name"] for item in checks if item["status"] in ("exists", "stdlib")]
            verify_seconds = time.perf_counter() - verify_start
            record = {"model": args.model, "prompt_id": fresh["prompt_id"],
                      "generation": fresh["generation"], "seed": fresh["seed"],
                      "answer": fresh["answer"], "source_packages": names,
                      "checks": checks, "retained_packages": retained,
                      "base_generation_seconds": fresh["base_generation_seconds"],
                      "verify_total_seconds": verify_seconds,
                      "bov_total_seconds": fresh["base_generation_seconds"] + verify_seconds,
                      "input_tokens": fresh["input_tokens"],
                      "output_tokens_reencoded": fresh["output_tokens_reencoded"],
                      "verified_utc": datetime.now(timezone.utc).isoformat(),
                      "timing_scope": "T_Base measured on GPU + subsequent per-answer verifier elapsed"}
            downstream.write(json.dumps(record, ensure_ascii=False) + "\n")
            downstream.flush()
            added += 1
            if added % 50 == 0:
                print(f"{datetime.now(timezone.utc).isoformat()} {args.model} new={added} total={len(completed)+added}/{expected}", flush=True)
    if len(completed) + added != expected:
        raise SystemExit(f"incomplete verified output: {args.model} {len(completed)+added}/{expected}")
    print(f"completed {args.model}: {expected}/{expected}", flush=True)


if __name__ == "__main__":
    main()
