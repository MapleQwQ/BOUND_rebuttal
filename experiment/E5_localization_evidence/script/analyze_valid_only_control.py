"""Compare archived full-risk localization with the same-prompt valid-only control."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FULL = ROOT / "knowledgeEdit/results/rq4_localization_analysis_20260615/rq4_prompt_level_scores.jsonl"
CONTROL = E5 / "results/03_localization_stability/valid_only"
OUT = E5 / "results/03_localization_stability"


def main() -> None:
    full: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    with FULL.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            full[(row["model"], row["fold"], str(row["prompt_id"]))].append(row)
    rows = []
    rng = np.random.default_rng(20260924)
    summary = {}
    for model in MODELS:
        meta = json.loads((CONTROL / model / "metadata.json").read_text(encoding="utf-8"))
        if meta["n_prompts"] != 200:
            raise ValueError(f"Incomplete control: {model}")
        seen = set()
        family_full, family_control = Counter(), Counter()
        layer_full, layer_control = Counter(), Counter()
        with (CONTROL / model / "per_prompt.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                control = json.loads(line)
                key = (model, control["fold"], str(control["prompt_id"]))
                if key in seen:
                    raise ValueError(f"Duplicate control prompt: {key}")
                seen.add(key)
                original = sorted(full[key], key=lambda row: int(row["rank"]))
                valid = control["scores"]
                full_names = [row["module"] for row in original]
                valid_names = [row["module"] for row in valid]
                if len(full_names) != len(valid_names) or set(full_names) != set(valid_names):
                    raise ValueError(f"Candidate module mismatch: {key}")
                a, b = set(full_names[:5]), set(valid_names[:5])
                valid_rank = {name: i for i, name in enumerate(valid_names)}
                x = np.arange(len(full_names), dtype=float)
                y = np.array([valid_rank[name] for name in full_names], dtype=float)
                rho = float(np.corrcoef(x, y)[0, 1])
                rows.append({"model": model, "fold": control["fold"], "prompt_id": control["prompt_id"],
                             "n_modules": len(full_names), "top1_same": int(full_names[0] == valid_names[0]),
                             "top5_intersection": len(a & b), "top5_jaccard": len(a & b) / len(a | b),
                             "rank_spearman": rho,
                             "full_top1": full_names[0], "valid_only_top1": valid_names[0]})
                family_full.update(row["module_family"] for row in original[:5])
                family_control.update(row["module_family"] for row in valid[:5])
                layer_full.update(row["layer"] for row in original[:5])
                layer_control.update(row["layer"] for row in valid[:5])
        if len(seen) != meta["n_prompts_scored"]:
            raise ValueError(f"Control count mismatch: {model}/{len(seen)}")
        selected = [row for row in rows if row["model"] == model]
        indices = rng.integers(0, len(selected), size=(10000, len(selected)))
        metric_summary = {}
        for metric in ("top1_same", "top5_intersection", "top5_jaccard", "rank_spearman"):
            values = np.array([row[metric] for row in selected], dtype=float)
            boot = values[indices].mean(axis=1)
            metric_summary[metric] = {"mean": float(values.mean()),
                                      "ci95_prompt_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist()}
        summary[model] = {"n_prompts_total": 200, "n_prompts_paired": len(selected),
                          "n_prompts_no_valid_reference": meta["n_prompts_skipped_no_valid"],
                          "metrics": metric_summary,
                          "full_top5_family": dict(family_full), "valid_only_top5_family": dict(family_control),
                          "full_top5_layers": dict(layer_full.most_common(10)),
                          "valid_only_top5_layers": dict(layer_control.most_common(10))}
    with (OUT / "valid_only_comparison_per_prompt.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {"bootstrap_seed": 20260924, "bootstrap_resamples": 10000,
              "comparison": "same prompt and candidate modules, full risk versus valid-only LSE", "models": summary}
    (OUT / "valid_only_comparison_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
