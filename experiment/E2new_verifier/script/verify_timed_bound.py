#!/usr/bin/env python3
"""Follow timed BOUND generations and verify each answer online against PyPI."""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

import requests

from generate_base_timed import MODELS, RESULTS
from run_existing_generations import query

THREAD_LOCAL = threading.local()


def source_path(model: str, fold: str) -> Path:
    return RESULTS / f"bound_timed_{model}_fold_{fold}.jsonl"


def key_of(row: dict) -> tuple[str, str, str, int]:
    return row["model"], row["fold"], str(row["prompt_id"]), int(row["generation"])


def verify_one(row: dict) -> dict:
    session = getattr(THREAD_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": "BOUND-E2new-bound-online-verifier/1.0 (research evaluation)"})
        THREAD_LOCAL.session = session
    start = time.perf_counter()
    names = sorted({str(package).strip() for package in row["packages"] if str(package).strip()})
    checks = [query(session, name, 0.0) for name in names]
    retained = [check["name"] for check in checks if check["status"] in ("exists", "stdlib")]
    elapsed = time.perf_counter() - start
    generation = float(row["generation_seconds"])
    extraction = float(row["extraction_seconds"])
    return {"model": row["model"], "fold": row["fold"], "prompt_id": row["prompt_id"],
            "generation": row["generation"], "seed": row["seed"],
            "answer": row["answer"], "source_packages": names, "checks": checks,
            "retained_packages": retained,
            "generation_seconds": generation, "extraction_seconds": extraction,
            "online_verify_filter_seconds": elapsed,
            "delivery_total_seconds": generation + extraction + elapsed,
            "filtered_absent_by_verifier": [check["name"] for check in checks if check["status"] == "absent"],
            "filtered_unknown_by_verifier": [check["name"] for check in checks if check["status"] == "unknown"],
            "extra_llm_tokens_from_verifier": 0,
            "verified_utc": datetime.now(timezone.utc).isoformat(),
            "timing_scope": "saved BOUND generation+extraction; subsequent online serial per-package PyPI query/retry/filter; no model load or offline registry labels"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 4:
        parser.error("workers must be 1–4 to limit PyPI request rate")
    expected = sum(config[1] for config in MODELS.values()) * 5 * 4
    output = RESULTS / "bound_timed_verified_all.jsonl"
    completed = set()
    if output.exists():
        with output.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                key = key_of(json.loads(line))
                if key in completed:
                    raise ValueError(f"duplicate existing verifier record {key}")
                completed.add(key)
    paths = {(model, fold): source_path(model, fold) for model in MODELS for fold in "ABCD"}
    offsets = {key: 0 for key in paths}
    source_seen = set()
    submitted = set()
    in_flight = {}
    new_count = 0
    print(f"START {datetime.now(timezone.utc).isoformat()} existing={len(completed)}/{expected} workers={args.workers}", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool, output.open("a", encoding="utf-8") as downstream:
        while len(completed) < expected:
            for source_key, path in paths.items():
                if len(in_flight) >= args.workers * 12 or not path.exists():
                    continue
                with path.open(encoding="utf-8") as upstream:
                    upstream.seek(offsets[source_key])
                    while len(in_flight) < args.workers * 12:
                        offset = upstream.tell()
                        line = upstream.readline()
                        if not line or not line.endswith("\n"):
                            upstream.seek(offset)
                            break
                        offsets[source_key] = upstream.tell()
                        row = json.loads(line)
                        marker = key_of(row)
                        if marker[:2] != source_key:
                            raise ValueError(f"source identity mismatch {path} {marker}")
                        if marker in source_seen:
                            raise ValueError(f"duplicate source record {marker}")
                        source_seen.add(marker)
                        if marker in completed:
                            continue
                        if marker in submitted:
                            raise ValueError(f"duplicate submitted record {marker}")
                        submitted.add(marker)
                        in_flight[pool.submit(verify_one, row)] = marker
            if in_flight:
                done, _ = wait(in_flight, timeout=args.poll_seconds, return_when=FIRST_COMPLETED)
                for future in done:
                    marker = in_flight.pop(future)
                    result = future.result()
                    if key_of(result) != marker:
                        raise ValueError(f"verifier result identity mismatch {marker}")
                    downstream.write(json.dumps(result, ensure_ascii=False) + "\n")
                    downstream.flush()
                    completed.add(marker)
                    new_count += 1
                    if new_count % 100 == 0:
                        print(f"{datetime.now(timezone.utc).isoformat()} new={new_count} total={len(completed)}/{expected}", flush=True)
            else:
                time.sleep(args.poll_seconds)
    print(f"COMPLETE {datetime.now(timezone.utc).isoformat()} records={len(completed)}", flush=True)


if __name__ == "__main__":
    main()
