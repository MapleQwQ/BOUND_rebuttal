# E10——实验过程记录

本文件按时间顺序追加，记录候选模型、选择依据、资源评估、配置、运行和结果版本。

## 2026-09-23

- 清点到 Qwen3-14B、Qwen3-32B、Qwen3.5-9B/27B preliminary Base 输出。
- 明确这些输出在 prompt 集和协议统一前不能直接与主结果合并。
- 将未筛选共同集上的 Base prevalence 设为模型选择前置条件。
- 明确一个预注册 fold 只能称为探索性范围扩展。

## 下一步

- 等待 E3 shared prompt manifest 冻结。
- 用统一协议复算候选模型 Base prevalence 与成本。
- 在查看 BOUND 效果前冻结模型和 fold 选择。

