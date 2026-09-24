#!/usr/bin/env python3
"""Small-scale E2 verifier-guided one-shot repair (Base and one BOUND fold).

The run is resumable at the (condition, prompt_id) level.  It uses the frozen
PackMonitor PyPI-name file as a deployment snapshot, never a live registry
request.  Remaining invalid names after one repair are explicitly filtered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from getHallucinationPackage.build_edit_examples import check_std_package
from knowledgeEdit.package_edit import gen_chat, load_model
from knowledgeEdit.package_edit_utils import set_lora_enabled, split_recommendation_packages


REPAIR_SYSTEM = """You are a Python dependency recommendation assistant.
Return only a comma-separated package list inside [ANSWER] and [/ANSWER].
A registry verifier rejected some names from a previous answer. Recommend a
complete replacement list using only real PyPI distribution names or Python
standard-library modules. Do not repeat rejected names."""


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", str(name).strip().lower())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(packages: list[str], registry: set[str]) -> tuple[list[str], list[str], list[str]]:
    valid, invalid, stdlib = [], [], []
    for raw in sorted(set(packages)):
        package = normalize(raw)
        if not package:
            continue
        if check_std_package(package):
            stdlib.append(package)
        elif package in registry:
            valid.append(package)
        else:
            invalid.append(package)
    return valid, invalid, stdlib


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--source-eval", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-key", default="deepseekcoder")
    parser.add_argument("--bound-condition", default="bound_fold_A")
    parser.add_argument("--max-prompts", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.max_prompts <= 100:
        raise SystemExit("require 1 <= --max-prompts <= 100")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected_ids = [str(x) for x in manifest["models"][args.model_key]["selected_prompt_ids"]][
        : args.max_prompts
    ]
    source = json.loads(args.source_eval.read_text(encoding="utf-8"))
    rows = {str(row["id"]): row for row in source["details"]}
    registry_values = json.loads(args.registry.read_text(encoding="utf-8"))
    registry = {normalize(x) for x in registry_values}

    completed: set[tuple[str, str]] = set()
    if args.output.exists():
        with args.output.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    old = json.loads(line)
                    completed.add((str(old["condition"]), str(old["prompt_id"])))

    model, tokenizer = load_model(args.model_path, args.adapter_dir)
    for condition, lora_enabled in (("base", False), (args.bound_condition, True)):
        set_lora_enabled(model, lora_enabled)
        for prompt_id in selected_ids:
            if (condition, prompt_id) in completed:
                continue
            row = rows[prompt_id]
            payload = row["baseline"] if condition == "base" else row["edited"]
            initial = payload["trials"][0]
            initial_packages = split_recommendation_packages(initial.get("answer", ""), "Python")
            initial_valid, initial_invalid, initial_stdlib = classify(initial_packages, registry)

            repaired_answer = None
            repaired_packages: list[str] = []
            repair_latency = 0.0
            if initial_invalid:
                feedback = ", ".join(initial_invalid)
                messages = [
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"[TASK]\n{row['question']}\n[/TASK]\n"
                            f"[PREVIOUS_ANSWER]\n{initial.get('answer', '')}\n[/PREVIOUS_ANSWER]\n"
                            f"[REGISTRY_FEEDBACK]\nRejected names: {feedback}\n[/REGISTRY_FEEDBACK]"
                        ),
                    },
                ]
                start = time.perf_counter()
                repaired_answer = gen_chat(
                    model,
                    tokenizer,
                    messages,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                )
                repair_latency = time.perf_counter() - start
                repaired_packages = split_recommendation_packages(repaired_answer, "Python")
                final_candidates = repaired_packages
            else:
                final_candidates = initial_packages

            final_valid, final_invalid, final_stdlib = classify(final_candidates, registry)
            final_filtered = sorted(set(final_valid + final_stdlib))
            if final_invalid:
                terminal = "final_filter"
            elif not final_filtered:
                terminal = "explicit_refusal_or_empty"
            elif initial_invalid:
                terminal = "repair_verified"
            else:
                terminal = "initial_verified"
            append_jsonl(
                args.output,
                {
                    "condition": condition,
                    "prompt_id": row["id"],
                    "question": row["question"],
                    "initial_answer": initial.get("answer", ""),
                    "initial_packages": initial_packages,
                    "initial_valid": initial_valid,
                    "initial_invalid": initial_invalid,
                    "initial_stdlib": initial_stdlib,
                    "repair_attempted": bool(initial_invalid),
                    "repair_answer": repaired_answer,
                    "repair_packages": repaired_packages,
                    "final_valid": final_valid,
                    "final_invalid_before_terminal_policy": final_invalid,
                    "final_stdlib": final_stdlib,
                    "final_filtered_packages": final_filtered,
                    "terminal_state": terminal,
                    "repair_latency_seconds": repair_latency,
                    "registry_source": str(args.registry),
                    "registry_sha256": file_sha256(args.registry),
                    "registry_size": len(registry),
                    "generation_policy": "greedy; max one repair; final_filter on remaining invalid",
                },
            )
            print(json.dumps({"condition": condition, "prompt_id": prompt_id, "terminal": terminal}), flush=True)


if __name__ == "__main__":
    main()
