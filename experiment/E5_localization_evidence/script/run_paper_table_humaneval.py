"""Evaluate All-module LoRA on the four HumanEval runs used by the paper table."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
OUT = E5 / "results/01_all_module_lora/humaneval_paper_table"
MODELS = {
    "deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
    "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
    "llama3.1-release": "/data0/shuhanliu/models/llama3.1",
}
# Recovered from E0_version_audit/results/paper_cell_provenance.csv.  Each
# published edited cell averages one selected ten-sample run per edit fold.
PAPER_RUNS = {
    "deepseekcoder": {"A": 1, "B": 1, "C": 2, "D": 2},
    "qwen3-release": {"A": 5, "B": 4, "C": 4, "D": 1},
    "llama3.1-release": {"A": 1, "B": 2, "C": 2, "D": 4},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("1", "2", "3"))
    parser.add_argument("--models", nargs="+", required=True, choices=tuple(MODELS))
    args = parser.parse_args()
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run(
        [PYTHON, "-c", "import torch; assert torch.cuda.is_available() and torch.cuda.device_count() == 1"],
        env=env, capture_output=True, text=True,
    )
    if probe.returncode:
        raise SystemExit(f"GPU {args.gpu} unavailable; refusing CPU fallback: {probe.stderr.strip()}")
    OUT.mkdir(parents=True, exist_ok=True)
    events = OUT / "queue_log.jsonl"
    for model in args.models:
        for fold, run in PAPER_RUNS[model].items():
            adapter = ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model / f"fold_{fold}/wo_localization_all_lora"
            if not (adapter / "blast_delta.pt").exists():
                raise FileNotFoundError(adapter)
            method = f"fold_{fold}/All-module-LoRA/run_{run:02d}"
            folder = OUT / model / method
            summary = folder / "summary.json"
            if summary.exists():
                payload = json.loads(summary.read_text(encoding="utf-8"))
                cfg = payload.get("generation_config", {})
                if (payload.get("n_tasks") == 164 and payload.get("n_samples") == 1640
                        and payload.get("num_samples_per_task") == 10
                        and cfg.get("seed") == 42 + run and cfg.get("max_new_tokens") == 512
                        and not cfg.get("use_chat_template") and cfg.get("enable_thinking") != "true"):
                    continue
                raise ValueError(f"Existing summary does not match the paper table: {summary}")
            cmd = [
                PYTHON, str(ROOT / "scripts/run_humaneval_models.py"),
                "--model-name", model, "--model-path", MODELS[model],
                "--method-name", method, "--delta-dir", str(adapter),
                "--adapter-type", "blast", "--out-dir", str(OUT),
                "--gpu", args.gpu, "--seed", str(42 + run),
                "--num-samples-per-task", "10", "--completion-batch-size", "10",
                "--max-new-tokens", "512", "--temperature", "0.2",
                "--top-p", "0.95", "--n-workers", "4", "--timeout", "3",
            ]
            record = {"event": "start", "model": model, "fold": fold, "run": run,
                      "gpu": args.gpu, "utc_epoch": time.time(), "command": cmd}
            with events.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "queue.log").open("a", encoding="utf-8") as handle:
                proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
            record = {"event": "end", "model": model, "fold": fold, "run": run,
                      "gpu": args.gpu, "utc_epoch": time.time(), "returncode": proc.returncode}
            with events.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            print(json.dumps(record), flush=True)
            if proc.returncode:
                raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
