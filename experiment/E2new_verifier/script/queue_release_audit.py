#!/usr/bin/env python3
"""Wait for online verifier completion before starting independent cutoff audit."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
EXPECTED = {"deepseekcoder": 2705, "qwen3-release": 2045, "llama3.1-release": 4670}


def alive(pid):
    try:
        os.kill(pid, 0)
        stat = Path(f"/proc/{pid}/stat")
        return not (stat.exists() and stat.read_text().split()[2] == "Z")
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-pid", type=int, required=True)
    args = parser.parse_args()
    print(f"waiting for verifier PID {args.after_pid}", flush=True)
    while alive(args.after_pid):
        time.sleep(10)
    for model, expected in EXPECTED.items():
        path = RESULTS / f"base_timed_verified_{model}.jsonl"
        with path.open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        if len(rows) != expected or len({(str(x["prompt_id"]), x["generation"]) for x in rows}) != expected:
            raise SystemExit(f"verification incomplete: {model} {len(rows)}/{expected}")
    print(f"{datetime.now(timezone.utc).isoformat()} all BOV complete; starting cutoff release-date audit", flush=True)
    raise SystemExit(subprocess.call([sys.executable, str(HERE / "fetch_release_dates.py")]))


if __name__ == "__main__":
    main()
