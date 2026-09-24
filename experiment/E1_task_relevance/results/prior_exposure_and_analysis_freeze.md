# E1 正式标注前分析冻结

冻结时间：2026-09-23 UTC。正式样本生成 seed 为 `20260925`。

## 已知的探索性结果

- 已查看自动存在性指标、部分 folds 的空回答率与热门包集中度。
- 已完成两轮5-prompt试标；round-2 Adequacy κ 为0.839，task-role κ 为0.468。
- 已知 E3 small-100 中不同模型和 folds 的幻觉率与空回答率存在明显异质性。

因此本分析只能称为“正式人工标签揭盲前冻结的预分析计划”，不能称为完全未接触数据的外部预注册。

## 正式样本

- 每模型20个 prompts，共60个任务；这是设计允许的时间受限下界。
- 每个任务包含1条 fresh/既有 Base generation-0，以及四个 BOUND folds 各1条 generation-0，共300条匿名回答。
- 先按模型从四折共同 unseen prompt 交集中稳定随机抽任务，再纳入完整配对条件。
- 排除两轮试标使用过的10个 prompt ID；回答顺序和条件映射已盲化。
- 正式盲键只保存于 `/tmp/e1_formal_blind_key.json`，在两名标注者提交独立原始标签前不得读取或复制到结果目录。

## 冻结的判断与指标

- 使用 `annotation_guideline.md` 中修订后的原子 requirement-slot、候选类型、registry、task-role 与 Adequacy 规则。
- 主要指标：Recommendation Adequacy Rate 以及 prompt 配对的 `BOUND四折均值−Base`。
- 关键次要指标：Inclusive Task-Relevant Precision、必要 slot coverage、Empty/Refusal。
- 不计算 Source-Package Hit 或 Reference Dependency Recall：公开数据没有可核实的 prompt→源包 ground truth。
- `cannot_judge` 不删除；报告比例、已知标签结果和 Base/BOUND 最不利/最有利差异边界。
- Bootstrap 以 task/prompt 为 cluster，Base与四折一同重采样，2,000次，seed `20260925`。
- 非劣性 margin 冻结为5个百分点：只有充分性差异95%区间下界高于 `-0.05`，才支持“在该容忍范围内保持适用性”。该阈值表达每100条回答多5条不充分已是最大可接受损伤；若当前样本无法排除该损伤，结论必须为证据不足，不得事后放宽。

## 停止与扩样

- 本轮固定60 tasks/300 answers，不依据标注效果或显著性扩样、删任务或更换 folds。
- 基础设施或文件损坏只允许恢复同一匿名项目；不能用新任务替代难标或不利项目。
- 一致性按仲裁前的独立标签计算。完成独立标签后才揭盲、仲裁和计算方法差异。
