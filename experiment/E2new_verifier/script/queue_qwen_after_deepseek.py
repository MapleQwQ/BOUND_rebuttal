#!/usr/bin/env python3
"""Run the full Qwen Base job on GPU2 as soon as DeepSeek's GPU process exits."""

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
EXPECTED_DEEPSEEK = 541 * 5


def alive(pid):
    try:
        os.kill(pid, 0)
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists() and stat.read_text().split()[2] == "Z":
            return False
        return True
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-pid", type=int, required=True, help="PID of the running DeepSeekCoder generator")
    args = parser.parse_args()
    print(f"waiting for DeepSeekCoder PID {args.after_pid}", flush=True)
    while alive(args.after_pid):
        time.sleep(10)
    source = RESULTS / "base_timed_deepseekcoder.jsonl"
    with source.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if len(rows) != EXPECTED_DEEPSEEK or len({(str(x["prompt_id"]), x["generation"]) for x in rows}) != EXPECTED_DEEPSEEK:
        raise SystemExit(f"DeepSeekCoder incomplete, refusing GPU switch: {len(rows)}/{EXPECTED_DEEPSEEK}")
    print(f"{datetime.now(timezone.utc).isoformat()} DeepSeekCoder complete; starting Qwen3 on GPU2", flush=True)
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = "2"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, str(HERE / "generate_base_timed.py"),
               "--model", "qwen3-release", "--gpu", "2"]
    raise SystemExit(subprocess.call(command, env=environment))


if __name__ == "__main__":
    main()
