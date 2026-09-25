"""All-module LoRA HumanEval with the paper's 10-sample, five-run protocol."""

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
MODELS = {
    "deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
    "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
    "llama3.1-release": "/data0/shuhanliu/models/llama3.1",
}
OUT = E5 / "results/01_all_module_lora/humaneval_paper_protocol"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--models", nargs="+", required=True, choices=tuple(MODELS))
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--runs", default="12345")
    args = parser.parse_args()
    if not args.folds or any(f not in "ABCD" for f in args.folds) or len(set(args.folds)) != len(args.folds):
        parser.error("--folds must be unique A/B/C/D")
    if not args.runs or any(r not in "12345" for r in args.runs) or len(set(args.runs)) != len(args.runs):
        parser.error("--runs must be unique 1/2/3/4/5")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run([PYTHON, "-c", "import torch; assert torch.cuda.is_available() and torch.cuda.device_count() == 1"],
                           env=env, capture_output=True, text=True)
    if probe.returncode:
        raise SystemExit(f"GPU {args.gpu} unavailable; refusing CPU fallback: {probe.stderr.strip()}")
    OUT.mkdir(parents=True, exist_ok=True)
    events = OUT / "queue_log.jsonl"
    for model in args.models:
        for fold in args.folds:
            adapter = ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model / f"fold_{fold}/wo_localization_all_lora"
            if not (adapter / "blast_delta.pt").exists():
                raise FileNotFoundError(adapter)
            for run in args.runs:
                method = f"fold_{fold}/All-module-LoRA/run_{int(run):02d}"
                folder = OUT / model / method
                summary = folder / "summary.json"
                if summary.exists():
                    payload = json.loads(summary.read_text(encoding="utf-8"))
                    cfg = payload.get("generation_config", {})
                    expected_tokens = 2048 if model == "qwen3-release" else 512
                    if (payload.get("n_tasks") == 164 and payload.get("n_samples") == 1640
                            and cfg.get("seed") == 42 + int(run)
                            and cfg.get("max_new_tokens") == expected_tokens):
                        continue
                    raise ValueError(f"Existing summary does not match protocol: {summary}")
                cmd = [PYTHON, str(ROOT / "scripts/run_humaneval_models.py"),
                       "--model-name", model, "--model-path", MODELS[model],
                       "--method-name", method, "--delta-dir", str(adapter),
                       "--adapter-type", "blast", "--out-dir", str(OUT),
                       "--gpu", args.gpu, "--seed", str(42 + int(run)),
                       "--num-samples-per-task", "10", "--completion-batch-size", "10",
                       "--max-new-tokens", "2048" if model == "qwen3-release" else "512",
                       "--temperature", "0.2", "--top-p", "0.95", "--n-workers", "4", "--timeout", "3"]
                if model == "qwen3-release":
                    cmd += ["--use-chat-template", "--enable-thinking", "true"]
                record = {"event": "start", "model": model, "fold": fold, "run": int(run),
                          "gpu": args.gpu, "utc_epoch": time.time(), "command": cmd}
                with events.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                folder.mkdir(parents=True, exist_ok=True)
                with (folder / "queue.log").open("a", encoding="utf-8") as handle:
                    proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                record = {"event": "end", "model": model, "fold": fold, "run": int(run),
                          "gpu": args.gpu, "utc_epoch": time.time(), "returncode": proc.returncode}
                with events.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                print(json.dumps(record), flush=True)
                if proc.returncode:
                    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
