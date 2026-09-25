"""Compare full-risk and hallucination-only localization rankings on all 12 folds."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def main() -> None:
    rows = []
    for model in MODELS:
        for fold in "ABCD":
            full_path = (ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / model /
                         f"fold_{fold}/blast_50/localization_report.json")
            hall_path = (ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model /
                         f"fold_{fold}/wo_valid_anchor/localization_report.json")
            full = json.loads(full_path.read_text(encoding="utf-8"))
            hall = json.loads(hall_path.read_text(encoding="utf-8"))
            a = [row["module"] for row in full["layer_scores"]]
            b = [row["module"] for row in hall["layer_scores"]]
            common = set(a) & set(b)
            if len(a) != 200 or len(b) != 200 or len(common) < 180:
                raise ValueError(f"Unexpected ranking coverage: {model}/{fold}")
            ra = {name: i for i, name in enumerate(a)}
            rb = {name: i for i, name in enumerate(b)}
            names = sorted(common)
            rho = float(np.corrcoef([ra[name] for name in names], [rb[name] for name in names])[0, 1])
            top5a, top5b = set(a[:5]), set(b[:5])
            rows.append({"model": model, "fold": fold, "n_ranked_full": len(a),
                         "n_ranked_hall_only": len(b), "n_common": len(common),
                         "top5_jaccard": len(top5a & top5b) / len(top5a | top5b),
                         "top5_intersection": len(top5a & top5b),
                         "common_rank_spearman": rho})
    output = E5 / "results/02_risk_score/localization_rank_comparison.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {model: {metric: float(np.mean([row[metric] for row in rows if row["model"] == model]))
                       for metric in ("top5_jaccard", "top5_intersection", "common_rank_spearman")}
               for model in MODELS}
    (output.parent / "localization_rank_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
