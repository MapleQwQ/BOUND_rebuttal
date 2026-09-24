# E7——PyPI 有效性、时间与名称映射审计

## 实验目标

把当前二元 valid/hallucinated 标签拆成相互独立的证据维度，避免把 cutoff 后真实发布、namespace/alias、元数据缺失或网络失败统一记为“不存在”。

## 多维状态 schema

每个原始模型输出名称必须原样保留，并分别记录：

| 维度 | 允许状态示例 |
| --- | --- |
| 注册表状态 | `exists`、`not_found`、`uncertain` |
| 时间状态 | `pre_cutoff`、`post_cutoff`、`release_date_unknown` |
| 名称/映射关系 | `direct_distribution`、`stdlib`、`alias_or_renamed`、`namespace`、`import_distribution_mismatch`、`ambiguous` |
| 查询证据 | `success_response`、`network_failure`、`metadata_missing`、`cache_hit` |

这些字段不互斥。例如一个候选可以同时是 `exists + post_cutoff + alias_or_renamed + success_response`。normalization 只用于查询键，不能把模型输出的错误名称悄悄替换成正确依赖后记为成功。

## 两种存在性口径

1. **原论文 cutoff 口径：** 保持与投稿表格可比，使用结果生成时冻结的模型 cutoff。
2. **固定评估日期口径：** 判断在指定评估日期是否真实存在。

cutoff 后发布但评估时存在的包单独报告，不能与评估时仍不存在的名称合并为同一种安全风险。E2 verifier/PackMonitor 也使用这两种配置。

## 数据与人工审计

- 对全部 unique raw candidates 查询并冻结原始 registry response、HTTP/错误状态、查询时间和 cache key。
- 按随机样本、高频样本、长尾、dotted name、hyphen/underscore、extras、版本约束、namespace、alias 和 post-cutoff 分层人工复核。
- 查询失败和无法确定项保留在完整分母，并报告保守/宽松边界。
- 计算二元旧标签相对多维新标签的误差率，以及对 Sample-HR/Package-HR 和 E2 verifier 结果的敏感性。

## 输出

- `results/registry_cache.json`
- `results/candidate_multidimensional_status.csv`
- `results/manual_audit.csv`
- `results/cutoff_vs_evaluation_date_metrics.json`
- `results/metric_sensitivity.json`
- `results/summary.md`

## 实验结果

状态：多维 schema 已设计；E0 已确认 cutoff 配置冲突，正式 registry 冻结和人工复核尚未开始。

