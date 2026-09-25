# E6：first-token 与 full-sequence localization 成对实验

## 目标与范围

在 DeepSeekCoder、Qwen3-8B、Llama3.1-8B 的四个既有 edit folds（A–D）上，复用既有 first-token localization、BLAST 编辑和 unseen 结果；只新增 full-sequence localization、编辑和 unseen 评估。总计 12 个新增运行单元，与 12 个历史 first-token 单元成对比较。用定位排名、运行时间和编辑后指标判断 first-token 近似是否实质改变定位及编辑效果。

## 固定输入与控制变量

- 每折沿用 `knowledgeEdit/results/robust_nonedit_highrisk_20260605/{model}/fold_{A-D}/blast_50/experiment_config.json` 中的模型、50 条 `selected_task_recommend_cases.jsonl`、定位随机种子、BLAST 参数、定位候选模块族、top-5、window-family ±1 选择和 unseen 生成参数。编辑随机种子以历史实际 `blast_config.json` 为准；Llama3.1 fold A 的历史编辑 seed=43，与总配置中的定位 seed=42 不同。
- 新增变体与历史 first-token 实现使用完全相同的 recommendation chat prompt、候选包名集合及前导 ASCII 空格策略；只改变定位 risk 的候选打分。
- 既有四折 held-out high-risk prompt 集保持不变。每个 unseen prompt 生成 5 次，沿用原折的最大生成长度、温度、top-k/top-p、包名分类器与截止日期。需要新增生成时，full-sequence 变体对每个 prompt 的 5 次采样分别使用由固定 seed 和 prompt 顺序导出的种子，并逐 prompt 保存断点；历史 first-token 生成沿用原文件，因此随机流未严格成对，解释小幅差异时须谨慎。
- 新增 full-sequence 定位保留全部可选模块的分数和排序。历史 first-token 报告只保留 top 200；编辑从同一 base 权重重新加载。若新旧编辑所得 LoRA adapter 的所有 tensor 逐项 bitwise 相同，则复制历史 unseen 输出并写入复用来源；否则重新生成 unseen 输出。

## 两种定位目标

对每条有 hallucinated 包的 edit 记录，令 `H` 为 hallucinated 名称集合、`G` 为 valid reference 名称集合，`λ=0.5` 为既有 anchor penalty。

**First-token（复用历史结果）**：对 `" " + package_name` 分词，取首 token ID；每类 ID 去重。风险是 hallucinated 首 token logits 的 log-sum-exp，减去 `λ` 倍 valid 首 token logits 的 log-sum-exp。空 valid 集时省略后一项。其余梯度和模块打分复刻既有实现。

**Full-sequence**：对每个不同的完整包名 token 序列 `t_1,…,t_L`，计算条件 log probability 的长度归一化值 `s(pkg) = (1/L) Σ_j log P(t_j | chat_context,t_<j)`；相同完整 token 序列去重。风险为 `logsumexp_{h∈H}s(h) − λ·logsumexp_{g∈G}s(g)`，空 valid 集时省略后一项。长度归一化避免长包名因 token 数更多而机械地得到更小的总 log probability。新增方法与历史方法都按每条记录 `mean(abs(gradient × weight))` 给模块打分，再对记录求平均。原配置的 family penalty 均为 0。

## 测量与分析

- **Top-k 模块重合率**：同一模型、同一 fold 两种定位 top-5 模块集合的交集数/5。另记录 `window_family` 展开后的实际 LoRA 模块数及交集，以识别训练参数预算变化。
- **排名相关性**：历史 first-token 报告每折仅保存 top 200，故精确的全模块 Spearman 无法从旧文件恢复。主报告在旧 top 200 模块上计算 Spearman ρ；对完整模块集合，依据已知前 200 名和缺失模块只能占据第 201–N 名这一事实，求所有可能尾部排列下 Spearman ρ 的严格最小值和最大值。实现依据重排不等式：新排名固定，未知尾部按新排名反向/同向排列分别使秩协方差最小/最大；`script/rank_bounds.py` 以小规模穷举自测。另保留将尾部并列第 201 位的右删失点估计。精确单值仍不可恢复，以上界限不能被写成一个精确观测值。
- **Localization 时间**：历史 first-token 使用 `timing.json` 的 localization `elapsed_sec`（整个定位子进程，含启动和模型加载）；新增 full-sequence 记录模型加载、纯定位及其合计时间。主表列出这两种计时口径并标明不可严格直接比较；新增逐记录耗时供审计。
- **编辑后 unseen 指标**：沿用既有 `eval_unseen_prompts.json` 格式及逐 prompt 宏平均口径，报告 Sample-HR、Package-HR、Valid-Rate。与相同 unseen 集的 Base 值并列，主比较为 12 组成对 first-token/full-sequence 差值。不能根据测试结果选择 fold。
- 先核验每折输入哈希、定位记录数、模型模块集合和输出完整性，再汇总四折均值及成对差值。若 top-5 相同但排名不同，仍报告旧 top-200 范围内相关性和时间；若 top-5 不同，检查实际编辑模块和 unseen 指标是否随之变化。

## 脚本和产物

所有**新建**脚本、日志和结果均在本目录。运行脚本为 `script/run_e6.py`；`script/snapshot_legacy.py` 将 12 折复用的 first-token 原始结果复制到 `results/{model}/fold_{A-D}/first_token/`，文件哈希见 `results/first_token_snapshot_manifest.json`。每个新增 full-sequence 单元输出在 `results/{model}/fold_{A-D}/full_sequence/`：`localization_report.json`、`experiment_config.json`、`blast_delta.pt`、`blast_config.json`、`train_log.jsonl`、`eval_unseen_prompts.json`、逐 prompt `unseen_progress.jsonl`（若实际生成）和运行日志。总体汇总为 `results/localization_variant_results.csv`、`results/full_rank_spearman_bounds.csv` 及本文件中的结果表。运行可断点续跑，已完成阶段跳过。

## 实验结果

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

## 数据核验与产物

12/12 折均通过 `script/validate.py` 核验；first-token 历史结果快照与原文件逐文件 SHA-256 一致。核验内容包括：每折 50 条定位记录，完整模块报告（DeepSeekCoder/Llama3.1 各 224，Qwen3 252），实际历史编辑 seed，全部 unseen prompt IDs 和每条 5 次生成，评估宏平均重算；5 个复用折的 adapter 与历史逐 tensor 相同且复制的 unseen 文件 SHA-256 相同。全模块相关性严格界限见 `results/full_rank_spearman_bounds.csv`。核验清单和输入哈希见 `results/validation.json`。逐折 Base/first-token/full-sequence 数值见 `results/localization_variant_results.csv`，模型汇总见 `results/summary.json` 和 `results/summary.md`。
