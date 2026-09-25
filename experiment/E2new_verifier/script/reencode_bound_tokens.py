#!/usr/bin/env python3
"""Count BOUND answer tokens offline with each source model's unchanged tokenizer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from generate_base_timed import MODELS, RESULTS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    args = parser.parse_args()
    model, n_prompts, model_path = MODELS[args.model]
    base_path = RESULTS / f"base_timed_{model}.jsonl"
    base = {}
    for line in base_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            key = str(row["prompt_id"]), int(row["generation"])
            if key in base:
                raise ValueError(f"duplicate Base key {key}")
            base[key] = row
    if len(base) != n_prompts * 5:
        raise ValueError("Base source incomplete")
    paths = [RESULTS / f"bound_timed_{model}_fold_{fold}.jsonl" for fold in "ABCD"]
    if any(not path.exists() for path in paths):
        raise FileNotFoundError("BOUND fold not yet complete")
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            actual = sum(bool(line.strip()) for line in stream)
        if actual != n_prompts * 5:
            raise ValueError(f"incomplete {path}: {actual}/{n_prompts*5}")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    output = RESULTS / f"bound_tokens_reencoded_{model}.jsonl"
    count = 0
    with output.open("w", encoding="utf-8") as downstream:
        for fold, path in zip("ABCD", paths):
            seen = set()
            with path.open(encoding="utf-8") as upstream:
                for line in upstream:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    key = str(row["prompt_id"]), int(row["generation"])
                    if key in seen or key not in base or row["model"] != model or row["fold"] != fold:
                        raise ValueError(f"identity/duplication error {model} {fold} {key}")
                    seen.add(key)
                    answer_tokens = len(tokenizer(row["answer"], add_special_tokens=False).input_ids)
                    base_tokens = int(base[key]["output_tokens_reencoded"])
                    downstream.write(json.dumps({"model": model, "fold": fold, "prompt_id": row["prompt_id"],
                                                 "generation": row["generation"],
                                                 "input_tokens": int(base[key]["input_tokens"]),
                                                 "output_tokens_reencoded": answer_tokens,
                                                 "base_output_tokens_reencoded": base_tokens,
                                                 "delta_output_tokens_vs_base": answer_tokens - base_tokens,
                                                 "extra_llm_tokens_from_verifier": 0}) + "\n")
                    count += 1
            if len(seen) != n_prompts * 5:
                raise ValueError(f"incomplete {model} fold {fold}: {len(seen)}")
    print(json.dumps({"model": model, "records": count, "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()
