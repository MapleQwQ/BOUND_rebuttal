#!/usr/bin/env python3
"""Time BOUND generation and package extraction, without evaluation-time PyPI calls."""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import set_seed

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from knowledgeEdit.package_edit import gen_chat, load_model
from knowledgeEdit.package_edit_utils import recommendation_messages, split_recommendation_packages
from generate_base_timed import MODELS, RESULTS, SOURCE, file_sha256, generation_seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    parser.add_argument("--fold", choices=tuple("ABCD"), required=True)
    parser.add_argument("--gpu", type=int, required=True)
    parser.add_argument("--max-prompts", type=int, default=0)
    args = parser.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit("Set CUDA_VISIBLE_DEVICES to exactly one GPU")
    key, expected_n, model_path = MODELS[args.model]
    delta_dir = SOURCE / key / f"fold_{args.fold}/blast_50"
    source = delta_dir / "eval_unseen_prompts.json"
    tasks = json.loads(source.read_text(encoding="utf-8"))["details"]
    if len(tasks) != expected_n or len({str(row["id"]) for row in tasks}) != expected_n:
        raise ValueError(f"Unexpected source size or duplicate IDs: {source}")
    if args.max_prompts < 0:
        parser.error("max-prompts must be nonnegative")
    if args.max_prompts:
        tasks = tasks[: args.max_prompts]
    suffix = f"_pilot{args.max_prompts}" if args.max_prompts else ""
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / f"bound_timed_{key}_fold_{args.fold}{suffix}.jsonl"
    lock_path = output.with_suffix(output.suffix + ".lock")
    lock_stream = lock_path.open("a", encoding="utf-8")
    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
    completed = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            marker = str(row["prompt_id"]), int(row["generation"])
            if marker in completed:
                raise ValueError(f"Duplicate output key: {marker}")
            completed.add(marker)
    if len(completed) == len(tasks) * 5:
        print(f"already complete {key} fold {args.fold}", flush=True)
        return
    print(f"loading {key} fold {args.fold} GPU {args.gpu}", flush=True)
    load_start = time.perf_counter()
    model, tokenizer = load_model(Path(model_path), delta_dir)
    load_seconds = time.perf_counter() - load_start
    set_seed(20260924)
    _ = gen_chat(model, tokenizer, recommendation_messages("Python", tasks[0]["question"]), 16,
                 do_sample=True, temperature=0.7, top_p=0.9, top_k=40)
    torch.cuda.synchronize()
    meta = {"model": key, "fold": args.fold, "gpu_physical": args.gpu,
            "model_path": model_path, "delta_dir": str(delta_dir), "source": str(source),
            "source_sha256": file_sha256(source), "n_prompts": len(tasks),
            "generations_per_prompt": 5, "load_seconds": load_seconds,
            "timing_scope": "generation: chat-template/tokenization/model.generate/decode; extraction: split_recommendation_packages; both exclude warmup, load, output I/O and registry labels",
            "sampler": {"do_sample": True, "temperature": 0.7, "top_p": 0.9, "top_k": 40, "max_new_tokens": 128},
            "seed_schedule": "E2new-base-20260924:{model}:{prompt_id}:{trial}",
            "started_utc": datetime.now(timezone.utc).isoformat()}
    metadata = RESULTS / f"bound_timed_{key}_fold_{args.fold}{suffix}_metadata.json"
    metadata.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    added = 0
    with output.open("a", encoding="utf-8") as stream:
        for task in tasks:
            prompt_id = str(task["id"])
            messages = recommendation_messages("Python", task["question"])
            for trial in range(5):
                marker = prompt_id, trial
                if marker in completed:
                    continue
                seed = generation_seed(key, prompt_id, trial)
                set_seed(seed)
                torch.cuda.synchronize()
                start = time.perf_counter()
                answer = gen_chat(model, tokenizer, messages, 128, do_sample=True,
                                  temperature=0.7, top_p=0.9, top_k=40)
                torch.cuda.synchronize()
                generation_seconds = time.perf_counter() - start
                start = time.perf_counter()
                packages = split_recommendation_packages(answer, "Python")
                extraction_seconds = time.perf_counter() - start
                row = {"model": key, "fold": args.fold, "prompt_id": task["id"],
                       "generation": trial, "seed": seed, "answer": answer,
                       "packages": packages, "generation_seconds": generation_seconds,
                       "extraction_seconds": extraction_seconds,
                       "delivery_seconds": generation_seconds + extraction_seconds,
                       "measured_utc": datetime.now(timezone.utc).isoformat()}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                added += 1
                if added % 100 == 0:
                    print(f"{datetime.now(timezone.utc).isoformat()} {key} fold {args.fold} "
                          f"new={added} total={len(completed)+added}/{len(tasks)*5}", flush=True)
    print(f"completed {key} fold {args.fold}: {len(completed)+added}/{len(tasks)*5}", flush=True)


if __name__ == "__main__":
    main()
