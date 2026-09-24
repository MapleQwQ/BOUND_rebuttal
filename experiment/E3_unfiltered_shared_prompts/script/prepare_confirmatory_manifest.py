#!/usr/bin/env python3
"""构造 E3 确认性未筛选共同集，并审计全部 edit_records 泄漏。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).strip().lower()
    prefixes = (
        "what python packages would be useful in solving the following coding problem:",
        "[task]",
    )
    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix) :].strip()
    value = value.replace("[/task]", " ")
    return re.sub(r"\s+", " ", value).strip()


def token_ngrams(text: str, n: int = 3) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[a-z0-9_.+-]+", normalize(text))
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(left: set, right: set) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def read_jsonl(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--near-candidates", type=Path, required=True)
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--candidate-threshold", type=float, default=0.80)
    parser.add_argument("--exclude-threshold", type=float, default=0.90)
    args = parser.parse_args()

    raw = read_jsonl(args.source)
    prompts = [str(row) if not isinstance(row, dict) else str(row.get("question", row.get("prompt", ""))) for row in raw]
    exclusion_rows: dict[str, dict] = {}
    file_audit = []
    edit_files = sorted(args.repo_root.glob("knowledgeEdit/results/**/edit_records.jsonl"))
    for path in edit_files:
        before = len(exclusion_rows)
        parsed = 0
        try:
            rows = read_jsonl(path)
        except (OSError, json.JSONDecodeError):
            file_audit.append({"path": str(path.relative_to(args.repo_root)), "parsed": 0, "new_unique": 0, "status": "read_error"})
            continue
        for row in rows:
            value = row.get("prompt") or row.get("question")
            if not value:
                continue
            parsed += 1
            key = normalize(str(value))
            exclusion_rows.setdefault(key, {"text": str(value), "sources": []})["sources"].append(str(path.relative_to(args.repo_root)))
        file_audit.append({"path": str(path.relative_to(args.repo_root)), "parsed": parsed, "new_unique": len(exclusion_rows) - before, "status": "ok"})

    exclusion_ngrams = [(key, token_ngrams(info["text"]), info) for key, info in exclusion_rows.items()]
    seen: set[str] = set()
    eligible: list[tuple[int, str]] = []
    exact_removed = 0
    near_removed = 0
    within_duplicate = 0
    candidates = []
    for index, question in enumerate(prompts):
        key = normalize(question)
        if not key:
            continue
        if key in seen:
            within_duplicate += 1
            continue
        seen.add(key)
        if key in exclusion_rows:
            exact_removed += 1
            continue
        grams = token_ngrams(question)
        best_score = 0.0
        best_key = ""
        best_info = None
        for exclusion_key, other_grams, info in exclusion_ngrams:
            # 长度差过大时不可能达到候选阈值，先廉价剪枝。
            small, large = sorted((len(grams), len(other_grams)))
            if large and small / large < args.candidate_threshold:
                continue
            score = jaccard(grams, other_grams)
            if score > best_score:
                best_score, best_key, best_info = score, exclusion_key, info
        if best_score >= args.candidate_threshold:
            decision = "exclude_near_duplicate" if best_score >= args.exclude_threshold else "retain_candidate_review"
            candidates.append(
                {
                    "source_id": index,
                    "score": round(best_score, 6),
                    "decision": decision,
                    "prompt": question,
                    "matched_edit_prompt": best_info["text"] if best_info else best_key,
                    "matched_sources": " | ".join(best_info["sources"] if best_info else []),
                }
            )
            if decision == "exclude_near_duplicate":
                near_removed += 1
                continue
        eligible.append((index, question))

    rng = random.Random(args.seed)
    selected = rng.sample(eligible, args.n)
    selected.sort(key=lambda item: item[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for index, question in selected:
            handle.write(json.dumps({"id": index, "question": question}, ensure_ascii=False) + "\n")
    fieldnames = ["source_id", "score", "decision", "prompt", "matched_edit_prompt", "matched_sources"]
    with args.near_candidates.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)
    with args.audit_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "parsed", "new_unique", "status"])
        writer.writeheader()
        writer.writerows(file_audit)
    audit = {
        "status": "confirmatory_manifest_frozen_before_generation",
        "source": str(args.source),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "seed": args.seed,
        "n": args.n,
        "source_prompts": len(prompts),
        "edit_record_files": len(edit_files),
        "unique_edit_prompts": len(exclusion_rows),
        "exact_removed": exact_removed,
        "near_removed": near_removed,
        "within_pool_exact_duplicates": within_duplicate,
        "lexical_candidate_threshold": args.candidate_threshold,
        "lexical_auto_exclude_threshold": args.exclude_threshold,
        "retained_review_candidates": sum(row["decision"] == "retain_candidate_review" for row in candidates),
        "eligible": len(eligible),
        "selected": len(selected),
        "source_group_status": "unavailable: official dataset does not publish prompt-to-source-package/task mapping",
        "embedding_status": "not_used",
        "warning": "Lexical rules were frozen after preliminary outcomes were known but before confirmatory generations; this is disclosed, not claimed as pristine preregistration.",
    }
    args.audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
