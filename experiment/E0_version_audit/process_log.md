# E0——实验过程记录

本文件按时间顺序追加记录，不覆盖或改写之前的过程条目。

## 2026-09-23

- 清点论文、reviewer 意见、replication package、历史结果、baseline delta、Full-FT checkpoint、RQ2/RQ3/HumanEval 输出以及 12 个主 BOUND adapter。
- 确认 12 个 adapter 均可读取，并统计目标模块数和文件大小。
- 运行仓库结果验证器：RQ1 147 行、RQ2 72 个 method-fold、RQ3 60 行、成本算术和 15 个选定 HumanEval summary 均通过，结果为 `bad=0, warn=2`。
- 建立覆盖 321 个 cell 的 TeX→原始结果审计，并将末位舍入差异与实质差异分开。
- 确认 RQ1 Base 使用独立 base evaluation 文件，而不是 edited-model evaluation 中嵌入的 `baseline_*` 字段。
- 审计 Llama-3.1 fold-A run2 时间戳并冻结最终文件哈希。
- 对比原始结果配置和克隆版 replication package 的 cutoff，发现两个冲突。
- 生成 `artifact_manifest.json`、`paper_cell_provenance.csv`、`validation_report.txt` 和 `version_discrepancies.md`。
- 将 E0 迁移到以实验为单位的新目录结构。

## 后续待处理事项

- 确定生成投稿 RQ2 表格的实际结果归档。
- 统一并记录 MEMIT localization time 的表示口径。
- 修正克隆版 cutoff 配置，并补充 cutoff 的定义和来源证据。

