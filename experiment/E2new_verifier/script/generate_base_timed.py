#!/usr/bin/env python3
"""Fresh, timed Base generations for the full original unseen high-risk set.

Run with CUDA_VISIBLE_DEVICES set to one physical GPU. Resumes by prompt/trial.
The package recommendation template and sampler come from knowledgeEdit.
"""

from __future__ import annotations

import argparse
import hashlib
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
from knowledgeEdit.package_edit_utils import apply_chat_template, recommendation_messages, split_recommendation_packages

SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
RESULTS = Path(__file__).resolve().parents[1] / "results"
MODELS = {
    "deepseekcoder": ("deepseekcoder", 541, "/data0/shuhanliu/models/deepseekcoder"),
    "qwen3-release": ("qwen3-release", 409, "/data0/shuhanliu/models/qwen3-8B"),
    "llama3.1-release": ("llama3.1-release", 934, "/data0/shuhanliu/models/llama3.1"),
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generation_seed(model: str, prompt_id: str, trial: int) -> int:
    # Stable per prompt/trial, independent of process shard or resume position.
    material = f"E2new-base-20260924:{model}:{prompt_id}:{trial}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    parser.add_argument("--gpu", type=int, required=True, help="Physical GPU index for audit only")
    parser.add_argument("--max-prompts", type=int, default=0, help="0 means full set; smoke uses a separate output suffix")
    args = parser.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit("Set CUDA_VISIBLE_DEVICES to exactly one available GPU")
    if args.max_prompts < 0:
        parser.error("max-prompts must be >= 0")
    key, expected_n, model_path = MODELS[args.model]
    source = SOURCE / key / "fold_A/blast_50/eval_unseen_prompts.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    tasks = data["details"]
    if len(tasks) != expected_n or len({str(x["id"]) for x in tasks}) != expected_n:
        raise ValueError(f"unexpected source count: {args.model} {len(tasks)}")
    if args.max_prompts:
        tasks = tasks[: args.max_prompts]
    suffix = f"_smoke{args.max_prompts}" if args.max_prompts else ""
    RESULTS.mkdir(exist_ok=True)
    output = RESULTS / f"base_timed_{args.model}{suffix}.jsonl"
    existing = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                marker = str(row["prompt_id"]), int(row["generation"])
                if marker in existing:
                    raise ValueError(f"duplicate output {args.model} {marker}")
                existing.add(marker)
    run_info = {"model": args.model, "gpu_physical": args.gpu, "device_name": torch.cuda.get_device_name(0),
                "model_path": model_path, "source": str(source), "source_sha256": file_sha256(source),
                "task_count": len(tasks), "generations_per_task": 5,
                "sampler": {"do_sample": True, "temperature": 0.7, "top_p": 0.9,
                            "top_k": 40, "max_new_tokens": 128},
                "torch_version": torch.__version__, "started_utc": datetime.now(timezone.utc).isoformat(),
                "timing_scope": "chat template + tokenization + model.generate + decode; synchronized GPU",
                "warmup": "first prompt, seed 20260924, discarded"}
    metadata = RESULTS / f"base_timed_{args.model}{suffix}_metadata.json"
    if not metadata.exists():
        metadata.write_text(json.dumps(run_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"loading {args.model} on physical GPU {args.gpu}", flush=True)
    load_start = time.perf_counter()
    model, tokenizer = load_model(Path(model_path), None)
    load_seconds = time.perf_counter() - load_start
    print(f"loaded {args.model} in {load_seconds:.2f}s", flush=True)
    # Warm GPU kernels once, outside recorded answer timings.
    set_seed(20260924)
    _ = gen_chat(model, tokenizer, recommendation_messages("Python", tasks[0]["question"]), 16,
                 do_sample=True, temperature=0.7, top_p=0.9, top_k=40)
    torch.cuda.synchronize()
    added = 0
    with output.open("a", encoding="utf-8") as stream:
        for task in tasks:
            prompt_id = str(task["id"])
            messages = recommendation_messages("Python", task["question"])
            for trial in range(5):
                marker = prompt_id, trial
                if marker in existing:
                    continue
                seed = generation_seed(args.model, prompt_id, trial)
                set_seed(seed)
                torch.cuda.synchronize()
                start = time.perf_counter()
                answer = gen_chat(model, tokenizer, messages, 128,
                                  do_sample=True, temperature=0.7, top_p=0.9, top_k=40)
                torch.cuda.synchronize()
                generate_seconds = time.perf_counter() - start
                packages = split_recommendation_packages(answer, "Python")
                encoded = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt")
                input_ids = encoded["input_ids"] if hasattr(encoded, "keys") and "input_ids" in encoded else encoded
                record = {"model": args.model, "prompt_id": task["id"], "question": task["question"],
                          "generation": trial, "seed": seed, "answer": answer, "packages": packages,
                          "input_tokens": int(input_ids.shape[-1]),
                          "output_tokens_reencoded": len(tokenizer(answer, add_special_tokens=False).input_ids),
                          "base_generation_seconds": generate_seconds,
                          "generated_utc": datetime.now(timezone.utc).isoformat()}
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                added += 1
                if added % 50 == 0:
                    print(f"{datetime.now(timezone.utc).isoformat()} {args.model} new={added} total={len(existing)+added}/{len(tasks)*5}", flush=True)
    print(f"completed {args.model}: {len(existing)+added}/{len(tasks)*5}", flush=True)


if __name__ == "__main__":
    main()
