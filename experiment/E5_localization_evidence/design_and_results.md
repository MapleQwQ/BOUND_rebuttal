# E5——Localization 独立贡献与 Boundary 证据

## 实验目标

E5 与 E6 采用统一优先级规划，先回答三个问题：定位是否优于同预算随机位置；风险分数设计是否有独立贡献；boundary 是否有独立 held-out 证据。避免同时铺开过多 locator 和 tokenization 变体。

## 问题一：定位是否优于同预算随机位置

核心对照：

1. BOUND localization + 相同 BOUND losses；
2. 多随机 seed 位置 + 相同 BOUND losses；
3. budget-matched broad LoRA + 相同 BOUND losses；
4. all-module LoRA + 相同 BOUND losses，作为实际宽覆盖对照而非纯定位归因；
5. ordinary LoRA/SFT，仅 valid NLL，作为实用 baseline，但不单独用于定位因果归因。

“同模块数”不等于“同参数预算”。每个配置必须报告实际可训练参数量：

$$r(d_{\mathrm{in}}+d_{\mathrm{out}}),$$

并记录 rank、projection 类型、矩阵形状、层位置、扩展后的模块数。定位因果对照尽量同时匹配参数量、projection family 和形状分布；不能在预算明显不同时声称只改变定位因素。

优先复用已有 random/hard-random repeats 和 RQ3/RQ4 结果，先判断已有运行是否真的预算匹配，再决定重训。

## 问题二：风险分数是否有独立贡献

优先恢复或新增 `w/o Valid Anchor`：去掉 valid anchor，但保持编辑损失、数据、参数预算和其他流程不变。该对照直接检验 valid/hallucinated 对比式风险设计。

若比较 gradient norm、gradient×activation、Fisher 或 DINM/CREME-style locator，必须只替换 locator，保持训练目标和更新机制不变。完整 DINM 方法不能作为只改变 locator 的因果证据。

## 问题三：boundary 是否有独立证据

在比较前固定同一组 held-out candidate，Base 与 BOUND 不能各自挑选不同候选。候选拆分为：

- 编辑中出现过的 hallucinated packages；
- 未出现过的 hallucinated packages；
- cutoff 前真实 packages；
- cutoff 后真实 packages（单独解释）；
- valid packages。

指标包括完整序列 log-probability margin、编辑前后变化、AUROC/AUPRC、valid score retention 和 prompt-cluster CI。完整序列分数必须说明是否按 token length 归一化，并同时报告 normalized/un-normalized 敏感性。

若只观察训练目标下降，不能证明独立 boundary；若只画表示分离图，也不能证明稳定几何边界。第一 token 结果称为 operational score separation；representation probe 必须使用独立训练/测试划分和 probe controls。

## 统计与结果呈现

- 每折和每个 random seed 单独报告，不把 seed/fold 当作 prompt 样本扩大显著性。
- 同一 prompt 索引用于各定位方法的 paired bootstrap。
- 报告 localization top-k 跨 fold/seed 的 Jaccard、rank correlation、layer/family 分布。
- 如果 budget-matched random 与 BOUND 无差异，弱化“定位独立贡献”和稳定 boundary 表述。

## 输出

- `results/existing_ablation_reanalysis.csv`
- `results/parameter_budget_manifest.csv`
- `results/budget_matched_comparison.csv`
- `results/valid_anchor_ablation.csv`
- `results/fixed_candidate_manifest.jsonl`
- `results/score_separation.json`
- `results/localization_stability.json`
- `results/summary.md`

## 实验结果

状态：已有 RQ3、random/hard-random repeats 和 RQ4 资产，待先重算实际参数预算与可比性；尚未决定是否需要新增训练。

