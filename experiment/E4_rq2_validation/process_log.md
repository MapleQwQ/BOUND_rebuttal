# E4——实验过程记录

本文件按时间顺序追加，记录 RQ2 版本选择、审计脚本、映射证据、人工样本、分母变化和结果版本。

## 2026-09-23

- 确认 RQ2 Base、BOUND 和 baselines 的逐 generation 原始输出存在。
- E0 发现当前 72 个 method-fold 明细可由 JSONL 复算，但与投稿 TeX 有 55 个实质 cell 差异。
- 明确 `packages_distributions()` 不是全 PyPI 映射表，本地查不到不得判为 hallucinated。
- 新增完整 import path、证据来源、多候选、namespace、unknown 和 ambiguous 状态。
- 将 mapper 人工审核拆为 unique-macro 与 frequency-weighted 两种准确率。
- 在 `ast.parse` 之外加入固定 Python 版本的非执行 `compile`；新增 no-code、trivial、truncated 等完整分母状态。

## 下一步

- 先确定 rebuttal 使用的 RQ2 结果版本并冻结哈希。
- 实现统一输出状态分类器和 AST/compile 审计脚本。
- 构建分层 mapper 标注样本与证据表。
- 使用原 mapper/hybrid mapper 和 unknown 上下界重算 RQ2。

