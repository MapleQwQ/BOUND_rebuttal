#!/usr/bin/env python3
"""Copy only protocol-compatible E3 outputs into resumable new E3 detail files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "BOUND_rebuttal/experiment/E3_unfiltered_shared_prompts/results"
MODELS = ("deepseekcoder", "qwen3", "llama31")
FOLDS = "ABCD"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def expected_seed(prompt_id: int, generation: int) -> int:
    payload = f"20260926|{prompt_id}|{generation}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, required=True)
    parser.add_argument("--top-p", type=float, required=True)
    args = parser.parse_args()
    if args.max_new_tokens != 64 or args.top_p != 0.95:
        print("Old E3 outputs used max_new_tokens=64 and top_p=0.95; no compatible generations to reuse.")
        return
    sample = {int(row["id"]): row["question"] for row in read_jsonl(args.manifest)}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for model in MODELS:
        for fold in FOLDS:
            source = OLD / f"confirm200_{model}_fold{fold}_seed20260926.details.jsonl"
            selected = []
            for row in read_jsonl(source):
                prompt_id = int(row["id"])
                if prompt_id not in sample:
                    continue
                if row["question"] != sample[prompt_id]:
                    raise ValueError(f"prompt mismatch in {source}: {prompt_id}")
                trials = row["edited"]["trials"]
                if len(trials) != 5 or any(trial.get("seed") != expected_seed(prompt_id, generation) for generation, trial in enumerate(trials)):
                    raise ValueError(f"seed/trial mismatch in {source}: {prompt_id}")
                selected.append(row)
            output = args.output_dir / f"{model}_fold{fold}.details.jsonl"
            if output.exists():
                raise FileExistsError(f"refusing to overwrite existing details: {output}")
            output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected), encoding="utf-8")
            counts[f"{model}_fold{fold}"] = len(selected)
    report = {"source": str(OLD), "max_new_tokens": 64, "top_p": 0.95, "seed": 20260926, "counts": counts}
    (args.output_dir.parent / "reuse_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
