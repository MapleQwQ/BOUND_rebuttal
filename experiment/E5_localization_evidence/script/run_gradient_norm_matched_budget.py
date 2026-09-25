"""Matched final-module-count sensitivity for gradient-norm folds that expand beyond BOUND."""

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
OUT = E5 / "results/06_gradient_norm"
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(gpu: str, model: str, fold: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(ROOT))
    import torch
    from scripts.run_rq3_ablation_queue import build_cfg, config_payload, summarize_eval_file
    from knowledgeEdit.package_edit import edit_package_boundary, evaluate_after_edit
    from knowledgeEdit.package_edit_utils import module_family, select_modules_from_report, to_edit_config

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError(f"GPU {gpu} unavailable")
    parent = OUT / model / f"fold_{fold}"
    out = parent / "matched_budget"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "run_metadata.json").exists() and read(out / "run_metadata.json").get("status") == "complete":
        print(json.dumps({"skip_complete": str(out)}), flush=True)
        return
    if (out / "blast_delta.pt").exists():
        raise RuntimeError(f"Partial adapter requires inspection: {out}")
    report = parent / "localization_report_gradient_norm.json"
    if not report.exists():
        raise RuntimeError(f"Missing gradient report: {report}")
    overlap = read(parent / "module_overlap.json")
    target_n = int(overlap["selected_original_n"])
    cfg = build_cfg(model, fold, "BOUND", gpu, OUT)
    paper_cfg = read(SOURCE / model / f"fold_{fold}/blast_50/blast_config.json")
    cfg.seed = int(paper_cfg["seed"])
    selected = [x for x in select_modules_from_report(report, cfg.localization_top_k,
                cfg.localization_mode, cfg.localization_window).split(",") if x]
    if len(selected) == target_n:
        raise RuntimeError(f"Matched-budget rerun unnecessary: {model}/{fold}")
    if len(selected) > target_n:
        matched = selected[:target_n]
        adjustment = "rank_order_cap"
    else:
        matched = list(selected)
        selected_families = {module_family(x) for x in selected}
        candidates = [row["module"] for row in read(report)["layer_scores"]]
        candidates = [x for x in candidates if x not in matched and module_family(x) in selected_families]
        candidates += [x for x in [row["module"] for row in read(report)["layer_scores"]]
                       if x not in matched and x not in candidates]
        matched.extend(candidates[:target_n - len(matched)])
        if len(matched) != target_n:
            raise RuntimeError(f"Not enough candidate modules to match budget: {model}/{fold}")
        adjustment = "same_family_ranked_augmentation"
    cfg.output_dir = out
    cfg.experiment_dir = out
    cfg.localization_report = ""
    cfg.target_modules = ",".join(matched)
    write(out / "matched_selection.json", {
        "method": "gradient_norm_window_family_then_match_final_module_count",
        "adjustment": adjustment,
        "source_report": str(report), "source_report_sha256": sha(report),
        "uncapped_modules": selected, "matched_modules": matched,
        "excluded_by_budget_cap": selected[target_n:],
        "added_to_match_budget": [x for x in matched if x not in selected],
        "target_module_count": target_n,
        "source_control_modules": overlap["selected_original"],
    })
    write(out / "experiment_config.json", config_payload(cfg, model, fold, "GradientNorm+BOUND-edit matched-budget"))
    started = time.time()
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    trained, tokenizer = edit_package_boundary(to_edit_config(cfg))
    edit_seconds = time.time() - t
    peak_mib = torch.cuda.max_memory_reserved() / 2**20
    t = time.time()
    evaluate_after_edit(cfg, trained, tokenizer, eval_edit=False, eval_unseen=True)
    eval_seconds = time.time() - t
    del trained, tokenizer
    actual = read(out / "blast_config.json")
    if set(actual["resolved_target_modules"].split(",")) != set(matched):
        raise RuntimeError("Matched-budget edited modules differ from selected set")
    metrics = summarize_eval_file(out / "eval_unseen_prompts.json", model, fold, "BOUND", out)
    metrics["setting"] = "GradientNorm+BOUND-edit matched-budget"
    trials = [t for row in read(out / "eval_unseen_prompts.json")["details"] for t in row["edited"]["trials"]]
    metrics["no_package_rate"] = metrics["empty_rate"]
    metrics["empty_rate"] = sum(not str(t.get("answer") or "").strip() for t in trials) / len(trials)
    write(out / "rq3_metrics.json", metrics)
    (out / "rq3_summary.md").write_text(
        f"# RQ3 {model} fold_{fold} GradientNorm+BOUND-edit matched-budget\n\n"
        f"- Sample-HR: {metrics['sample_hr']:.4f}\n- Package-HR: {metrics['package_hr']:.4f}\n"
        f"- Valid-Rate: {metrics['valid_rate']:.4f}\n- Blank-output rate: {metrics['empty_rate']:.4f}\n"
        f"- No-extracted-package rate: {metrics['no_package_rate']:.4f}\n", encoding="utf-8")
    adapter = out / "blast_delta.pt"
    state = torch.load(adapter, map_location="cpu", weights_only=True)
    paper_adapter = SOURCE / model / f"fold_{fold}/blast_50/blast_delta.pt"
    paper_state = torch.load(paper_adapter, map_location="cpu", weights_only=True)
    adapter_parameters = sum(x.numel() for x in state.values())
    paper_parameters = sum(x.numel() for x in paper_state.values())
    if adapter_parameters != paper_parameters:
        raise RuntimeError(f"Matched module count but unequal LoRA parameters: {model}/{fold}")
    write(out / "run_metadata.json", {
        "status": "complete", "model": model, "fold": fold, "gpu": gpu,
        "seed": cfg.seed, "started_at": started, "ended_at": time.time(),
        "edit_seconds": edit_seconds, "eval_seconds": eval_seconds,
        "peak_edit_reserved_mib": peak_mib, "n_edited_modules": actual["n_edited_modules"],
        "n_adapter_parameters": adapter_parameters,
        "bound_adapter_parameters": paper_parameters,
        "adapter_bytes": adapter.stat().st_size, "adapter_sha256": sha(adapter),
        "eval_file_sha256": sha(out / "eval_unseen_prompts.json"),
    })
    print(json.dumps({"complete": f"{model}/{fold}/matched_budget", "metrics": metrics}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("1", "2", "3"))
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--folds", default="ABCD")
    parser.add_argument("--fold", choices=tuple("ABCD"))
    parser.add_argument("--one", action="store_true")
    args = parser.parse_args()
    if args.one:
        if not args.fold:
            parser.error("--one requires --fold")
        one(args.gpu, args.model, args.fold)
        return
    for fold in args.folds:
        overlap_file = OUT / args.model / f"fold_{fold}" / "module_overlap.json"
        if not overlap_file.exists():
            raise RuntimeError(f"Missing main localization result: {overlap_file}")
        overlap = read(overlap_file)
        if overlap["selected_original_n"] == overlap["selected_gradient_norm_n"]:
            print(json.dumps({"model": args.model, "fold": fold, "skip_equal_budget": True}), flush=True)
            continue
        out = OUT / args.model / f"fold_{fold}" / "matched_budget"
        out.mkdir(parents=True, exist_ok=True)
        cmd = [PYTHON, __file__, "--gpu", args.gpu, "--model", args.model, "--fold", fold, "--one"]
        with (out / "queue.log").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "start", "command": cmd, "epoch": time.time()}) + "\n")
            handle.flush()
            proc = subprocess.run(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
            handle.write(json.dumps({"event": "end", "returncode": proc.returncode, "epoch": time.time()}) + "\n")
        print(json.dumps({"model": args.model, "fold": fold, "returncode": proc.returncode}), flush=True)
        if proc.returncode:
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
