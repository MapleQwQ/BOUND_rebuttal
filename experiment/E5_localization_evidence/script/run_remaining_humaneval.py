"""Wait for E5 margin scoring, then run the remaining HumanEval models on GPU 3."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).with_name("run_all_module_humaneval.py")
LOG = E5 / "results/01_all_module_lora/humaneval/remaining_queue_log.jsonl"


def record(event: str, **extra: object) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    data = {"event": event, "utc_epoch": time.time(), **extra}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data) + "\n")
    print(json.dumps(data), flush=True)


def main() -> None:
    # The scorer owns GPU 3. Polling is intentionally sparse while it runs.
    while subprocess.run(["tmux", "has-session", "-t", "e5_margin_gpu3"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        record("waiting_for_gpu3")
        time.sleep(1800)
    for model in ("qwen3-release", "llama3.1-release"):
        record("start", model=model, gpu=3)
        cmd = [sys.executable, str(RUNNER), "--gpu", "3", "--model", model,
               "--folds", "ABCD"]
        proc = subprocess.run(cmd)
        record("end", model=model, gpu=3, returncode=proc.returncode)
        if proc.returncode:
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
