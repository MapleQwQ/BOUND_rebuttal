#!/usr/bin/env python3
"""Produce the E6 paper-facing paired summary from the validated run CSV."""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

E6 = Path(__file__).resolve().parent.parent
CSV = E6 / "results/localization_variant_results.csv"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = "ABCD"
METRICS = ("sample_hr", "package_hr", "valid_rate")


def mean(rows, key):
    return statistics.mean(float(x[key]) for x in rows)


def pct(value):
    return f"{100 * value:.2f}%"


def main():
    rows = list(csv.DictReader(CSV.open()))
    by_pair = defaultdict(dict)
    for row in rows:
        by_pair[(row["model"], row["fold"])][row["variant"]] = row
    complete = {k: v for k, v in by_pair.items() if set(v) == {"first_token", "full_sequence"}}
    if len(complete) != 12:
        raise SystemExit(f"Require 12 completed pairs; found {len(complete)}")
    bound_rows = list(csv.DictReader((E6 / "results/full_rank_spearman_bounds.csv").open()))
    bounds = {(r["model"], r["fold"]): r for r in bound_rows}
    if set(bounds) != set(complete):
        raise SystemExit("Full-ranking bound file must cover the same 12 pairs")
    result = {"n_pairs": 12, "models": {}, "all_pairs": {}}
    lines = ["# E6 full-sequence 对照结果", "", "12/12 组已完成。first-token 列复用原论文实验；full-sequence 列为本次新增定位和编辑。", "",
             "| Model | Top-5 overlap | Top-200 Spearman | Full-rank ρ bounds | Sample-HR first → full | Package-HR first → full | Valid-Rate first → full |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for model in MODELS:
        pairs = [complete[(model, fold)] for fold in FOLDS]
        first = [x["first_token"] for x in pairs]
        full = [x["full_sequence"] for x in pairs]
        entry = {
            "n_folds": 4,
            "top5_overlap_mean": mean(full, "top5_overlap"),
            "old_top200_spearman_mean": mean(full, "old_top200_spearman"),
            "full_rank_spearman_lower_mean": statistics.mean(float(bounds[(model, fold)]["full_rank_spearman_lower_bound"]) for fold in FOLDS),
            "full_rank_spearman_upper_mean": statistics.mean(float(bounds[(model, fold)]["full_rank_spearman_upper_bound"]) for fold in FOLDS),
            "right_censored_all_module_spearman_mean": mean(full, "right_censored_all_module_spearman"),
            "first_token_localization_wall_seconds_mean": mean(first, "localization_seconds"),
            "full_sequence_scoring_seconds_mean": mean(full, "localization_seconds"),
            "full_sequence_model_load_seconds_mean": mean(full, "model_load_seconds"),
            "expanded_module_jaccard_mean": mean(full, "selected_module_jaccard"),
        }
        for metric in METRICS:
            entry[metric] = {"first_mean": mean(first, metric), "full_mean": mean(full, metric),
                             "full_minus_first_mean": mean(full, metric) - mean(first, metric),
                             "fold_deltas": [float(b[metric]) - float(a[metric]) for a, b in zip(first, full)]}
        result["models"][model] = entry
        lines.append(f"| {model} | {entry['top5_overlap_mean']:.2f} | {entry['old_top200_spearman_mean']:.3f} | {entry['full_rank_spearman_lower_mean']:.3f}–{entry['full_rank_spearman_upper_mean']:.3f} | " +
                     " | ".join(f"{pct(entry[m]['first_mean'])} → {pct(entry[m]['full_mean'])} ({100*entry[m]['full_minus_first_mean']:+.2f} pp)" for m in METRICS) + " |")
        for fold, pair in zip(FOLDS, pairs):
            result["all_pairs"][f"{model}/{fold}"] = {
                "top5_overlap": float(pair["full_sequence"]["top5_overlap"]),
                "old_top200_spearman": float(pair["full_sequence"]["old_top200_spearman"]),
                "full_rank_spearman_bounds": [float(bounds[(model, fold)]["full_rank_spearman_lower_bound"]),
                                              float(bounds[(model, fold)]["full_rank_spearman_upper_bound"])],
                "expanded_module_jaccard": float(pair["full_sequence"]["selected_module_jaccard"]),
                "metric_deltas": {m: float(pair["full_sequence"][m]) - float(pair["first_token"][m]) for m in METRICS},
            }
    lines += ["", "## 定位时间与排名解释", "",
              "| Model | first-token 历史定位进程耗时 | full-sequence 模型加载 | full-sequence 纯定位耗时 |",
              "|---|---:|---:|---:|"]
    for model in MODELS:
        x = result["models"][model]
        lines.append(f"| {model} | {x['first_token_localization_wall_seconds_mean']:.1f}s | {x['full_sequence_model_load_seconds_mean']:.1f}s | {x['full_sequence_scoring_seconds_mean']:.1f}s |")
    changed = sum(v["top5_overlap"] < 1 for v in result["all_pairs"].values())
    deep_delta = 100 * result["models"]["deepseekcoder"]["sample_hr"]["full_minus_first_mean"]
    qwen_delta = 100 * result["models"]["qwen3-release"]["sample_hr"]["full_minus_first_mean"]
    reused = sum((E6 / "results" / model / f"fold_{fold}" / "full_sequence" / "unseen_reuse_provenance.json").exists() for model in MODELS for fold in FOLDS)
    lines += ["", "历史 first-token 时间包含 Python 进程启动和模型加载；新增 full-sequence 纯定位时间排除了模型加载，因此时间列仅供近似成本比较。历史定位报告每折只保存 top 200 模块，无法恢复一个精确的全模块 Spearman。表中 Full-rank ρ bounds 是所有可能缺失尾部排名下的严格上下界（先逐折求界，再取四折均值），逐折界见 `full_rank_spearman_bounds.csv`；`summary.json` 另存右删失估计。", "",
              "## 观察与限制", "",
              f"12 折中有 {changed} 折的 top-5 集合改变，但旧 top-200 排名相关性均较高。{reused} 折的实际 LoRA adapter 与历史结果逐 tensor 完全一致，因此编辑后指标相同。其余 {12-reused} 折重新生成 unseen 结果；DeepSeekCoder 四折的 Sample-HR 平均差值为 {deep_delta:+.2f} 个百分点，Qwen3 四折为 {qwen_delta:+.2f} 个百分点，方向不一致。可以据此说明首 token 近似会改变部分模块选择和下游结果，但不能据此声称 full-sequence 一致优于默认设置。", "",
              "旧 first-token unseen 输出直接复用，新生成输出采用可断点恢复的逐 prompt 固定采样 seed，随机流未严格成对。小幅指标差异混合了编辑差异与采样波动；解释时应结合模块选择变化及逐折差值。", "",
              "## 结果文件", "",
              "逐折数据与 Base 对照见 `localization_variant_results.csv`；每折新结果见 `results/{model}/fold_{A-D}/full_sequence/`，复用的 first-token 产物快照见并列的 `first_token/`，哈希见 `first_token_snapshot_manifest.json`。只在新旧 adapter 所有 tensor bitwise 相同的折复用历史 unseen 输出，来源记录于 `unseen_reuse_provenance.json`。", ""]
    (E6 / "results/summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (E6 / "results/summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
