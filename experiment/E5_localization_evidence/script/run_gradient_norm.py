"""Controlled gradient-only localization, unchanged BOUND editing, and RQ3 evaluation.

The alternative localizer is compiled from the repository localizer with exactly
one expression replaced. This keeps all prompts, risk terms, backward calls,
aggregation, and report ordering identical without modifying production code.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
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
OLD_EXPR = "(weight.grad.detach().float() * weight.detach().float()).abs().mean().item()"
NEW_EXPR = "weight.grad.detach().float().abs().mean().item()"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gradient_only_localizer():
    import knowledgeEdit.package_edit as core
    source = inspect.getsource(core.localize_package_boundary)
    if source.count(OLD_EXPR) != 1:
        raise RuntimeError("Expected exactly one gradient×weight score expression")
    altered = source.replace(OLD_EXPR, NEW_EXPR)
    if altered.replace(NEW_EXPR, OLD_EXPR) != source:
        raise RuntimeError("Alternative localizer differs beyond the score expression")
    namespace = {}
    exec(compile(altered, str(inspect.getsourcefile(core.localize_package_boundary)), "exec"), core.__dict__, namespace)
    return namespace["localize_package_boundary"], hashlib.sha256(source.encode()).hexdigest(), hashlib.sha256(altered.encode()).hexdigest()


def selection(report: Path, cfg) -> list[str]:
    from knowledgeEdit.package_edit_utils import select_modules_from_report
    return [x for x in select_modules_from_report(report, cfg.localization_top_k,
                                                  cfg.localization_mode, cfg.localization_window).split(",") if x]


def one(gpu: str, model_name: str, fold: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(ROOT))
    import torch
    from scripts.run_rq3_ablation_queue import build_cfg, config_payload, summarize_eval_file
    from knowledgeEdit.package_edit import edit_package_boundary, evaluate_after_edit, localize_package_boundary
    from knowledgeEdit.package_edit_utils import to_edit_config, to_localization_config

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError(f"GPU {gpu} unavailable; CPU fallback forbidden")
    out = OUT / model_name / f"fold_{fold}"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "run_metadata.json").exists() and read(out / "run_metadata.json").get("status") == "complete":
        print(json.dumps({"skip_complete": str(out)}), flush=True)
        return
    if (out / "blast_delta.pt").exists():
        raise RuntimeError(f"Partial adapter exists; inspect before retrying: {out}")

    cfg = build_cfg(model_name, fold, "BOUND", gpu, OUT)
    paper_dir = SOURCE / model_name / f"fold_{fold}" / "blast_50"
    paper_config = read(paper_dir / "blast_config.json")
    # The final Llama A BOUND adapter uses 43 despite the source YAML's 42.
    cfg.seed = int(paper_config["seed"])
    cfg.output_dir = out
    cfg.experiment_dir = out
    cfg.localization_report = str(out / "localization_report_gradient_norm.json")
    cfg.target_modules = ""
    if cfg.rank != 8 or cfg.edit_case_count != 50 or cfg.eval_num_generations != 5:
        raise RuntimeError("RQ3 configuration drift")
    control_report = out / "localization_report_gradient_weight_control.json"
    gradient_report = Path(cfg.localization_report)
    old_report = paper_dir / "localization_report.json"
    original_source = ROOT / "knowledgeEdit/package_edit.py"
    alt_func, original_fn_hash, alt_fn_hash = gradient_only_localizer()

    started = time.time()
    loc_seconds = {}
    for method, path, func in (("gradient_weight", control_report, localize_package_boundary),
                               ("gradient_norm", gradient_report, alt_func)):
        if not path.exists():
            loc_cfg = to_localization_config(cfg)
            loc_cfg.out_file = path
            t = time.time()
            func(loc_cfg)
            loc_seconds[method] = time.time() - t
        else:
            loc_seconds[method] = None
    original = read(old_report)
    regenerated = read(control_report)
    changed = read(gradient_report)
    if original["n_records"] != regenerated["n_records"] or original["n_records"] != changed["n_records"]:
        raise RuntimeError("Localization case count differs from original BOUND")
    original_modules = selection(old_report, cfg)
    regenerated_modules = selection(control_report, cfg)
    gradient_modules = selection(gradient_report, cfg)
    stored_modules = [x for x in paper_config["resolved_target_modules"].split(",") if x]
    control_match = set(original_modules) == set(regenerated_modules) == set(stored_modules)
    # Full rank lists can differ slightly around ties, but trained module sets must match.
    if not control_match:
        write(out / "control_mismatch.json", {"historical": original_modules,
              "regenerated": regenerated_modules, "stored": stored_modules})
        raise RuntimeError(f"Regenerated gradient×weight control does not select original modules: {out}")
    old_seed = {x["module"] for x in original["layer_scores"][:cfg.localization_top_k]}
    new_seed = {x["module"] for x in changed["layer_scores"][:cfg.localization_top_k]}
    old_set, new_set = set(original_modules), set(gradient_modules)
    overlap = {
        "model": model_name, "fold": fold,
        "top_k": cfg.localization_top_k, "selection_mode": cfg.localization_mode,
        "window": cfg.localization_window,
        "historical_control_matches_regenerated_selection": control_match,
        "top_k_original": sorted(old_seed), "top_k_gradient_norm": sorted(new_seed),
        "top_k_intersection": len(old_seed & new_seed),
        "top_k_jaccard": len(old_seed & new_seed) / len(old_seed | new_seed),
        "selected_original": sorted(old_set), "selected_gradient_norm": sorted(new_set),
        "selected_original_n": len(old_set), "selected_gradient_norm_n": len(new_set),
        "selected_intersection": len(old_set & new_set),
        "selected_jaccard": len(old_set & new_set) / len(old_set | new_set),
        "selected_equal_cardinality": len(old_set) == len(new_set),
        "original_source_sha256": sha(original_source),
        "original_localizer_sha256": original_fn_hash,
        "gradient_localizer_sha256": alt_fn_hash,
        "historical_report_sha256": sha(old_report),
        "regenerated_control_sha256": sha(control_report),
        "gradient_report_sha256": sha(gradient_report),
    }
    write(out / "module_overlap.json", overlap)
    # The original BOUND window_family rule can expand different top-k families
    # into different final counts; report that difference rather than hiding it.
    write(out / "experiment_config.json", config_payload(cfg, model_name, fold, "GradientNorm+BOUND-edit"))
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    trained, tokenizer = edit_package_boundary(to_edit_config(cfg))
    edit_seconds = time.time() - t
    peak_edit_mib = torch.cuda.max_memory_reserved() / 2**20
    t = time.time()
    evaluate_after_edit(cfg, trained, tokenizer, eval_edit=False, eval_unseen=True)
    eval_seconds = time.time() - t
    del trained, tokenizer
    report = read(out / "blast_config.json")
    if set(report["resolved_target_modules"].split(",")) != new_set:
        raise RuntimeError("Edited modules differ from gradient-norm report")
    metric = summarize_eval_file(out / "eval_unseen_prompts.json", model_name, fold, "BOUND", out)
    metric["setting"] = "GradientNorm+BOUND-edit"
    trials = [t for row in read(out / "eval_unseen_prompts.json")["details"] for t in row["edited"]["trials"]]
    metric["no_package_rate"] = metric["empty_rate"]
    metric["empty_rate"] = sum(not str(t.get("answer") or "").strip() for t in trials) / len(trials)
    write(out / "rq3_metrics.json", metric)
    (out / "rq3_summary.md").write_text(
        f"# RQ3 {model_name} fold_{fold} GradientNorm+BOUND-edit\n\n"
        f"- Sample-HR: {metric['sample_hr']:.4f}\n- Package-HR: {metric['package_hr']:.4f}\n"
        f"- Valid-Rate: {metric['valid_rate']:.4f}\n- Blank-output rate: {metric['empty_rate']:.4f}\n"
        f"- No-extracted-package rate: {metric['no_package_rate']:.4f}\n", encoding="utf-8")
    adapter = out / "blast_delta.pt"
    state = torch.load(adapter, map_location="cpu", weights_only=True)
    write(out / "run_metadata.json", {
        "status": "complete", "model": model_name, "fold": fold, "gpu": gpu,
        "seed": cfg.seed, "started_at": started, "ended_at": time.time(),
        "localization_seconds": loc_seconds, "edit_seconds": edit_seconds,
        "eval_seconds": eval_seconds, "total_seconds": time.time() - started,
        "peak_edit_reserved_mib": peak_edit_mib,
        "n_edited_modules": report["n_edited_modules"],
        "n_adapter_parameters": sum(x.numel() for x in state.values()),
        "adapter_bytes": adapter.stat().st_size, "adapter_sha256": sha(adapter),
        "edit_cases_sha256": sha(cfg.edits_file), "eval_file_sha256": sha(out / "eval_unseen_prompts.json"),
    })
    print(json.dumps({"complete": f"{model_name}/{fold}", "metrics": metric,
                      "overlap": overlap["selected_jaccard"]}), flush=True)


def queue(gpu: str, model_names: list[str], folds: str) -> None:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for model in model_names:
        for fold in folds:
            out = OUT / model / f"fold_{fold}"
            out.mkdir(parents=True, exist_ok=True)
            cmd = [PYTHON, __file__, "--gpu", gpu, "--model", model, "--fold", fold, "--one"]
            with (out / "queue.log").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": "start", "command": cmd, "epoch": time.time()}) + "\n")
                handle.flush()
                proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                handle.write(json.dumps({"event": "end", "returncode": proc.returncode,
                                         "epoch": time.time()}) + "\n")
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
