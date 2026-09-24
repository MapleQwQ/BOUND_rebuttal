#!/usr/bin/env python3
"""构造 E1 双盲小试标清单；盲键默认写入 /tmp，标注完成前不公开。"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--blind-key", default="/tmp/e1_pilot_blind_key.json")
    parser.add_argument("--name", default="pilot")
    parser.add_argument("--prompts", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--exclude-prompt-manifest", default="")
    args = parser.parse_args()

    source = Path(args.input)
    payload = json.loads(source.read_text(encoding="utf-8"))
    details = list(payload["details"])
    rng = random.Random(args.seed)
    excluded_ids: set[str] = set()
    if args.exclude_prompt_manifest:
        with Path(args.exclude_prompt_manifest).open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    excluded_ids.add(str(json.loads(line)["prompt_id"]))
    eligible = [row for row in details if str(row["id"]) not in excluded_ids]
    selected = rng.sample(eligible, min(args.prompts, len(eligible)))

    prompt_rows: list[dict] = []
    answer_rows: list[dict] = []
    blind_key: list[dict] = []
    for prompt_order, row in enumerate(selected):
        prompt_id = str(row["id"])
        question = str(row["question"])
        prompt_rows.append({"prompt_id": prompt_id, "question": question})
        candidates = []
        for condition in ("baseline", "edited"):
            trials = row[condition]["trials"]
            if not trials:
                continue
            trial = trials[0]
            candidates.append((condition, trial))
        rng.shuffle(candidates)
        for answer_order, (condition, trial) in enumerate(candidates):
            digest = hashlib.sha256(
                f"{args.seed}|{prompt_id}|{answer_order}|{condition}".encode()
            ).hexdigest()[:12]
            blind_id = f"E1P-{prompt_order:02d}-{digest}"
            answer_rows.append(
                {
                    "blind_answer_id": blind_id,
                    "prompt_id": prompt_id,
                    "question": question,
                    "answer": str(trial.get("answer", "")),
                    "packages": list(trial.get("packages", [])),
                }
            )
            blind_key.append(
                {
                    "blind_answer_id": blind_id,
                    "prompt_id": prompt_id,
                    "condition": condition,
                    "generation": trial.get("generation", 0),
                    "source": str(source),
                }
            )

    rng.shuffle(answer_rows)
    out_dir = Path(args.output_dir)
    dump_jsonl(out_dir / f"{args.name}_prompt_manifest.jsonl", prompt_rows)
    dump_jsonl(out_dir / f"{args.name}_manifest.jsonl", answer_rows)
    key_path = Path(args.blind_key)
    key_path.write_text(json.dumps(blind_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "seed": args.seed,
        "source": str(source),
        "n_prompts": len(prompt_rows),
        "n_answers": len(answer_rows),
        "excluded_prompt_ids": sorted(excluded_ids),
        "blind_key": str(key_path),
    }
    (out_dir / f"{args.name}_manifest_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
