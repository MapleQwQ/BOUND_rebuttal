"""Same-prompt valid-only localization control for E5 experiment 3.

The model, candidate linear modules, first-token convention and gradient
saliency formula match the archived RQ4 full-risk localization run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from knowledgeEdit.package_edit import task_question_from_prompt
from knowledgeEdit.package_edit_utils import chat_message_ids, recommendation_messages
from scripts.run_rq4_top1_localization import collect_linear_params, module_family, module_layer

MODELS = {
    "deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
    "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
    "llama3.1-release": "/data0/shuhanliu/models/llama3.1",
}
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--model", required=True, choices=tuple(MODELS))
    parser.add_argument("--folds", default="ABCD")
    args = parser.parse_args()
    if not args.folds or any(fold not in "ABCD" for fold in args.folds):
        parser.error("folds must be A/B/C/D")
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit(f"GPU {args.gpu} unavailable; refusing CPU fallback")

    out = E5 / "results/03_localization_stability/valid_only" / args.model
    out.mkdir(parents=True, exist_ok=True)
    output = out / "per_prompt.jsonl"
    skipped = out / "skipped_no_valid.jsonl"
    done = set()
    for existing in (output, skipped):
        if not existing.exists():
            continue
        with existing.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                key = (row["fold"], row["prompt_id"])
                if key in done:
                    raise ValueError(f"Duplicate result: {key}")
                done.add(key)
    tokenizer = AutoTokenizer.from_pretrained(MODELS[args.model], trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODELS[args.model], device_map="cuda",
                                                  torch_dtype=torch.bfloat16, trust_remote_code=True)
    model.eval()
    params = collect_linear_params(model)
    sources = {}
    start = time.time()
    for fold in args.folds:
        selected = SOURCE / args.model / f"fold_{fold}/blast_50/selected_task_recommend_cases.jsonl"
        sources[fold] = {"path": str(selected.relative_to(ROOT)), "sha256": sha(selected)}
        records = [json.loads(line) for line in selected.read_text(encoding="utf-8").splitlines()]
        records = [row for row in records if row.get("type") == "task_recommend"]
        for rec in records:
            prompt_id = str(rec.get("id"))
            if (fold, prompt_id) in done:
                continue
            question = task_question_from_prompt(rec.get("language", "Python"), rec["prompt"])
            ids, _ = chat_message_ids(tokenizer,
                                      recommendation_messages(rec.get("language", "Python"), question),
                                      None, "cuda")
            good_ids = sorted({tokenizer(" " + str(pkg), add_special_tokens=False).input_ids[0]
                               for pkg in rec.get("valid_reference", []) or []
                               if tokenizer(" " + str(pkg), add_special_tokens=False).input_ids})
            if not good_ids:
                with skipped.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"model": args.model, "fold": fold, "prompt_id": prompt_id,
                                             "reason": "no_valid_reference"}) + "\n")
                done.add((fold, prompt_id))
                continue
            model.zero_grad(set_to_none=True)
            logits = model(input_ids=ids).logits[:, -1, :]
            logits[:, good_ids].logsumexp(dim=-1).mean().backward()
            scored = []
            for name, weight in params:
                if weight.grad is None:
                    continue
                value = (weight.grad.detach().float() * weight.detach().float()).abs().mean().item()
                scored.append({"module": name, "layer": module_layer(name),
                               "module_family": module_family(name), "score": value})
            scored.sort(key=lambda row: row["score"], reverse=True)
            if not scored:
                raise ValueError(f"No module scores: {args.model}/{fold}/{prompt_id}")
            result = {"model": args.model, "fold": fold, "prompt_id": prompt_id,
                      "n_scored_modules": len(scored), "n_valid_first_tokens": len(good_ids),
                      "scores": scored}
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result) + "\n")
            done.add((fold, prompt_id))
            if len(done) % 25 == 0:
                print(json.dumps({"model": args.model, "n_done": len(done), "elapsed": time.time() - start}),
                      flush=True)
    n_skipped = sum(1 for _ in skipped.open(encoding="utf-8")) if skipped.exists() else 0
    meta = {"status": "complete", "model": args.model, "gpu": args.gpu, "n_prompts": len(done),
            "n_prompts_scored": len(done) - n_skipped, "n_prompts_skipped_no_valid": n_skipped,
            "n_candidate_modules": len(params), "sources": sources, "elapsed_seconds": time.time() - start,
            "objective": "LSE(valid first tokens)", "score": "mean(abs(gradient * weight))"}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
