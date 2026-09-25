"""After DeepSeekCoder paper-protocol runs finish, use GPU 2 for Llama-3.1."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
OUT = E5 / "results/01_all_module_lora/humaneval_paper_protocol"
LOG = OUT / "llama_wait_queue.jsonl"


def record(event: str, **extra: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"event": event, "utc_epoch": time.time(), **extra}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data) + "\n")
    print(json.dumps(data), flush=True)


def gpu_free() -> bool:
    proc = subprocess.run(["nvidia-smi", "-i", "2", "--query-gpu=memory.used",
                           "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if proc.returncode:
        return False
    try:
        return int(proc.stdout.strip().splitlines()[0]) < 4096
    except (ValueError, IndexError):
        return False


def main() -> None:
    while subprocess.run(["tmux", "has-session", "-t", "e5_paper_humaneval_gpu2"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        record("waiting_for_deepseek")
        time.sleep(1800)
    deep = list((OUT / "deepseekcoder").glob("fold_*/All-module-LoRA/run_*/summary.json"))
    if len(deep) != 20:
        raise SystemExit(f"DeepSeekCoder queue ended with {len(deep)}/20 summaries; inspect before proceeding")
    while not gpu_free():
        record("waiting_for_gpu2")
        time.sleep(1800)
    record("start_llama", gpu=2)
    cmd = [PYTHON, str(Path(__file__).with_name("run_paper_protocol_humaneval.py")),
           "--gpu", "2", "--models", "llama3.1-release"]
    proc = subprocess.run(cmd)
    record("end_llama", gpu=2, returncode=proc.returncode)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
