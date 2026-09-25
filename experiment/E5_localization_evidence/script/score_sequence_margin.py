"""Teacher-forced complete package-name scores on E5 candidate manifests.

Only physical GPUs 2/3. Both original RQ2 labels and registry-screened sensitivity are supported.
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
from knowledgeEdit.package_edit_utils import apply_chat_template, inject_lora, recommendation_messages, set_lora_enabled

MODEL_PATHS = {
    "deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
    "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
    "llama3.1-release": "/data0/shuhanliu/models/llama3.1",
}


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_ids(tokenizer, question: str):
    messages = recommendation_messages("Python", question)
    encoded = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt")
    prefix = encoded["input_ids"] if hasattr(encoded, "keys") and "input_ids" in encoded else encoded
    answer = tokenizer("[ANSWER]\n", add_special_tokens=False, return_tensors="pt").input_ids
    return torch.cat([prefix, answer], dim=1).to("cuda")


@torch.inference_mode()
def score(model, tokenizer, prefix, package: str, leading_space: bool = False):
    suffix = tokenizer((" " if leading_space else "") + package,
                       add_special_tokens=False, return_tensors="pt").input_ids.to("cuda")
    if suffix.shape[1] == 0:
        raise ValueError(f"Empty tokenization: {package}")
    full = torch.cat([prefix, suffix], dim=1)
    logits = model(input_ids=full).logits[0, prefix.shape[1] - 1 : -1].float()
    token_logprobs = torch.log_softmax(logits, dim=-1).gather(1, suffix[0, :, None]).squeeze(1)
    values = token_logprobs.cpu().tolist()
    return {"n_tokens": len(values), "token_ids": suffix[0].cpu().tolist(),
            "token_logprobs": values, "sum_logprob": float(sum(values)),
            "mean_logprob": float(sum(values) / len(values))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", required=True, choices=("2", "3"))
    parser.add_argument("--model", required=True, choices=tuple(MODEL_PATHS))
    parser.add_argument("--fold", required=True, choices=tuple("ABCD"))
    parser.add_argument("--max-prompts", type=int, default=0)
    parser.add_argument("--candidate-manifest", choices=("preliminary", "registry_screened"), default="registry_screened")
    parser.add_argument("--leading-space", action="store_true")
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise SystemExit(f"GPU {args.gpu} is not visible; refusing CPU fallback")
    manifest = E5 / "results/04_sequence_margin" / f"candidate_manifest_{args.candidate_manifest}.jsonl"
    candidates = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()
                  if line.strip() and json.loads(line)["model"] == args.model]
    if len(candidates) != 100:
        raise ValueError(f"Expected 100 prompts: {args.model}, found {len(candidates)}")
    candidates = [row for row in candidates if row["valid_candidates"] or row["hallucinated_candidates"]]
    if args.max_prompts:
        candidates = candidates[: args.max_prompts]
    variant = ("smoke_" if args.max_prompts else "scores_") + args.candidate_manifest
    if args.leading_space:
        variant += "_leading_space"
    out = E5 / "results/04_sequence_margin" / variant / args.model / f"fold_{args.fold}"
    out.mkdir(parents=True, exist_ok=True)
    result_file = out / "per_candidate.jsonl"
    meta_file = out / "metadata.json"
    if result_file.exists() or meta_file.exists():
        raise FileExistsError(f"Output exists; inspect before rerunning: {out}")
    adapter = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / args.model / f"fold_{args.fold}" / "blast_50"
    cfg = json.loads((adapter / "blast_config.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATHS[args.model], trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATHS[args.model], device_map="cuda",
                                                  torch_dtype=torch.bfloat16, trust_remote_code=True)
    model.eval()
    targets = [name.strip() for name in cfg["resolved_target_modules"].split(",") if name.strip()]
    edited = inject_lora(model, targets, int(cfg["rank"]), float(cfg["alpha"]), 0.0)
    state = torch.load(adapter / "blast_delta.pt", map_location="cpu", weights_only=True)
    incompatible = model.load_state_dict(state, strict=False)
    if incompatible.unexpected_keys or len(edited) != int(cfg["n_edited_modules"]):
        raise ValueError(f"Adapter mismatch: {incompatible.unexpected_keys}")
    start = time.time()
    n = 0
    with result_file.open("w", encoding="utf-8") as handle:
        for row in candidates:
            prefix = context_ids(tokenizer, row["question"])
            for condition, enabled in (("Base", False), ("BOUND", True)):
                set_lora_enabled(model, enabled)
                for label, names in (("valid", row["valid_candidates"]), ("hallucinated", row["hallucinated_candidates"])):
                    for name in names:
                        record = {"model": args.model, "fold": args.fold, "prompt_id": row["prompt_id"],
                                  "condition": condition, "label": label, "package": name,
                                  **score(model, tokenizer, prefix, name, args.leading_space)}
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        n += 1
            handle.flush()
    meta = {"status": "provisional_historical_labels", "model": args.model, "fold": args.fold,
            "gpu": args.gpu, "n_prompts": len(candidates), "n_candidate_scores": n,
            "elapsed_seconds": time.time() - start, "candidate_manifest_sha256": sha(manifest),
            "adapter_config_sha256": sha(adapter / "blast_config.json"),
            "adapter_delta_sha256": sha(adapter / "blast_delta.pt"),
            "model_path": MODEL_PATHS[args.model], "answer_prefix": "[ANSWER]\n",
            "candidate_presentation": "normalized package name with leading space" if args.leading_space
                                      else "normalized package name without leading space"}
    meta_file.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
