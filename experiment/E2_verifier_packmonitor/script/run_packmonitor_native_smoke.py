#!/usr/bin/env python3
"""在 PackMonitor 原生 pip-install 语法上运行真实生成中约束 smoke。"""

from __future__ import annotations

import argparse
import json
import re
import time
import traceback
from pathlib import Path

import torch

from packmonitor_generate import PackMonitor
from knowledgeEdit.package_edit_utils import inject_lora


DEFAULT_IDS = ("429", "3896", "3151", "4369", "1728")
PIP_RE = re.compile(r"```bash\s*\n\s*pip\s+install\s+([^#\n]+)", re.IGNORECASE)


class TypoPatchedPackMonitor(PackMonitor):
    """只修正官方 grammar 中 NATATURAL_LANG 的明显拼写错误。"""

    def make_grammar(self, package_list: list[str]) -> str:
        return super().make_grammar(package_list).replace("NATATURAL_LANG", "NATURAL_LANG")


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def extract_packages(text: str) -> list[str]:
    matches = PIP_RE.findall(text)
    packages: list[str] = []
    for match in matches:
        for token in match.split():
            token = token.strip("'\";, ")
            if token and not token.startswith("-"):
                packages.append(normalize(token))
    return list(dict.fromkeys(packages))


def load_tasks(eval_path: Path, ids: tuple[str, ...]) -> list[dict]:
    data = json.loads(eval_path.read_text(encoding="utf-8"))
    rows = {str(row["id"]): row for row in data["details"]}
    missing = [key for key in ids if key not in rows]
    if missing:
        raise ValueError(f"missing prompt ids: {missing}")
    tasks = []
    for key in ids:
        question = rows[key]["question"]
        prompt = (
            "Identify the Python distributions needed for the following task. "
            "Return only one Markdown bash code block containing exactly one `pip install` command. "
            "After `pip install`, use only plain PyPI distribution names separated by spaces; "
            "do not use version specifiers, options, comments, prose, or standard-library modules.\n\n"
            f"Task: {question}"
        )
        tasks.append({"prompt_id": key, "question": question, "prompt": prompt})
    return tasks


def official_grammar_probe(model: TypoPatchedPackMonitor) -> dict:
    """保留官方原样 grammar 的 matcher 错误证据，不运行生成。"""
    grammar = PackMonitor.make_grammar(model, ["requests", "numpy"])
    from llguidance import LLMatcher, grammar_from

    matcher = LLMatcher(model.ll_tokenizer, grammar=grammar_from("lark", grammar))
    return {
        "is_error": matcher.is_error(),
        "error": matcher.get_error() if matcher.is_error() else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--eval-json", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--prompt-ids", default=",".join(DEFAULT_IDS))
    parser.add_argument("--manifest-json", default="")
    parser.add_argument("--manifest-model", default="deepseekcoder")
    parser.add_argument("--delta-dir", default="")
    parser.add_argument("--condition-prefix", choices=["base", "bound"], default="base")
    args = parser.parse_args()

    if args.manifest_json:
        manifest = json.loads(Path(args.manifest_json).read_text(encoding="utf-8"))
        prompt_ids = tuple(str(value) for value in manifest["models"][args.manifest_model]["selected_prompt_ids"])
    else:
        prompt_ids = tuple(value.strip() for value in args.prompt_ids.split(",") if value.strip())
    tasks = load_tasks(Path(args.eval_json), prompt_ids)
    registry_list = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    registry = {normalize(name) for name in registry_list}

    load_start = time.perf_counter()
    model = TypoPatchedPackMonitor(args.model_path, package_path=[args.registry])
    load_seconds = time.perf_counter() - load_start
    probe = official_grammar_probe(model)
    if not probe["is_error"]:
        raise RuntimeError("expected frozen official grammar to expose its undefined-symbol error")

    delta_dir = Path(args.delta_dir) if args.delta_dir else None
    if args.condition_prefix == "bound":
        if delta_dir is None:
            parser.error("--delta-dir is required when --condition-prefix=bound")
        config_file = delta_dir / "blast_config.json"
        delta_file = delta_dir / "blast_delta.pt"
        if not config_file.exists():
            config_file = delta_dir / "bee_config.json"
        if not delta_file.exists():
            delta_file = delta_dir / "bee_delta.pt"
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        target_modules = cfg.get("resolved_target_modules", cfg["target_modules"])
        targets = [value.strip() for value in target_modules.split(",") if value.strip()]
        inject_lora(model.model, targets, int(cfg["rank"]), float(cfg["alpha"]), 0.0)
        state = torch.load(delta_file, map_location="cpu")
        model.model.load_state_dict(state, strict=False)
        model.model.eval()

    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    with output_path.open("w", encoding="utf-8") as handle:
        for task in tasks:
            messages = [{"role": "user", "content": task["prompt"]}]
            condition_pairs = (
                (("base", False), ("packmonitor", True))
                if args.condition_prefix == "base"
                else (("bound", False), ("bound_packmonitor", True))
            )
            for condition, use_packmonitor in condition_pairs:
                start = time.perf_counter()
                try:
                    text, tokens = model.generate(
                        messages,
                        use_packmonitor=use_packmonitor,
                        max_tokens=args.max_tokens,
                        temperature=0.0,
                    )
                    error = None
                    stack = None
                except Exception as exc:  # 保存完整失败而不是将失败计为空回答
                    text = ""
                    tokens = 0
                    error = f"{type(exc).__name__}: {exc}"
                    stack = traceback.format_exc()
                latency = time.perf_counter() - start
                packages = extract_packages(text)
                invalid = [name for name in packages if name not in registry]
                row = {
                    **task,
                    "condition": condition,
                    "use_packmonitor": use_packmonitor,
                    "compatibility_patch": "NATATURAL_LANG->NATURAL_LANG" if use_packmonitor else None,
                    "answer": text,
                    "decoded_tokens": tokens,
                    "latency_seconds": latency,
                    "install_region_emitted": bool(PIP_RE.search(text)),
                    "packages": packages,
                    "invalid_packages": invalid,
                    "empty_package_list": not packages,
                    "error": error,
                    "traceback": stack,
                }
                rows.append(row)
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()

    conditions = {}
    condition_names = (
        ("base", "packmonitor")
        if args.condition_prefix == "base"
        else ("bound", "bound_packmonitor")
    )
    for condition in condition_names:
        subset = [row for row in rows if row["condition"] == condition]
        latencies = sorted(row["latency_seconds"] for row in subset)
        conditions[condition] = {
            "n_tasks": len(subset),
            "successful_generations": sum(row["error"] is None for row in subset),
            "install_region_trigger_rate": sum(row["install_region_emitted"] for row in subset) / len(subset),
            "invalid_answer_rate": sum(bool(row["invalid_packages"]) for row in subset) / len(subset),
            "empty_package_rate": sum(row["empty_package_list"] for row in subset) / len(subset),
            "mean_latency_seconds": sum(latencies) / len(latencies),
            "p50_latency_seconds": latencies[len(latencies) // 2],
            "total_decoded_tokens": sum(row["decoded_tokens"] for row in subset),
        }
    summary = {
        "status": "completed_with_minimal_compatibility_patch",
        "official_commit": "8808362e14891fe692b17b8192ed123dff4d64d2",
        "official_grammar_probe": probe,
        "compatibility_patch": "NATATURAL_LANG->NATURAL_LANG only; official worktree unchanged",
        "model_path": args.model_path,
        "delta_dir": str(delta_dir) if delta_dir else "",
        "condition_prefix": args.condition_prefix,
        "registry_path": args.registry,
        "registry_size": len(registry),
        "prompt_ids": list(prompt_ids),
        "max_tokens": args.max_tokens,
        "decoding": "greedy temperature=0; same model/tasks/protocol",
        "model_load_seconds": load_seconds,
        "conditions": conditions,
        "cuda_peak_allocated_gib": torch.cuda.max_memory_allocated() / 2**30 if torch.cuda.is_available() else None,
        "cuda_peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30 if torch.cuda.is_available() else None,
    }
    Path(args.output_summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
