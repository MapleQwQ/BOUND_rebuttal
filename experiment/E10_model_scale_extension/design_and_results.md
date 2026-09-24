# E10——更强或更大模型扩展

## 实验目标

探索 BOUND 是否扩展到更强或更大模型。该实验只用于范围扩展，不替代前三个模型的四折证据，也不使用重新筛选高风险集合掩盖未筛选集合上的低 prevalence。

## 执行门

1. 先在 E3 的未筛选共同提示集上报告候选模型 Base prevalence 和 CI。
2. 若 hallucination floor 很低，不以 high-risk 重筛后的相对下降声称总体部署收益。
3. 根据 prevalence、显存、模型许可和推理成本预注册选择一个模型。
4. 优先完成 Base + 一个预注册 BOUND fold + shared prompts，再决定是否扩展 folds/baselines。
5. 保持 E3 的编辑提示并集排除、E7 双时间口径和统一 Package-HR 聚合。

已有 Qwen3-14B、Qwen3-32B、Qwen3.5-9B/27B preliminary Base 输出只作为可行性线索；在协议和 shared set 一致前不与主表直接合并。

## 输出

- `results/model_selection.md`
- `results/base_prevalence.csv`
- `results/resolved_config.yaml`
- `results/generations/`
- `results/metrics.json`
- `results/summary.md`

## 实验结果

状态：存在 preliminary Base 输出；尚未完成共同提示集上的可比 prevalence，也未选择扩展模型。

