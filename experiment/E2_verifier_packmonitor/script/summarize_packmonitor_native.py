#!/usr/bin/env python3
"""汇总100-task原生PackMonitor四条件配对结果。"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def load(path: Path) -> dict[str, dict[str, dict]]:
    rows: dict[str, dict[str, dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows.setdefault(str(row["prompt_id"]), {})[row["condition"]] = row
    return rows


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def stats(rows: dict[str, dict[str, dict]], conditions: tuple[str, str], seed: int, n_boot: int) -> dict:
    ids = sorted(rows, key=int)
    if not ids or any(set(rows[prompt_id]) != set(conditions) for prompt_id in ids):
        raise ValueError(f"conditions are incomplete for {conditions}")

    def rate(sample: list[str], condition: str, field: str) -> float:
        return sum(bool(rows[prompt_id][condition][field]) for prompt_id in sample) / len(sample)

    output = {"n_tasks": len(ids), "conditions": {}}
    for condition in conditions:
        subset = [rows[prompt_id][condition] for prompt_id in ids]
        output["conditions"][condition] = {
            "invalid_answer_rate": sum(bool(row["invalid_packages"]) for row in subset) / len(subset),
            "empty_package_rate": sum(bool(row["empty_package_list"]) for row in subset) / len(subset),
            "install_region_trigger_rate": sum(bool(row["install_region_emitted"]) for row in subset) / len(subset),
            "generation_error_rate": sum(row["error"] is not None for row in subset) / len(subset),
            "mean_latency_seconds": sum(float(row["latency_seconds"]) for row in subset) / len(subset),
        }
    rng = random.Random(seed)
    for field, label in (("invalid_packages", "invalid_answer_rate"), ("empty_package_list", "empty_package_rate")):
        observed = rate(ids, conditions[1], field) - rate(ids, conditions[0], field)
        draws = []
        for _ in range(n_boot):
            sample = [rng.choice(ids) for _ in ids]
            draws.append(rate(sample, conditions[1], field) - rate(sample, conditions[0], field))
        output[f"delta_{label}"] = observed
        output[f"delta_{label}_ci95"] = [percentile(draws, 0.025), percentile(draws, 0.975)]
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260923)
    args = parser.parse_args()
    base_rows = load(args.results_dir / "packmonitor_runtime100_generations.jsonl")
    bound_rows = load(args.results_dir / "packmonitor_bound_runtime100_generations.jsonl")
    result = {
        "scope": "DeepSeekCoder, frozen E2 manifest, native constrained decoding",
        "base_vs_packmonitor": stats(base_rows, ("base", "packmonitor"), args.seed, args.bootstrap),
        "bound_vs_bound_packmonitor": stats(bound_rows, ("bound", "bound_packmonitor"), args.seed, args.bootstrap),
        "bootstrap": {"cluster": "prompt", "replicates": args.bootstrap, "seed": args.seed},
        "boundary": "registry membership and install-region syntax only; no adequacy or execution claim",
    }
    (args.results_dir / "packmonitor_native100_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# PackMonitor 原生约束解码 100-task 汇总",
        "",
        "范围：DeepSeekCoder、冻结 E2 100-task manifest、greedy decoding；PackMonitor 仅应用官方 grammar 拼写的最小兼容修正。",
        "",
        "| 比较 | 条件 | invalid answer | empty | 触发率 | 平均时延（秒） |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for comparison in ("base_vs_packmonitor", "bound_vs_bound_packmonitor"):
        block = result[comparison]
        first = True
        for condition, values in block["conditions"].items():
            lines.append(
                f"| {comparison if first else ''} | {condition} | {values['invalid_answer_rate']:.3f} | "
                f"{values['empty_package_rate']:.3f} | {values['install_region_trigger_rate']:.3f} | {values['mean_latency_seconds']:.3f} |"
            )
            first = False
        lo, hi = block["delta_invalid_answer_rate_ci95"]
        lines.append(
            f"| 配对差（约束−无约束） | invalid | {block['delta_invalid_answer_rate']:+.3f} "
            f"(95% CI [{lo:+.3f}, {hi:+.3f}]) | — | — | — |"
        )
    lines += [
        "",
        "该表只验证安装区域语法和冻结 registry 成员约束；不把 registry-valid 解释为任务相关、可安装、API兼容或端到端成功。",
    ]
    (args.results_dir / "packmonitor_native100_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
