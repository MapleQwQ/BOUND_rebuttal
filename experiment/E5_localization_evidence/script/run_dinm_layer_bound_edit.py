"""Run original DINM layer selection with BOUND LoRA training and RQ3 evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
OUT = E5 / "results/05_dinm_localization_bound_edit"
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def get_modules(model: str, fold: str) -> tuple[list[str], dict]:
    base = SOURCE / model / f"fold_{fold}"
    dinm = base / "dinm_50"
    bound = base / "blast_50"
    report_file = dinm / "dinm_localization_report.json"
    requests_file = dinm / "dinm_requests.json"
    config_file = dinm / "dinm_config.json"
    edits_file = bound / "selected_task_recommend_cases.jsonl"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    requests = json.loads(requests_file.read_text(encoding="utf-8"))["requests"]
    config = json.loads(config_file.read_text(encoding="utf-8"))
    edits = [row for row in jsonl(edits_file) if row.get("type") == "task_recommend"]
    ids = [str(row["id"]) for row in edits]
    request_ids = [str(row["case_id"]) for row in requests]
    detail_ids = [str(row["case_id"]) for row in report["details"]]
    layers = [int(row["selected_layer"]) for row in report["details"]]
    if not (len(ids) == len(request_ids) == len(detail_ids) == len(layers) == 50):
        raise ValueError(f"Expected 50 paired DINM/BOUND edit cases: {model}/{fold}")
    if ids != request_ids or ids != detail_ids or layers != report["selected_layers"]:
        raise ValueError(f"DINM case/order/layer mismatch: {model}/{fold}")
    if report["method"] != "dinm-hidden-state-distance":
        raise ValueError(f"Unexpected localization algorithm: {report_file}")
    template = config["hparams"]["rewrite_module_tmp"]
    if template != "model.layers.{}.mlp.down_proj":
        raise ValueError(f"Unexpected DINM rewrite module: {template}")
    unique_layers = sorted(set(layers))
    modules = [template.format(layer) for layer in unique_layers]
    if sorted(config["rewrite_weights"]) != sorted(module + ".weight" for module in modules):
        raise ValueError(f"DINM selected weights disagree with report: {model}/{fold}")
    meta = {
        "method": report["method"], "source_implementation": "baselines2/dinm.py::locate_dinm_layers",
        "model": model, "fold": fold, "n_cases": 50,
        "case_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
        "dinm_report_sha256": sha(report_file), "dinm_requests_sha256": sha(requests_file),
        "bound_edit_cases_sha256": sha(edits_file), "dinm_config_sha256": sha(config_file),
        "selected_layers_per_case": layers, "layer_counts": dict(Counter(layers)),
        "unique_layers": unique_layers, "target_modules": modules,
        "dinm_historical_localization_seconds": json.loads((dinm / "timing.json").read_text())["localization"]["elapsed_sec"],
        "source_report": str(report_file.relative_to(ROOT)),
        "source_edit_cases": str(edits_file.relative_to(ROOT)),
    }
    return modules, meta


def one(gpu: str, model_name: str, fold: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(ROOT))
    import torch
    from scripts.run_rq3_ablation_queue import build_cfg, config_payload, summarize_eval_file
    from knowledgeEdit.package_edit import edit_package_boundary, evaluate_after_edit
    from knowledgeEdit.package_edit_utils import to_edit_config

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit(f"GPU {gpu} unavailable; refusing CPU fallback")
    out = OUT / model_name / f"fold_{fold}" / "DINM-layer+BOUND-edit"
    out.mkdir(parents=True, exist_ok=True)
    modules, loc_meta = get_modules(model_name, fold)
    meta_file = out / "run_metadata.json"
    if meta_file.exists() and json.loads(meta_file.read_text()).get("status") == "complete":
        print(json.dumps({"skip_complete": str(out)}), flush=True)
        return
    if (out / "blast_delta.pt").exists():
        raise RuntimeError(f"Partial previous run; inspect before retrying: {out}")
    (out / "dinm_layer_selection.json").write_text(json.dumps(loc_meta, indent=2) + "\n")

    cfg = build_cfg(model_name, fold, "BOUND", gpu, OUT)
    cfg.output_dir = out
    cfg.experiment_dir = out
    cfg.target_modules = ",".join(modules)
    cfg.localization_report = ""
    payload = config_payload(cfg, model_name, fold, "DINM-layer+BOUND-edit")
    payload["dinm_layer_source"] = loc_meta["source_report"]
    (out / "experiment_config.json").write_text(json.dumps(payload, indent=2) + "\n")

    started = time.time()
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    trained, tokenizer = edit_package_boundary(to_edit_config(cfg))
    edit_seconds = time.time() - t
    peak_edit_mib = torch.cuda.max_memory_reserved() / 2**20
    t = time.time()
    evaluate_after_edit(cfg, trained, tokenizer, eval_edit=False, eval_unseen=True)
    eval_seconds = time.time() - t
    del trained, tokenizer
    report = json.loads((out / "blast_config.json").read_text())
    if set(report["resolved_target_modules"].split(",")) != set(modules):
        raise ValueError(f"Trained target modules differ from DINM mapping: {out}")
    metric = summarize_eval_file(out / "eval_unseen_prompts.json", model_name, fold, "BOUND", out)
    metric["setting"] = "DINM-layer+BOUND-edit"
    (out / "rq3_metrics.json").write_text(json.dumps(metric, indent=2) + "\n")
    (out / "rq3_summary.md").write_text(
        f"# RQ3 {model_name} fold_{fold} DINM-layer+BOUND-edit\n\n"
        f"- Sample-HR: {metric['sample_hr']:.4f}\n"
        f"- Package-HR: {metric['package_hr']:.4f}\n"
        f"- Valid-Rate: {metric['valid_rate']:.4f}\n"
        f"- Empty-Rate: {metric['empty_rate']:.4f}\n"
        f"- Edited modules: {len(modules)}\n",
        encoding="utf-8",
    )
    adapter = out / "blast_delta.pt"
    state = torch.load(adapter, map_location="cpu", weights_only=True)
    data = {"status": "complete", "model": model_name, "fold": fold, "gpu": gpu,
            "started_at": started, "ended_at": time.time(),
            "dinm_historical_localization_seconds": loc_meta["dinm_historical_localization_seconds"],
            "edit_seconds": edit_seconds, "eval_seconds": eval_seconds,
            "total_new_run_seconds": time.time() - started,
            "peak_edit_reserved_mib": peak_edit_mib,
            "n_edited_modules": report["n_edited_modules"],
            "n_trainable_adapter_parameters": sum(t.numel() for t in state.values()),
            "adapter_bytes": adapter.stat().st_size, "adapter_sha256": sha(adapter),
            "dinm_report_sha256": loc_meta["dinm_report_sha256"],
            "edit_cases_sha256": loc_meta["bound_edit_cases_sha256"]}
    meta_file.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data), flush=True)


def queue(gpu: str, models: list[str], folds: str) -> None:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for model in models:
        for fold in folds:
            out = OUT / model / f"fold_{fold}" / "DINM-layer+BOUND-edit"
            out.mkdir(parents=True, exist_ok=True)
            cmd = [PYTHON, __file__, "--gpu", gpu, "--model", model,
                   "--fold", fold, "--one"]
            with (out / "queue.log").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": "start", "command": cmd, "utc_epoch": time.time()}) + "\n")
                handle.flush()
                proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                handle.write(json.dumps({"event": "end", "returncode": proc.returncode,
                                         "utc_epoch": time.time()}) + "\n")
            print(json.dumps({"model": model, "fold": fold, "returncode": proc.returncode}), flush=True)
            if proc.returncode:
                raise SystemExit(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("1", "2", "3"))
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--fold", choices=tuple("ABCD"))
    parser.add_argument("--one", action="store_true")
    args = parser.parse_args()
    if args.one:
        if not args.model or not args.fold:
            parser.error("--one requires --model and --fold")
        one(args.gpu, args.model, args.fold)
    else:
        if not args.folds or any(f not in "ABCD" for f in args.folds):
            parser.error("--folds must contain only A/B/C/D")
        queue(args.gpu, args.models, args.folds)


if __name__ == "__main__":
    main()
