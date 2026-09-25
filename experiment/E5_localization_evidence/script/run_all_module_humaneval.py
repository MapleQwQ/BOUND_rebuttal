"""Run existing All-module LoRA adapters through the paper HumanEval harness.

Only physical GPUs 2 and 3 are accepted. Results stay inside E5.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
MODEL_PATHS = {
    "deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
    "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
    "llama3.1-release": "/data0/shuhanliu/models/llama3.1",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--model", required=True, choices=tuple(MODEL_PATHS))
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--max-tasks", type=int, default=0, help="Use only for a separate smoke output")
    args = parser.parse_args()
    if not args.folds or any(fold not in "ABCD" for fold in args.folds):
        parser.error("--folds must contain only A/B/C/D")
    if len(set(args.folds)) != len(args.folds):
        parser.error("duplicate fold")
    output = E5 / "results/01_all_module_lora" / ("humaneval_smoke" if args.max_tasks else "humaneval")
    log = output / "queue_log.jsonl"
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run([PYTHON, "-c", "import torch; assert torch.cuda.is_available() and torch.cuda.device_count() == 1"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
    if probe.returncode:
        raise SystemExit(f"GPU {args.gpu} is not visible; refusing CPU fallback: {probe.stderr.strip()}")
    for fold in args.folds:
        method = f"fold_{fold}/All-module-LoRA"
        summary = output / args.model / method / "summary.json"
        if summary.exists():
            done = json.loads(summary.read_text(encoding="utf-8"))
            if done.get("n_tasks") == (args.max_tasks or 164):
                continue
            raise ValueError(f"Existing summary has wrong task count: {summary}")
        delta = ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / args.model / f"fold_{fold}" / "wo_localization_all_lora"
        if not (delta / "blast_delta.pt").exists():
            raise FileNotFoundError(delta)
        cmd = [PYTHON, str(ROOT / "scripts/run_humaneval_models.py"),
               "--model-name", args.model, "--model-path", MODEL_PATHS[args.model],
               "--method-name", method, "--delta-dir", str(delta), "--adapter-type", "blast",
               "--out-dir", str(output), "--gpu", args.gpu,
               "--num-samples-per-task", "1", "--max-new-tokens", "512",
               "--temperature", "0.2", "--top-p", "0.95", "--n-workers", "4"]
        if args.max_tasks:
            cmd += ["--max-tasks", str(args.max_tasks)]
        record = {"event": "start", "model": args.model, "fold": fold, "gpu": args.gpu,
                  "max_tasks": args.max_tasks, "utc_epoch": time.time(), "command": cmd}
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        with (output / f"gpu{args.gpu}.log").open("a", encoding="utf-8") as handle:
            proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
        record = {"event": "end", "model": args.model, "fold": fold, "gpu": args.gpu,
                  "returncode": proc.returncode, "utc_epoch": time.time()}
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)
        if proc.returncode:
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
