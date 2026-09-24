# E0——版本冻结与一致性审计

## 实验目标

冻结投稿所使用的论文、结果文件、配置和 BOUND adapter。在解释任何新 rebuttal 实验前，确保论文每个表格 cell 都能追溯到明确的文件、字段和聚合规则。

## 实验设计

- 直接解析投稿 TeX 中的 RQ1–RQ3、成本和 HumanEval 表格。
- 从整理后的原始数据索引及底层 JSON/JSONL 文件重新计算表格数值。
- 区分完全一致、末位舍入差异、实质差异和显式 N/A。
- 对全部直接证据文件和 12 个主实验 BOUND LoRA delta 计算 SHA-256。
- 使用 PyTorch 读取每个 delta，记录 tensor 数、目标模块、可训练参数量和文件大小。
- 对比生成论文结果的 cutoff 配置与克隆版 replication package。
- 通过文件哈希和时间戳冻结 Llama-3.1 fold-A run2 的最终版本链路。

## 实验结果

状态：**已于 2026-09-23 完成**。

- 共追溯 321 个论文表格 cell：235 个完全/显示值一致，17 个仅有末位舍入差异，56 个实质或语义差异，13 个显式 N/A。
- 保存的原始结果通过已有验证器：`bad=0, warn=2`。
- 55 个实质差异位于当前 RQ2 四折归档与投稿 RQ2 TeX 之间；另有 1 个差异来自 MEMIT localization time 的 `--` 与 `0.00` 表示口径。
- 12 个主 BOUND delta 均可读取，平均大小为 731.03 KiB；DeepSeekCoder、Qwen3、Llama-3.1 的目标模块数分别为 7、9、7。
- RQ1 curated 与历史 BOUND 文件的 24/24 个指标 summary 完全一致。
- 克隆版 replication package 中 DeepSeekCoder 和 Llama-3.1 的 cutoff 仍与结果生成配置冲突。
- Llama-3.1 fold-A run2 已冻结为 RQ1 最终版本，但由于输出未嵌入不可变 run ID，无法事后区分具体由哪个 GPU evaluator 进程生成。

## 当前结论与决策

在解决 RQ2 版本和 cutoff 配置前，不引用存在差异的 RQ2 cell，也不声称克隆版 artifact 可以精确复现投稿结果。详细证据见 `results/version_discrepancies.md` 和 `results/paper_cell_provenance.csv`。

## 复算命令

```bash
/home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E0_version_audit/script/e0_audit.py
```

