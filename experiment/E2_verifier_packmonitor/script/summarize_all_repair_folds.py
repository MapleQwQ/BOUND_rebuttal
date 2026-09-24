#!/usr/bin/env python3
"""汇总 E2 三模型四折 one-shot repair 结果。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODELS = {
    "DeepSeekCoder": "deepseek",
    "Qwen3": "qwen3",
    "Llama-3.1": "llama31",
}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(rows: list[dict]) -> dict[str, float]:
    n = len(rows)
    attempted = [row for row in rows if row["repair_attempted"]]
    return {
        "n": n,
        "initial_invalid": sum(bool(row["initial_invalid"]) for row in rows) / n,
        "residual_invalid": sum(bool(row["final_invalid_before_terminal_policy"]) for row in rows) / n,
        "final_empty": sum(not row["final_filtered_packages"] for row in rows) / n,
        "repair_success": sum(row["terminal_state"] == "repair_verified" for row in rows)
        / max(len(attempted), 1),
        "avg_final_packages": sum(len(row["final_filtered_packages"]) for row in rows) / n,
    }


def main() -> None:
    output: dict[str, dict] = {}
    lines = [
        "# E2 三模型四折 one-shot repair 汇总",
        "",
        "每个模型、每折固定100 prompts；每个条件使用已有 generation 0。Base 指标取 fold-A 文件，BOUND macro 为 A/B/C/D 四折算术平均。",
        "",
        "| 模型 | 条件 | 初始 invalid | repair后残余 invalid | 最终空回答 | repair成功率 | 最终包数 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for model, key in MODELS.items():
        fold_rows: dict[str, list[dict]] = {}
        paths = {
            "A": RESULTS / f"repair_generations_{key}.jsonl" if key != "deepseek" else RESULTS / "repair_generations.jsonl",
            **{fold: RESULTS / f"repair_generations_{key}_fold{fold}.jsonl" for fold in "BCD"},
        }
        for fold, path in paths.items():
            rows = load(path)
            bound = [row for row in rows if row["condition"] != "base"]
            if len(bound) != 100:
                raise SystemExit(f"{path}: expected 100 BOUND rows, got {len(bound)}")
            fold_rows[fold] = bound
        base_rows = [row for row in load(paths["A"]) if row["condition"] == "base"]
        if len(base_rows) != 100:
            raise SystemExit(f"{paths['A']}: expected 100 Base rows")
        base = metrics(base_rows)
        folds = {fold: metrics(rows) for fold, rows in fold_rows.items()}
        macro = {name: sum(value[name] for value in folds.values()) / 4 for name in (
            "initial_invalid", "residual_invalid", "final_empty", "repair_success", "avg_final_packages"
        )}
        output[model] = {"base": base, "bound_folds": folds, "bound_macro": macro}
        for condition, row in (("Base", base), ("BOUND四折均值", macro)):
            lines.append(
                f"| {model} | {condition} | {row['initial_invalid']:.3f} | {row['residual_invalid']:.3f} | "
                f"{row['final_empty']:.3f} | {row['repair_success']:.3f} | {row['avg_final_packages']:.3f} |"
            )
    lines += [
        "",
        "注意：最终过滤按构造移除残余 invalid，但不保证任务充分性。空回答和最终包数是必要 guardrails；该实验仍不是 PackMonitor 生成中约束解码，也不是真实 coding-agent 执行实验。",
        "",
    ]
    (RESULTS / "all_models_four_folds_repair.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "all_models_four_folds_repair.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
