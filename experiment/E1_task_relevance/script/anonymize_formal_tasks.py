#!/usr/bin/env python3
"""移除 E1 正式清单中会泄露模型名称的 task_id。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
KEY = Path("/tmp/e1_anonymous_task_key.json")
SEED = "20260925-e1-task-anonymization-v1"


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    prompts = read(RESULTS / "formal_prompt_manifest.jsonl")
    answers = read(RESULTS / "blinded_answers.jsonl")
    slots = read(RESULTS / "frozen_requirement_slots.jsonl")
    mapping = {
        row["task_id"]: "TASK-" + hashlib.sha256(f"{SEED}|{row['task_id']}".encode()).hexdigest()[:16]
        for row in prompts
    }
    anon_prompts = [{"anonymous_task_id": mapping[row["task_id"]], "question": row["question"]} for row in prompts]
    anon_answers = [
        {
            "blind_answer_id": row["blind_answer_id"],
            "anonymous_task_id": mapping[row["task_id"]],
            "question": row["question"],
            "answer": row["answer"],
            "packages": row["packages"],
        }
        for row in answers
    ]
    anon_slots = [
        {
            "anonymous_task_id": mapping[row["task_id"]],
            "slots": row.get("slots", []),
            "no_third_party_dependency_needed": row.get("no_third_party_dependency_needed", False),
            "non_dependency_constraints": row.get("non_dependency_constraints", []),
        }
        for row in slots
    ]
    write(RESULTS / "formal_prompt_manifest_anonymous.jsonl", anon_prompts)
    write(RESULTS / "blinded_answers_anonymous.jsonl", anon_answers)
    write(RESULTS / "frozen_requirement_slots_anonymous.jsonl", anon_slots)
    KEY.write_text(
        json.dumps(
            [{"anonymous_task_id": anon, "original_task_id": original} for original, anon in mapping.items()],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"tasks": len(anon_prompts), "answers": len(anon_answers), "key": str(KEY)}))


if __name__ == "__main__":
    main()
