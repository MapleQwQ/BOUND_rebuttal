#!/usr/bin/env python3
"""Freeze an unfiltered prompt sample, excluding edited and optionally prior prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    for prefix in (
        "what python packages would be useful in solving the following coding problem:",
        "[task]",
    ):
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
    return re.sub(r"\s+", " ", value.replace("[/task]", " ")).strip()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--exclude-manifest", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = read_jsonl(args.source)
    edit_files = sorted(args.repo.glob("knowledgeEdit/results/**/edit_records.jsonl"))
    edit_keys: set[str] = set()
    for path in edit_files:
        for row in read_jsonl(path):
            value = row.get("prompt") or row.get("question")
            if value:
                edit_keys.add(normalize(str(value)))

    seen: set[str] = set()
    eligible = []
    duplicates = edited = 0
    for source_id, row in enumerate(source):
        question = str(row.get("question", row.get("prompt", ""))) if isinstance(row, dict) else str(row)
        key = normalize(question)
        if not key or key in seen:
            duplicates += 1
            continue
        seen.add(key)
        if key in edit_keys:
            edited += 1
            continue
        eligible.append({"id": source_id, "question": question})
    excluded_ids: set[int] = set()
    excluded_keys: set[str] = set()
    if args.exclude_manifest:
        previous = read_jsonl(args.exclude_manifest)
        excluded_ids = {int(row["id"]) for row in previous}
        excluded_keys = {normalize(row["question"]) for row in previous}
        eligible = [row for row in eligible if row["id"] not in excluded_ids and normalize(row["question"]) not in excluded_keys]
    if len(eligible) < args.n:
        raise ValueError(f"only {len(eligible)} eligible prompts for n={args.n}")

    sample = sorted(random.Random(args.seed).sample(eligible, args.n), key=lambda row: row["id"])
    baseline_paths = {
        "deepseekcoder": args.repo / "getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl",
        "qwen3": args.repo / "getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl",
        "llama31": args.repo / "getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl",
    }
    sampled_ids = {row["id"] for row in sample}
    risk = defaultdict(lambda: defaultdict(list))
    for model, path in baseline_paths.items():
        for row in read_jsonl(path):
            prompt_id = int(row["id"])
            if prompt_id in sampled_ids:
                risk[prompt_id][model].append(bool(row.get("hallucinated")))
    for row in sample:
        for model in baseline_paths:
            values = risk[row["id"]][model]
            if len(values) != 5:
                raise ValueError(f"historical Base missing {model}/{row['id']}: {len(values)} trials")
            count = sum(values)
            row[f"{model}_historical_hallucination_count"] = count
            row[f"{model}_risk"] = "high" if count >= 3 else "low" if count else "clean"

    manifest = args.output_dir / f"sample{args.n}_manifest.jsonl"
    manifest.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sample), encoding="utf-8")
    audit = {
        "source": str(args.source),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "source_records": len(source),
        "edit_record_files": len(edit_files),
        "unique_edit_keys": len(edit_keys),
        "within_pool_duplicate_or_empty": duplicates,
        "edited_overlap_removed": edited,
        "eligible": len(eligible),
        "sample_n": len(sample),
        "sample_seed": args.seed,
        "excluded_manifest": str(args.exclude_manifest) if args.exclude_manifest else None,
        "excluded_manifest_sha256": hashlib.sha256(args.exclude_manifest.read_bytes()).hexdigest() if args.exclude_manifest else None,
        "excluded_prior_ids": len(excluded_ids),
        "excluded_prior_normalized_questions": len(excluded_keys),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "historical_risk_counts": {
            model: {risk_name: sum(row[f"{model}_risk"] == risk_name for row in sample) for risk_name in ("clean", "low", "high")}
            for model in baseline_paths
        },
        "baseline_files": {model: str(path) for model, path in baseline_paths.items()},
        "selection": "simple random sample without replacement from globally edit-excluded unique prompts; no risk quota",
    }
    (args.output_dir / "manifest_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
