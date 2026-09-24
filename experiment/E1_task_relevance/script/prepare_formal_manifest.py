#!/usr/bin/env python3
"""构造 E1 三模型、Base+四折的正式盲标清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


MODELS = {
    "deepseekcoder": "deepseekcoder",
    "qwen3-release": "qwen3-release",
    "llama3.1-release": "llama3.1-release",
}


def read_details(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in payload["details"]}


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def excluded_ids(paths: list[Path]) -> set[str]:
    out: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.add(str(json.loads(line)["prompt_id"]))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, default=Path("/tmp/e1_formal_blind_key.json"))
    parser.add_argument("--prompts-per-model", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--exclude-prompt-manifest", action="append", type=Path, default=[])
    args = parser.parse_args()

    rng = random.Random(args.seed)
    excluded = excluded_ids(args.exclude_prompt_manifest)
    prompt_rows: list[dict] = []
    answer_rows: list[dict] = []
    blind_key: list[dict] = []
    audit: dict[str, dict] = {}

    for model_key, directory in MODELS.items():
        fold_maps: dict[str, dict[str, dict]] = {}
        fold_paths: dict[str, Path] = {}
        for fold in "ABCD":
            path = (
                args.repo_root
                / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
                / directory
                / f"fold_{fold}/blast_50/eval_unseen_prompts.json"
            )
            fold_paths[fold] = path
            fold_maps[fold] = read_details(path)
        common = set.intersection(*(set(rows) for rows in fold_maps.values())) - excluded
        ordered = sorted(common, key=lambda value: (hashlib.sha256(f"{args.seed}|{model_key}|{value}".encode()).hexdigest(), value))
        selected = ordered[: args.prompts_per_model]
        if len(selected) != args.prompts_per_model:
            raise SystemExit(f"{model_key}: only {len(selected)} eligible prompts")
        audit[model_key] = {
            "common_before_exclusion": len(common | (set.intersection(*(set(rows) for rows in fold_maps.values())) & excluded)),
            "excluded_pilot_ids": len(set.intersection(*(set(rows) for rows in fold_maps.values())) & excluded),
            "eligible": len(common),
            "selected": len(selected),
            "source_paths": {fold: str(path) for fold, path in fold_paths.items()},
        }
        for prompt_id in selected:
            rows = {fold: fold_maps[fold][prompt_id] for fold in "ABCD"}
            questions = {str(row["question"]) for row in rows.values()}
            if len(questions) != 1:
                raise SystemExit(f"{model_key}/{prompt_id}: question mismatch across folds")
            task_id = f"{model_key}:{prompt_id}"
            question = questions.pop()
            prompt_rows.append({"task_id": task_id, "prompt_id": prompt_id, "question": question})
            candidates: list[tuple[str, str, dict, Path]] = []
            base_trial = rows["A"]["baseline"]["trials"][0]
            candidates.append(("base", "base", base_trial, fold_paths["A"]))
            for fold in "ABCD":
                trial = rows[fold]["edited"]["trials"][0]
                candidates.append(("bound", fold, trial, fold_paths[fold]))
            rng.shuffle(candidates)
            for answer_index, (condition, fold, trial, source) in enumerate(candidates):
                digest = hashlib.sha256(
                    f"{args.seed}|{task_id}|{answer_index}|{condition}|{fold}".encode()
                ).hexdigest()[:16]
                blind_id = f"E1F-{digest}"
                answer_rows.append(
                    {
                        "blind_answer_id": blind_id,
                        "task_id": task_id,
                        "prompt_id": prompt_id,
                        "question": question,
                        "answer": str(trial.get("answer", "")),
                        "packages": list(trial.get("packages", [])),
                    }
                )
                blind_key.append(
                    {
                        "blind_answer_id": blind_id,
                        "task_id": task_id,
                        "model": model_key,
                        "prompt_id": prompt_id,
                        "condition": condition,
                        "fold": fold,
                        "generation": trial.get("generation", 0),
                        "source": str(source),
                    }
                )

    rng.shuffle(prompt_rows)
    rng.shuffle(answer_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dump_jsonl(args.output_dir / "formal_prompt_manifest.jsonl", prompt_rows)
    dump_jsonl(args.output_dir / "blinded_answers.jsonl", answer_rows)
    args.blind_key.write_text(json.dumps(blind_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "seed": args.seed,
        "prompts_per_model": args.prompts_per_model,
        "n_tasks": len(prompt_rows),
        "n_answers": len(answer_rows),
        "generations_per_condition": 1,
        "conditions_per_task": 5,
        "excluded_prompt_ids": sorted(excluded),
        "blind_key": str(args.blind_key),
        "audit": audit,
    }
    (args.output_dir / "formal_manifest_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
