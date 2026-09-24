# E2 小规模 post-hoc verifier 结果

> 状态：探索性/暂定。历史在线标签存在同-cutoff 冲突；在 E7 时间快照复核前，本表不得用于最终 rebuttal claim。

固定抽样：每个模型 100 个 prompt，每个条件 5 次已有生成；Base 一份，BOUND 四折。
抽样 seed：`20260923`。本次共处理 7500 条回答。

本阶段只验证 post-hoc filtering。包标签来自原评估中按各模型 cutoff 缓存的标签，并在模型/cutoff 内构建一致快照；未重新查询 PyPI。
它不是 PackMonitor、不是 one-shot repair，也不提供任务充分性结论。

历史标签发现 6 个同-cutoff 冲突，固定采用 `valid-wins` 消解并在 `registry_snapshot.json` 保留原冲突；理由是成功查询提供存在性的正证据，而旧失败查询可能是瞬时网络错误。

| 模型 | 条件 | 初始 Sample-HR | 初始 Package-HR | 过滤后空回答率 | 每回答保留真实包 |
|---|---:|---:|---:|---:|---:|
| deepseekcoder | base | 0.836 | 0.343 | 0.162 | 1.818 |
| deepseekcoder | bound_fold_A | 0.202 | 0.109 | 0.166 | 2.212 |
| deepseekcoder | bound_fold_B | 0.392 | 0.176 | 0.090 | 2.310 |
| deepseekcoder | bound_fold_C | 0.272 | 0.100 | 0.068 | 2.882 |
| deepseekcoder | bound_fold_D | 0.482 | 0.187 | 0.048 | 2.772 |
| qwen3-release | base | 0.884 | 0.343 | 0.132 | 1.836 |
| qwen3-release | bound_fold_A | 0.126 | 0.080 | 0.148 | 1.726 |
| qwen3-release | bound_fold_B | 0.124 | 0.150 | 0.458 | 1.052 |
| qwen3-release | bound_fold_C | 0.226 | 0.153 | 0.272 | 1.854 |
| qwen3-release | bound_fold_D | 0.240 | 0.137 | 0.182 | 2.262 |
| llama3.1-release | base | 0.822 | 0.364 | 0.112 | 2.122 |
| llama3.1-release | bound_fold_A | 0.344 | 0.182 | 0.154 | 2.462 |
| llama3.1-release | bound_fold_B | 0.432 | 0.311 | 0.316 | 2.528 |
| llama3.1-release | bound_fold_C | 0.526 | 0.231 | 0.022 | 2.452 |
| llama3.1-release | bound_fold_D | 0.424 | 0.170 | 0.018 | 3.110 |

所有条件的过滤后 Sample-HR 与 Package-HR 按构造均为 0；这只说明无效候选被删除，不能解释为回答充分或任务成功。
后续仍需补充 deployment-date snapshot、one-shot repair 和 PackMonitor 兼容性试运行。
