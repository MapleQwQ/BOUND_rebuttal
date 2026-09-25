"""Normalize already-completed fold summaries to true blank-output and no-package rates."""

from __future__ import annotations

import json
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]
OUT = E5 / "results/06_gradient_norm"


def main() -> None:
    for metric_file in sorted(OUT.glob("*/fold_*/rq3_metrics.json")) + sorted(OUT.glob("*/fold_*/matched_budget/rq3_metrics.json")):
        directory = metric_file.parent
        evaluation = json.loads((directory / "eval_unseen_prompts.json").read_text(encoding="utf-8"))
        trials = [trial for row in evaluation["details"] for trial in row["edited"]["trials"]]
        if len(trials) != 500:
            raise ValueError(f"Expected 500 RQ3 generations: {directory}")
        metrics = json.loads(metric_file.read_text(encoding="utf-8"))
        metrics["empty_rate"] = sum(not str(trial.get("answer") or "").strip() for trial in trials) / len(trials)
        metrics["no_package_rate"] = sum(not trial.get("packages") for trial in trials) / len(trials)
        metric_file.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        (directory / "rq3_summary.md").write_text(
            f"# RQ3 {metrics['model']} {metrics['fold']} {metrics['setting']}\n\n"
            f"- Sample-HR: {metrics['sample_hr']:.4f}\n"
            f"- Package-HR: {metrics['package_hr']:.4f}\n"
            f"- Valid-Rate: {metrics['valid_rate']:.4f}\n"
            f"- Blank-output rate: {metrics['empty_rate']:.4f}\n"
            f"- No-extracted-package rate: {metrics['no_package_rate']:.4f}\n",
            encoding="utf-8",
        )
        print(directory)


if __name__ == "__main__":
    main()
