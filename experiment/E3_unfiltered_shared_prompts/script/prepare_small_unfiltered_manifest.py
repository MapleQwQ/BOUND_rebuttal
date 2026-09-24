#!/usr/bin/env python3
"""构造 E3 小规模简单随机 manifest；仅用于先行实验，不替代最终泄漏审计。"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    prefixes = [
        "what python packages would be useful in solving the following coding problem:",
        "[task]",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    text = text.replace("[/task]", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_json_lines(path: Path) -> list:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def collect_exclusions() -> tuple[set[str], dict[str, int]]:
    excluded: set[str] = set()
    counts: dict[str, int] = {}
    patterns = [
        "knowledgeEdit/results/robust_nonedit_highrisk_20260605/*/fold_*/edit_records.jsonl",
        "getHallucinationPackage/result/*/LLM_LY_edits*.jsonl",
    ]
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            before = len(excluded)
            try:
                rows = read_json_lines(path)
            except (OSError, json.JSONDecodeError):
                continue
            for row in rows:
                for key in ("question", "prompt"):
                    value = row.get(key)
                    if value:
                        excluded.add(normalize(str(value)))
            counts[str(path.relative_to(ROOT))] = len(excluded) - before
    return excluded, counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260923)
    args = parser.parse_args()

    source = Path(args.source)
    raw_rows = read_json_lines(source)
    prompts = [str(row) if not isinstance(row, dict) else str(row.get("question", row.get("prompt", ""))) for row in raw_rows]
    exclusions, sources = collect_exclusions()

    seen: set[str] = set()
    eligible = []
    excluded_overlap = 0
    duplicate_count = 0
    for index, question in enumerate(prompts):
        key = normalize(question)
        if not key:
            continue
        if key in exclusions:
            excluded_overlap += 1
            continue
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        eligible.append((index, question))

    rng = random.Random(args.seed)
    selected = rng.sample(eligible, min(args.n, len(eligible)))
    selected.sort(key=lambda item: item[0])
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for index, question in selected:
            handle.write(json.dumps({"id": index, "question": question}, ensure_ascii=False) + "\n")

    audit = {
        "status": "small_scale_preliminary",
        "warning": "仅完成 exact/normalized-exact exclusion；正式 E3 仍需 source-group 与 lexical near-duplicate 审计",
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "seed": args.seed,
        "requested_n": args.n,
        "source_prompts": len(prompts),
        "normalized_exclusion_keys": len(exclusions),
        "excluded_exact_overlap": excluded_overlap,
        "within_pool_exact_duplicates": duplicate_count,
        "eligible": len(eligible),
        "selected": len(selected),
        "exclusion_sources": sources,
    }
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
