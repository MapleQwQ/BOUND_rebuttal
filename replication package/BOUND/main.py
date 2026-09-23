from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from bound.bound import (
    BoundaryEditConfig,
    load_config_file,
    prepare_boundary_experiment,
    run_localize_then_edit,
)


REPO_ROOT = Path(__file__).resolve().parent
MODELS = {"deepseekcoder", "qwen3", "llama3.1"}
FOLDS = {"A", "B", "C", "D"}


def load_bound_config(config_path: str | Path) -> BoundaryEditConfig:
    payload = dict(load_config_file(config_path))
    payload.pop("alg_name", None)
    for key in [
        "model_path",
        "edits_file",
        "experiment_dir",
        "output_dir",
        "localization_report",
        "reference_response_file",
        "unseen_file",
    ]:
        value = payload.get(key)
        if value and not Path(value).is_absolute():
            payload[key] = str(REPO_ROOT / value)
    valid = {field.name for field in dataclasses.fields(BoundaryEditConfig)}
    unknown = sorted(set(payload) - valid)
    if unknown:
        raise SystemExit(f"unknown BOUND config keys in {config_path}: {unknown}")
    return BoundaryEditConfig(**payload)


def fold_dir(fold: str) -> str:
    fold = fold.replace("fold_", "")
    if fold not in FOLDS:
        raise SystemExit(f"unsupported fold: {fold}")
    return f"fold_{fold}"


def model_config(model: str) -> Path:
    if model not in MODELS:
        raise SystemExit(f"unsupported model: {model}")
    stems = {
        "deepseekcoder": "deepseekcoder",
        "qwen3": "qwen3",
        "llama3.1": "llama3.1",
    }
    path = REPO_ROOT / "bound/hparams" / f"{stems[model]}.yaml"
    if not path.exists():
        raise SystemExit(f"missing model config: {path}")
    return path


def load_model_fold_config(model: str, fold: str) -> BoundaryEditConfig:
    cfg = load_bound_config(model_config(model))
    fdir = fold_dir(fold)
    cfg.edits_file = REPO_ROOT / "data/package_hallucination" / model / fdir / "edit_cases.jsonl"
    cfg.experiment_dir = REPO_ROOT / "results/method_runs" / "package_recommendation" / model / fdir / "bound"
    return prepare_boundary_experiment(cfg)


def load_model_gpu(model: str) -> str:
    payload = dict(load_config_file(model_config(model)))
    return str(payload.get("gpu", "0"))


def cmd_run_package_recommendation(args: argparse.Namespace) -> int:
    cfg = load_model_fold_config(args.model, args.fold)
    if args.edit_only:
        cfg.auto_eval = False
    if args.max_edit_prompts:
        cfg.eval_edit_max_samples = args.max_edit_prompts
    if args.max_unseen_prompts:
        cfg.eval_unseen_max_samples = args.max_unseen_prompts
    run_localize_then_edit(cfg)
    return 0


def cmd_run_cross_task(args: argparse.Namespace) -> int:
    if args.model not in MODELS:
        raise SystemExit(f"unsupported model: {args.model}")
    fdir = fold_dir(args.fold)
    out_dir = REPO_ROOT / "results/method_runs" / "cross_task" / args.model / fdir / "bound"
    prompt_file = REPO_ROOT / "data/package_hallucination" / args.model / "cross_task_test100.jsonl"
    delta_dir = str(REPO_ROOT / "results/method_runs" / "package_recommendation" / args.model / fdir / "bound")
    adapter_type = "bound"
    model_paths = {
        "deepseekcoder": "models/deepseekcoder",
        "qwen3": "models/qwen3-8B",
        "llama3.1": "models/llama3.1",
    }
    gpu = load_model_gpu(args.model)
    from bound.cross_task import main as cross_task_main

    argv = [
        "--model-name", args.model,
        "--model-path", args.model_path or str(REPO_ROOT / model_paths[args.model]),
        "--prompt-file", str(prompt_file),
        "--out-dir", str(out_dir),
        "--adapter-type", adapter_type,
        "--gpu", gpu,
        "--max-prompts", str(args.max_prompts),
    ]
    if delta_dir:
        argv.extend(["--delta-dir", delta_dir])
    cross_task_main(argv)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BOUND replication package entry point")
    sub = parser.add_subparsers(dest="command", required=True)

    parser_package_recommendation = sub.add_parser("run-package-recommendation", help="run one BOUND package recommendation model/fold job")
    parser_package_recommendation.add_argument("--model", required=True, choices=sorted(MODELS))
    parser_package_recommendation.add_argument("--fold", required=True, choices=sorted(FOLDS))
    parser_package_recommendation.add_argument("--edit-only", action="store_true")
    parser_package_recommendation.add_argument("--max-edit-prompts", type=int, default=0)
    parser_package_recommendation.add_argument("--max-unseen-prompts", type=int, default=0)
    parser_package_recommendation.set_defaults(func=cmd_run_package_recommendation)

    parser_cross_task = sub.add_parser("run-cross-task", help="run one cross-task generalization BOUND model/fold job")
    parser_cross_task.add_argument("--model", required=True, choices=sorted(MODELS))
    parser_cross_task.add_argument("--fold", required=True, choices=sorted(FOLDS))
    parser_cross_task.add_argument("--model-path", default="")
    parser_cross_task.add_argument("--max-prompts", type=int, default=100)
    parser_cross_task.set_defaults(func=cmd_run_cross_task)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
