#!/usr/bin/env python3
"""Audit the original BOUND wall-clock timings used by the paper cost table."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "BOUND_rebuttal/replication package/BOUND/results/paper/package_recommendation"
ARCHIVE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
RESULTS = Path(__file__).resolve().parents[1] / "results"
MODELS = {"deepseekcoder": ("deepseekcoder", 541),
          "qwen3": ("qwen3-release", 409),
          "llama3.1": ("llama3.1-release", 934)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    rows = []
    summary = {}
    for source_model, (archive_model, n_prompts) in MODELS.items():
        model_rows = []
        for fold in "ABCD":
            source = SOURCE / source_model / f"fold_{fold}" / "BOUND"
            timing_path = source / "timing.json"
            eval_path = source / "eval_unseen_prompts.json"
            archived = ARCHIVE / archive_model / f"fold_{fold}" / "blast_50/eval_unseen_prompts.json"
            timing = json.loads(timing_path.read_text(encoding="utf-8"))
            evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
            assert timing["model"] == source_model and timing["fold"] == fold
            assert timing["eval_num_generations"] == 5
            assert evaluation["summary"]["n_prompts"] == len(evaluation["details"]) == n_prompts
            assert all(len(item["edited"]["trials"]) == 5 for item in evaluation["details"])
            assert sha256(eval_path) == sha256(archived), (source_model, fold, "archived output differs")
            unseen_total = float(timing["inference"]["unseen_total_sec"])
            edit50_total = float(timing["inference"]["edit50_total_sec"])
            row = {"model": source_model, "fold": fold, "unseen_prompts": n_prompts,
                   "generations_per_prompt": 5, "unseen_eval_total_sec": unseen_total,
                   "unseen_eval_sec_per_prompt_5_generations": unseen_total / n_prompts,
                   "unseen_eval_sec_per_generation_amortized": unseen_total / (n_prompts * 5),
                   "edit50_eval_total_sec": edit50_total,
                   "edit50_eval_sec_per_prompt_5_generations": edit50_total / 50,
                   "timing_path": str(timing_path), "eval_path": str(eval_path),
                   "eval_sha256": sha256(eval_path)}
            rows.append(row)
            model_rows.append(row)
        summary[source_model] = {
            "n_prompts": n_prompts, "n_generations_per_prompt": 5,
            "mean_unseen_eval_total_sec_across_folds": mean(x["unseen_eval_total_sec"] for x in model_rows),
            "mean_unseen_eval_sec_per_prompt_5_generations": mean(x["unseen_eval_sec_per_prompt_5_generations"] for x in model_rows),
            "mean_unseen_eval_sec_per_generation_amortized": mean(x["unseen_eval_sec_per_generation_amortized"] for x in model_rows),
            "fold_min_sec_per_prompt": min(x["unseen_eval_sec_per_prompt_5_generations"] for x in model_rows),
            "fold_max_sec_per_prompt": max(x["unseen_eval_sec_per_prompt_5_generations"] for x in model_rows),
            "mean_edit50_eval_sec_per_prompt_5_generations": mean(x["edit50_eval_sec_per_prompt_5_generations"] for x in model_rows)}
    overall = {"paper_cost_table_reconstructed_unseen_sec_per_prompt_5_generations":
               mean(x["mean_unseen_eval_sec_per_prompt_5_generations"] for x in summary.values()),
               "model_equal_mean_amortized_sec_per_generation":
               mean(x["mean_unseen_eval_sec_per_generation_amortized"] for x in summary.values()),
               "edit50_sec_per_prompt_5_generations_not_paper_11_30":
               mean(x["mean_edit50_eval_sec_per_prompt_5_generations"] for x in summary.values())}
    with (RESULTS / "bound_historical_timing_by_fold.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {"timing_scope": "historical full eval-unseen process wall clock: model load, five generations per prompt, package extraction, PyPI/cutoff classification and result writing; not pure inference",
              "model_summaries": summary, "overall": overall}
    (RESULTS / "bound_historical_timing_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"models": {m: round(x["mean_unseen_eval_sec_per_prompt_5_generations"], 3)
                                  for m, x in summary.items()}, "overall": overall}, indent=2))


if __name__ == "__main__":
    main()
