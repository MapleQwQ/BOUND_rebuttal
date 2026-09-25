"""Match All-module and published BOUND HumanEval by model, fold, run and task."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
NEW = E5 / "results/01_all_module_lora/humaneval_paper_table"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
PAPER_RUNS = {
    "deepseekcoder": {"A": 1, "B": 1, "C": 2, "D": 2},
    "qwen3-release": {"A": 5, "B": 4, "C": 4, "D": 1},
    "llama3.1-release": {"A": 1, "B": 2, "C": 2, "D": 4},
}


def old_folder(model: str, fold: str, run: int) -> Path:
    return (ROOT / "knowledgeEdit/results/humaneval_bound_base_20260620" / model /
            f"fold_{fold}/BOUND/run_{run:02d}")


def load(folder: Path, model: str, seed: int) -> tuple[dict, dict[str, tuple[float, float]]]:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    if (summary.get("n_tasks") != 164 or summary.get("n_samples") != 1640
            or summary.get("num_samples_per_task") != 10 or summary["generation_config"]["seed"] != seed):
        raise ValueError(f"Protocol mismatch: {folder}")
    cfg = summary["generation_config"]
    if cfg["max_new_tokens"] != 512:
        raise ValueError(f"Token budget mismatch: {folder}")
    if cfg.get("use_chat_template") or cfg.get("enable_thinking") == "true":
        raise ValueError(f"Paper table does not use Qwen thinking/chat template: {folder}")
    passes: dict[str, list[int]] = defaultdict(list)
    with (folder / "samples.jsonl_results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            passes[row["task_id"]].append(int(row["passed"]))
    if len(passes) != 164 or any(len(values) != 10 for values in passes.values()):
        raise ValueError(f"Incomplete task results: {folder}")
    per_task = {task: (float(np.mean(values)), float(any(values))) for task, values in passes.items()}
    if abs(np.mean([value[0] for value in per_task.values()]) - summary["pass_at_k"]["pass@1"]) > 1e-9:
        raise ValueError(f"pass@1 mismatch: {folder}")
    if abs(np.mean([value[1] for value in per_task.values()]) - summary["pass_at_k"]["pass@10"]) > 1e-9:
        raise ValueError(f"pass@10 mismatch: {folder}")
    return summary, per_task


def main() -> None:
    rows = []
    result = {}
    rng = np.random.default_rng(20260924)
    for model in MODELS:
        deltas = {"pass@1": [], "pass@10": []}
        old_values = {"pass@1": [], "pass@10": []}
        new_values = {"pass@1": [], "pass@10": []}
        for fold, run in PAPER_RUNS[model].items():
            seed = 42 + run
            old_summary, old = load(old_folder(model, fold, run), model, seed)
            new_folder = NEW / model / f"fold_{fold}/All-module-LoRA/run_{run:02d}"
            new_summary, new = load(new_folder, model, seed)
            if set(old) != set(new):
                raise ValueError(f"Task ID mismatch: {model}/{fold}/{run}")
            tasks = sorted(old, key=lambda task: int(task.split("/")[-1]))
            record = {"model": model, "fold": fold, "run": run, "n_tasks": 164,
                      "bound_total_seconds": old_summary["timing_seconds"]["total"],
                      "all_module_total_seconds": new_summary["timing_seconds"]["total"]}
            for index, metric in enumerate(("pass@1", "pass@10")):
                before = np.array([old[task][index] for task in tasks])
                after = np.array([new[task][index] for task in tasks])
                old_values[metric].append(before)
                new_values[metric].append(after)
                deltas[metric].append(after - before)
                record[f"bound_{metric}"] = float(before.mean())
                record[f"all_module_{metric}"] = float(after.mean())
                record[f"delta_{metric}"] = float((after - before).mean())
            rows.append(record)
        result[model] = {}
        indices = rng.integers(0, 164, size=(10000, 164))
        for metric in ("pass@1", "pass@10"):
            matrix = np.stack(deltas[metric])
            boot = matrix[:, indices].mean(axis=(0, 2))
            result[model][metric] = {
                "bound_four_fold_macro": float(np.stack(old_values[metric]).mean()),
                "all_module_four_fold_macro": float(np.stack(new_values[metric]).mean()),
                "delta_all_minus_bound": float(matrix.mean()),
                "ci95_task_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist(),
            }
    with (NEW / "per_run_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {"status": "complete", "n_runs_per_model": 4, "n_samples_per_task": 10,
               "bootstrap_seed": 20260924, "bootstrap_resamples": 10000,
               "bootstrap_unit": "HumanEval task; fold and run fixed", "models": result}
    (NEW / "comparison_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
