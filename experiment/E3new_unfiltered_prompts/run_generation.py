from __future__ import annotations

"""E3new generator with a read-only cache of already audited PyPI release dates."""

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from knowledgeEdit.package_edit import (  # noqa: E402
    baseline_for_prompt,
    generate_recommendation_trials,
    infer_model_cutoff,
    load_baseline_response_index,
    load_model,
    summarize_eval_pairs,
)
from knowledgeEdit.package_edit_utils import read_eval_questions, set_gpu, write_json  # noqa: E402


class DeferredReleaseCache(dict):
    """Avoid inference-time registry I/O; labels are rebuilt after all generations."""

    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return self.get(key)


def apply_direct_delta(model, delta_file: Path) -> None:
    payload = torch.load(delta_file, map_location="cpu")
    deltas = payload.get("deltas", {})
    modules = dict(model.named_modules())
    missing = [name for name in deltas if name not in modules]
    if missing:
        raise RuntimeError(f"delta modules missing from model: {missing[:5]}")
    with torch.no_grad():
        for name, delta in deltas.items():
            weight = modules[name].weight
            weight.add_(delta.to(device=weight.device, dtype=weight.dtype))


def load_direct_model(model_path: Path, delta_dir: Path):
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="cuda",
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        trust_remote_code=True,
    )
    apply_direct_delta(model, delta_dir / "direct_weight_delta.pt")
    model.eval()
    return model, tokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--delta-dir", default="")
    parser.add_argument("--adapter-type", choices=["base", "blast", "full", "direct"], required=True)
    parser.add_argument("--prompts-file", required=True)
    parser.add_argument("--baseline-response-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--gpu", default="auto")
    parser.add_argument("--num-generations", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--model-cutoff", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--release-cache-jsonl", default="", help="Preload dated PyPI JSON API release records only")
    parser.add_argument("--defer-release-lookups", action="store_true", help="Generate without PyPI I/O; valid/hallucinated fields are provisional")
    args = parser.parse_args()

    set_gpu(args.gpu)
    model_path = Path(args.model_path)
    delta_dir = Path(args.delta_dir) if args.delta_dir else None
    if args.adapter_type == "base":
        model, tokenizer = load_model(model_path, None)
    elif args.adapter_type in {"blast", "full"}:
        if delta_dir is None:
            parser.error("--delta-dir is required for blast/full adapters")
        model, tokenizer = load_model(model_path, delta_dir)
    else:
        if delta_dir is None:
            parser.error("--delta-dir is required for direct adapters")
        model, tokenizer = load_direct_model(model_path, delta_dir)
    # Reset after model loading so Base/BOUND conditions can share a reproducible
    # sampling stream even if their loading paths consume different RNG states.
    set_seed(args.seed)

    prompts_file = Path(args.prompts_file)
    questions = read_eval_questions(prompts_file, 0, 0)
    baseline_index = load_baseline_response_index(args.baseline_response_file)
    cutoff = infer_model_cutoff(model_path, args.model_cutoff)
    release_cache: dict = {}
    if args.release_cache_jsonl:
        for line in Path(args.release_cache_jsonl).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("status") != "dated" or not item.get("first_upload_utc"):
                continue
            release_cache[str(item["name"])] = dt.datetime.fromisoformat(str(item["first_upload_utc"]).replace("Z", "+00:00")).replace(tzinfo=None)
        print(f"preloaded {len(release_cache)} dated PyPI JSON API records", flush=True)
    if args.defer_release_lookups:
        release_cache = DeferredReleaseCache(release_cache)
        print("PyPI lookups deferred; provisional labels must be rebuilt before analysis", flush=True)
    details = []
    out_file = Path(args.output_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    detail_file = out_file.with_suffix(".details.jsonl")
    done_keys = set()
    if detail_file.exists():
        with detail_file.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                done_keys.add(str(row.get("id")))
                details.append(row)

    with detail_file.open("a", encoding="utf-8") as f:
        for prompt_id, question in tqdm(questions, desc=f"eval {out_file.parent.name}/{out_file.stem}"):
            key = str(prompt_id)
            if key in done_keys:
                continue
            generation_seeds = [
                int.from_bytes(
                    hashlib.sha256(f"{args.seed}|{prompt_id}|{generation_id}".encode()).digest()[:4],
                    "big",
                )
                for generation_id in range(args.num_generations)
            ]
            trials = generate_recommendation_trials(
                model,
                tokenizer,
                question,
                "Python",
                cutoff,
                release_cache,
                num_generations=args.num_generations,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
                top_k=args.top_k,
                top_p=args.top_p,
                generation_seeds=generation_seeds,
            )
            row = {
                "id": prompt_id,
                "question": question,
                "baseline": baseline_for_prompt(baseline_index, prompt_id, question),
                "edited": {"summary": summarize_eval_pairs([{"baseline": baseline_for_prompt(baseline_index, prompt_id, question), "edited": {"trials": trials}}]) if False else {}, "trials": trials},
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            details.append(row)

    summary = summarize_eval_pairs(details)
    write_json(
        out_file,
        {
            "summary": summary,
            "details_file": str(detail_file),
            "n_prompts": len(questions),
            "adapter_type": args.adapter_type,
            "delta_dir": str(delta_dir) if delta_dir else "",
            "prompts_file": str(prompts_file),
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
