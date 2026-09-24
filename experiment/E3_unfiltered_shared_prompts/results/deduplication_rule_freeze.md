# E3 确认性集合泄漏与去重规则冻结

冻结时间：2026-09-23 UTC；确认性 generation 启动前。

## 对 preliminary manifest 的纠正

先前 small100 脚本错误地把 `LLM_LY_edits_train/valid/test` 全部当成编辑数据排除。`test`/`valid` 中包含未用于参数编辑的高风险提示，因此该做法会重新按风险筛选集合。small100 只保留为暴露这一问题的 preliminary 结果，不再称为确认性 unfiltered sample。

## 确认性排除范围

- 遍历 `knowledgeEdit/results/**/edit_records.jsonl`，覆盖仓库中所有模型、folds、定位、训练、消融和调参运行实际写入的编辑记录。
- 只从 `prompt`/`question` 字段构造排除并集；不排除仅因属于 historical high-risk train/valid/test 而从未进入 `edit_records` 的任务。
- 使用 Unicode NFKC、小写、空白压缩，并移除统一任务前缀后进行 exact-text 对齐。
- 数据源没有稳定 prompt ID 字段，因此 exact ID overlap 无法独立执行；本次使用原始数组 index 作为输出 ID，并通过规范化文本对齐编辑记录。
- 官方数据未发布 prompt→source package/source task 映射，因此 source-group 排除不可执行；这一缺失保留为限制，不能用模型生成包反推分组。

## 近重复规则

- 对规范化文本构造 token 3-gram 集合。
- 仅在两个集合大小比至少0.80时计算 Jaccard。
- Jaccard ≥0.80 进入候选审计；≥0.90 才自动排除。
- embedding 不用于自动排除，避免事后选择 embedding 模型或阈值。
- 本次918个唯一编辑 prompt 与剩余原池比较，没有出现 Jaccard ≥0.80 的非exact候选，因此无人工边界案例，也没有 lexical auto-removal。

## 抽样

- exact排除918条；原池内规范化重复13条；剩余eligible 3,961条。
- 从eligible pool以 seed `20260926` 做一次不放回简单随机抽样，固定200 prompts。
- 200是原计划的预先写明下界，依据 rebuttal GPU预算选择；不是根据 preliminary 效果大小或方向计算出的继续扩样规则。
- manifest 为 `shared_prompt_manifest_confirmatory200.jsonl`；生成后不按 risk、popularity、token length 或结果重抽。
