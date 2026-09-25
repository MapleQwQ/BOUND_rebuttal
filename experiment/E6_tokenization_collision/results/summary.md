# E6 full-sequence 对照结果

12/12 组已完成。first-token 列复用原论文实验；full-sequence 列为本次新增定位和编辑。

| Model | Top-5 overlap | Top-200 Spearman | Full-rank ρ bounds | Sample-HR first → full | Package-HR first → full | Valid-Rate first → full |
|---|---:|---:|---:|---:|---:|---:|
| deepseekcoder | 0.80 | 0.974 | 0.979–0.982 | 37.12% → 39.21% (+2.10 pp) | 17.06% → 17.64% (+0.58 pp) | 89.09% → 91.10% (+2.01 pp) |
| qwen3-release | 0.85 | 0.996 | 0.980–0.998 | 15.95% → 15.10% (-0.86 pp) | 9.27% → 9.04% (-0.23 pp) | 74.34% → 74.10% (-0.24 pp) |
| llama3.1-release | 1.00 | 0.984 | 0.983–0.987 | 40.33% → 40.33% (+0.00 pp) | 19.55% → 19.55% (+0.00 pp) | 83.53% → 83.53% (+0.00 pp) |

## 定位时间与排名解释

| Model | first-token 历史定位进程耗时 | full-sequence 模型加载 | full-sequence 纯定位耗时 |
|---|---:|---:|---:|
| deepseekcoder | 21.6s | 3.4s | 56.4s |
| qwen3-release | 25.4s | 3.6s | 58.2s |
| llama3.1-release | 24.4s | 3.7s | 89.6s |

历史 first-token 时间包含 Python 进程启动和模型加载；新增 full-sequence 纯定位时间排除了模型加载，因此时间列仅供近似成本比较。历史定位报告每折只保存 top 200 模块，无法恢复一个精确的全模块 Spearman。表中 Full-rank ρ bounds 是所有可能缺失尾部排名下的严格上下界（先逐折求界，再取四折均值），逐折界见 `full_rank_spearman_bounds.csv`；`summary.json` 另存右删失估计。

## 观察与限制

12 折中有 7 折的 top-5 集合改变，但旧 top-200 排名相关性均较高。5 折的实际 LoRA adapter 与历史结果逐 tensor 完全一致，因此编辑后指标相同。其余 7 折重新生成 unseen 结果；DeepSeekCoder 四折的 Sample-HR 平均差值为 +2.10 个百分点，Qwen3 四折为 -0.86 个百分点，方向不一致。可以据此说明首 token 近似会改变部分模块选择和下游结果，但不能据此声称 full-sequence 一致优于默认设置。

旧 first-token unseen 输出直接复用，新生成输出采用可断点恢复的逐 prompt 固定采样 seed，随机流未严格成对。小幅指标差异混合了编辑差异与采样波动；解释时应结合模块选择变化及逐折差值。

## 结果文件

逐折数据与 Base 对照见 `localization_variant_results.csv`；每折新结果见 `results/{model}/fold_{A-D}/full_sequence/`，复用的 first-token 产物快照见并列的 `first_token/`，哈希见 `first_token_snapshot_manifest.json`。只在新旧 adapter 所有 tensor bitwise 相同的折复用历史 unseen 输出，来源记录于 `unseen_reuse_provenance.json`。
