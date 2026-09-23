from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "results" / "paper"
OUT = ROOT / "results" / "recomputed_bound_tables.md"
MODELS = ["deepseekcoder", "qwen3", "llama3.1"]
FOLDS = ["A", "B", "C", "D"]


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell) for cell in row) + " |")
    return "\n".join(lines)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def package_recommendation_rows() -> list[list[object]]:
    rows: list[list[object]] = []
    for model in MODELS:
        for fold in FOLDS:
            base = PAPER / "package_recommendation" / model / f"fold_{fold}" / "BOUND"
            for scope, filename in [
                ("edit50", "eval_edit_prompts.json"),
                ("unseen", "eval_unseen_prompts.json"),
            ]:
                payload = load_json(base / filename)
                summary = payload["summary"]
                rows.append(
                    [
                        model,
                        fold,
                        scope,
                        summary["n_prompts"],
                        summary["edited_sample_hallucination_rate"],
                        summary["edited_package_hallucination_rate"],
                        summary["edited_sample_valid_rate"],
                    ]
                )
    return rows


def cross_task_generalization_rows() -> list[list[object]]:
    rows: list[list[object]] = []
    for model in MODELS:
        for fold in FOLDS:
            path = (
                PAPER
                / "cross_task_generalization"
                / model
                / "BOUND"
                / f"fold_{fold}"
                / "bound"
                / "cross_task_summary.json"
            )
            summary = load_json(path)
            rows.append(
                [
                    model,
                    fold,
                    summary["code_sample_hr"],
                    summary["code_package_hr"],
                    summary["code_valid_rate"],
                    summary["install_sample_hr"],
                    summary["install_package_hr"],
                    summary["install_valid_rate"],
                ]
            )
    return rows


def main() -> int:
    sections = [
        "# Recomputed BOUND Result Tables",
        "",
        "This file is generated from raw files under `results/paper/`.",
        "",
        "## Package Recommendation Editing",
        markdown_table(
            ["model", "fold", "scope", "prompts", "Sample-HR", "Package-HR", "Valid-Rate"],
            package_recommendation_rows(),
        ),
        "",
        "## Cross-Task Generalization",
        markdown_table(
            [
                "model",
                "fold",
                "code Sample-HR",
                "code Package-HR",
                "code Valid-Rate",
                "install Sample-HR",
                "install Package-HR",
                "install Valid-Rate",
            ],
            cross_task_generalization_rows(),
        ),
        "",
    ]
    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
