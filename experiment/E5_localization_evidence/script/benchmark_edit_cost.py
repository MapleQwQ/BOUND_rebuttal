"""Same-GPU E5 edit-cost benchmark, including BOUND localization and LoRA training.

Run a queue with --models/--folds; each fold/condition uses a fresh process so
peak CUDA memory and wall time are comparable and prior jobs release memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
CONDITIONS = ("BOUND", "wo_localization_all_lora")
RESULTS = E5 / "results/01_all_module_lora/cost_rebench"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(gpu: str, model_name: str, fold: str, condition: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(ROOT))
    import torch
    from scripts.run_rq3_ablation_queue import build_cfg
    from knowledgeEdit.package_edit import edit_package_boundary, localize_package_boundary
    from knowledgeEdit.package_edit_utils import to_edit_config, to_localization_config

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit(f"GPU {gpu} unavailable; refusing CPU fallback")
    cfg = build_cfg(model_name, fold, condition, "", RESULTS)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta_file = out / "cost_metadata.json"
    if meta_file.exists():
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        if data.get("status") == "complete":
            print(json.dumps({"skip_complete": str(out)}), flush=True)
            return
        raise ValueError(f"Incomplete previous benchmark: {meta_file}")

    started = time.time()
    source_yaml = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / model_name / f"fold_{fold}/blast_50.yaml"
    selected = Path(cfg.edits_file)
    localization_seconds = 0.0
    peak_localization_mib = 0.0
    if condition == "BOUND":
        cfg.target_modules = ""
        cfg.localization_report = str(out / "localization_report.json")
        torch.cuda.reset_peak_memory_stats()
        t = time.time()
        localize_package_boundary(to_localization_config(cfg))
        localization_seconds = time.time() - t
        peak_localization_mib = torch.cuda.max_memory_reserved() / 2**20
        torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    model, tokenizer = edit_package_boundary(to_edit_config(cfg))
    edit_seconds = time.time() - t
    peak_edit_mib = torch.cuda.max_memory_reserved() / 2**20
    del model, tokenizer
    config = json.loads((out / "blast_config.json").read_text(encoding="utf-8"))
    adapter = out / "blast_delta.pt"
    data = {"status": "complete", "model": model_name, "fold": fold, "condition": condition,
            "gpu": gpu, "source_yaml_sha256": sha(source_yaml), "edit_cases_sha256": sha(selected),
            "localization_seconds": localization_seconds, "edit_seconds": edit_seconds,
            "total_seconds": time.time() - started,
            "peak_localization_reserved_mib": peak_localization_mib,
            "peak_edit_reserved_mib": peak_edit_mib,
            "n_edited_modules": config["n_edited_modules"],
            "adapter_bytes": adapter.stat().st_size, "adapter_sha256": sha(adapter),
            "resolved_target_modules": config["resolved_target_modules"]}
    meta_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data), flush=True)


def queue(gpu: str, models: list[str], folds: str) -> None:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    RESULTS.mkdir(parents=True, exist_ok=True)
    for model_name in models:
        for fold in folds:
            for condition in CONDITIONS:
                cmd = [PYTHON, __file__, "--gpu", gpu, "--model", model_name,
                       "--fold", fold, "--condition", condition, "--one"]
                out = RESULTS / model_name / f"fold_{fold}" / condition
                out.mkdir(parents=True, exist_ok=True)
                with (out / "queue.log").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"event": "start", "command": cmd, "utc_epoch": time.time()}) + "\n")
                    handle.flush()
                    proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                    handle.write(json.dumps({"event": "end", "returncode": proc.returncode,
                                             "utc_epoch": time.time()}) + "\n")
                print(json.dumps({"model": model_name, "fold": fold, "condition": condition,
                                  "returncode": proc.returncode}), flush=True)
                if proc.returncode:
                    raise SystemExit(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--fold", choices=tuple("ABCD"))
    parser.add_argument("--condition", choices=CONDITIONS)
    parser.add_argument("--one", action="store_true")
    args = parser.parse_args()
    if args.one:
        if not (args.model and args.fold and args.condition):
            parser.error("--one needs --model, --fold and --condition")
        one(args.gpu, args.model, args.fold, args.condition)
    else:
        if not args.folds or any(fold not in "ABCD" for fold in args.folds):
            parser.error("--folds must contain only A/B/C/D")
        queue(args.gpu, args.models, args.folds)


if __name__ == "__main__":
    main()
