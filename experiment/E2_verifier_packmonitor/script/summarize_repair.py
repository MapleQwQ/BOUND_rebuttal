#!/usr/bin/env python3
"""Summarize E2 one-shot repair JSONL into auditable tables."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * q)
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-label", default="DeepSeekCoder")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    keys = [(row["condition"], str(row["prompt_id"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate condition/prompt rows")

    summary = []
    transitions = []
    latency_rows = []
    conditions = ["base"] + sorted({str(row["condition"]) for row in rows if row["condition"] != "base"})
    for condition in conditions:
        subset = [row for row in rows if row["condition"] == condition]
        attempted = [row for row in subset if row["repair_attempted"]]
        states = Counter(row["terminal_state"] for row in subset)
        latencies = [float(row["repair_latency_seconds"]) for row in attempted]
        entry = {
            "condition": condition,
            "n_prompts": len(subset),
            "initial_invalid_rate": sum(bool(row["initial_invalid"]) for row in subset) / len(subset),
            "repair_attempt_rate": len(attempted) / len(subset),
            "repair_verified_rate_among_attempts": states["repair_verified"] / max(len(attempted), 1),
            "remaining_invalid_rate_after_repair_before_filter": sum(
                bool(row["final_invalid_before_terminal_policy"]) for row in subset
            ) / len(subset),
            "final_empty_rate": sum(not row["final_filtered_packages"] for row in subset) / len(subset),
            "avg_final_packages": sum(len(row["final_filtered_packages"]) for row in subset) / len(subset),
            "repair_latency_mean_seconds": statistics.mean(latencies) if latencies else 0.0,
            "repair_latency_p50_seconds": quantile(latencies, 0.50),
            "repair_latency_p95_seconds": quantile(latencies, 0.95),
        }
        summary.append(entry)
        for state, count in sorted(states.items()):
            transitions.append({"condition": condition, "terminal_state": state, "count": count, "rate": count / len(subset)})
        latency_rows.append(
            {
                "condition": condition,
                "repair_calls": len(attempted),
                "registry_network_calls": 0,
                "latency_mean_seconds": entry["repair_latency_mean_seconds"],
                "latency_p50_seconds": entry["repair_latency_p50_seconds"],
                "latency_p95_seconds": entry["repair_latency_p95_seconds"],
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "repair_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for filename, records in (
        ("repair_state_transitions.csv", transitions),
        ("latency_and_calls.csv", latency_rows),
    ):
        with (args.output_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    lines = [
        "# E2 one-shot repair 小规模结果",
        "",
        f"范围：{args.model_label}，固定 100 prompts；Base 与一个指定 BOUND fold 各使用已有 generation 0 作为初始回答。",
        "registry 为 PackMonitor 官方 commit 随附的 PyPI 名称文件；采用贪心修正、最多一次，之后重新验证全部候选。",
        "",
        "| 条件 | 初始 invalid 率 | repair 后仍有 invalid（过滤前） | 最终空回答率 | repair 成功率（尝试中） | p50/p95 repair 延迟（秒） |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['condition']} | {row['initial_invalid_rate']:.3f} | "
            f"{row['remaining_invalid_rate_after_repair_before_filter']:.3f} | {row['final_empty_rate']:.3f} | "
            f"{row['repair_verified_rate_among_attempts']:.3f} | "
            f"{row['repair_latency_p50_seconds']:.3f}/{row['repair_latency_p95_seconds']:.3f} |"
        )
    lines += [
        "",
        "`repair_verified` 要求修正后没有 invalid 且最终列表非空；仍有 invalid 的回答执行 `final_filter`。",
        "该结果只使用一个模型、一个 BOUND fold、每 prompt 一条初始回答，是小规模探索，不代替四折/三模型正式比较。",
        "",
    ]
    (args.output_dir / "repair_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
