"""Common-generation-seed RQ3 re-evaluation for the two changed-module DeepSeek folds."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
PYTHON = "/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python"
MODEL = "deepseekcoder"
MODEL_PATH = Path("/data0/shuhanliu/models/deepseekcoder")
OUTPUT = E5 / "results/02_risk_score/common_seed_eval"
CONDITIONS = ("full_risk", "hall_only")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_for(prompt_id: str, generation: int) -> int:
    digest = hashlib.sha256(f"E5-risk/{prompt_id}/{generation}".encode()).hexdigest()
    return 42 + int(digest[:8], 16) % 1_000_000


def cached_dates() -> dict:
    raw = json.loads((ROOT / "knowledgeEdit/results/rq2_cross_task_20260611/rq2_pypi_release_cache.json").read_text())
    other = json.loads((ROOT / "knowledgeEdit/results/ccfa_supplement_20260604_final/pypi_first_release_cache.json").read_text())
    for key, value in other.items():
        if raw.get(key) is None and value:
            raw[key] = value
    result = {}
    for key, value in raw.items():
        result[key] = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None) if value else None
    return result


def one(gpu: str, fold: str, condition: str, max_prompts: int) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu
    sys.path.insert(0, str(ROOT))
    import torch
    from knowledgeEdit.package_edit import (generate_recommendation_trials, load_model,
                                            read_eval_questions, summarize_trials)

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit(f"GPU {gpu} unavailable; refusing CPU fallback")
    delta = (ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605/deepseekcoder" / f"fold_{fold}/blast_50"
             if condition == "full_risk" else
             ROOT / "knowledgeEdit/results/rq3_ablation_20260613/deepseekcoder" / f"fold_{fold}/wo_valid_anchor")
    test100 = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611/deepseekcoder/test100/rq2_test100.jsonl"
    case = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611/deepseekcoder/Base" / f"fold_{fold}/test100_case_repeat5/case.json"
    cutoff = datetime.fromisoformat(json.loads(case.read_text(encoding="utf-8"))["model_cutoff"])
    folder = OUTPUT / ("smoke" if max_prompts else "full") / f"fold_{fold}" / condition
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "per_prompt.jsonl"
    meta = folder / "metadata.json"
    if meta.exists():
        complete = json.loads(meta.read_text(encoding="utf-8"))
        if complete.get("status") == "complete":
            return
        raise ValueError(f"Incomplete metadata: {meta}")
    prompts = read_eval_questions(test100, 0, 100)
    if max_prompts:
        prompts = prompts[:max_prompts]
    completed = set()
    if output.exists():
        with output.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if str(row["prompt_id"]) in completed:
                    raise ValueError(f"Duplicate prompt: {row['prompt_id']}")
                completed.add(str(row["prompt_id"]))
    release_cache = cached_dates()
    pre_cached = set(release_cache)
    started = time.time()
    model, tokenizer = load_model(MODEL_PATH, delta)
    for prompt_id, question in prompts:
        key = str(prompt_id)
        if key in completed:
            continue
        trials = generate_recommendation_trials(
            model, tokenizer, question, "Python", cutoff, release_cache,
            num_generations=5, max_new_tokens=64, temperature=0.7, top_k=40, top_p=0.95,
            generation_seeds=[seed_for(key, i) for i in range(5)],
        )
        record = {"prompt_id": key, "question": question, "summary": summarize_trials(trials), "trials": trials}
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        completed.add(key)
        if len(completed) % 10 == 0:
            print(json.dumps({"fold": fold, "condition": condition, "n_done": len(completed),
                              "elapsed_seconds": time.time() - started}), flush=True)
    extra = {key: value.isoformat() if value else None for key, value in release_cache.items() if key not in pre_cached}
    (folder / "release_cache_additions.json").write_text(json.dumps(extra, indent=2) + "\n", encoding="utf-8")
    result = {"status": "complete", "model": MODEL, "fold": fold, "condition": condition,
              "gpu": gpu, "n_prompts": len(completed), "n_generations_per_prompt": 5,
              "elapsed_seconds": time.time() - started, "adapter_sha256": sha(delta / "blast_delta.pt"),
              "test100_sha256": sha(test100), "case_sha256": sha(case),
              "cutoff": cutoff.isoformat(), "seed_rule": "SHA256(E5-risk/{prompt_id}/{generation})",
              "n_release_cache_additions": len(extra)}
    meta.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)


def queue(gpu: str) -> None:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for fold in "BD":
        for condition in CONDITIONS:
            cmd = [PYTHON, __file__, "--gpu", gpu, "--fold", fold, "--condition", condition, "--one"]
            folder = OUTPUT / "full" / f"fold_{fold}" / condition
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "queue.log").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": "start", "command": cmd, "utc_epoch": time.time()}) + "\n")
                handle.flush()
                proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                handle.write(json.dumps({"event": "end", "returncode": proc.returncode,
                                         "utc_epoch": time.time()}) + "\n")
            print(json.dumps({"fold": fold, "condition": condition, "returncode": proc.returncode}), flush=True)
            if proc.returncode:
                raise SystemExit(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--fold", choices=tuple("BD"))
    parser.add_argument("--condition", choices=CONDITIONS)
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--one", action="store_true")
    args = parser.parse_args()
    if args.one:
        if not args.fold or not args.condition:
            parser.error("--one needs fold and condition")
        one(args.gpu, args.fold, args.condition, args.max_prompts)
    else:
        queue(args.gpu)


if __name__ == "__main__":
    main()
