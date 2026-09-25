"""Run the 12 E5 sequence-margin folds sequentially on one allowed GPU."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).with_name("score_sequence_margin.py")
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--candidate-manifest", choices=("preliminary", "registry_screened"),
                        default="registry_screened")
    parser.add_argument("--leading-space", action="store_true")
    args = parser.parse_args()
    if not args.folds or any(f not in "ABCD" for f in args.folds):
        parser.error("--folds must contain only A/B/C/D")

    variant = f"scores_{args.candidate_manifest}" + ("_leading_space" if args.leading_space else "")
    output = E5 / "results/04_sequence_margin" / variant
    output.mkdir(parents=True, exist_ok=True)
    queue_log = output / "queue_log.jsonl"
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run(
        [sys.executable, "-c", "import torch; assert torch.cuda.is_available() and torch.cuda.device_count() == 1"],
        env=env, capture_output=True, text=True,
    )
    if probe.returncode:
        raise SystemExit(f"GPU {args.gpu} unavailable: {probe.stderr.strip()}")

    for model in args.models:
        for fold in args.folds:
            folder = output / model / f"fold_{fold}"
            meta = folder / "metadata.json"
            if meta.exists():
                done = json.loads(meta.read_text(encoding="utf-8"))
                if done.get("n_candidate_scores", 0) > 0:
                    continue
                raise ValueError(f"Incomplete metadata: {meta}")
            if (folder / "per_candidate.jsonl").exists():
                raise ValueError(f"Partial result requires inspection: {folder}")
            record = {"event": "start", "model": model, "fold": fold, "gpu": args.gpu,
                      "utc_epoch": time.time()}
            with queue_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            cmd = [sys.executable, str(SCRIPT), "--gpu", args.gpu, "--model", model,
                   "--fold", fold, "--candidate-manifest", args.candidate_manifest]
            if args.leading_space:
                cmd.append("--leading-space")
            with (output / f"gpu{args.gpu}.log").open("a", encoding="utf-8") as handle:
                proc = subprocess.run(cmd, env=env, stdout=handle, stderr=subprocess.STDOUT)
            record = {"event": "end", "model": model, "fold": fold, "gpu": args.gpu,
                      "returncode": proc.returncode, "utc_epoch": time.time()}
            with queue_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
            print(json.dumps(record), flush=True)
            if proc.returncode:
                raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
