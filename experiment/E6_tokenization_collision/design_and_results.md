# E6——Multi-token、前缀与 Token Collision 审计

## 实验目标

审计 localization 的第一 token 代理是否与实际包名打分位置一致，以及 multi-token、共享前缀和完全 collision 是否会让风险信号失效。与 E5 共同决定是否值得训练 full-sequence/prefix 变体。

## 实现事实与打分位置审计

当前实现使用 `tokenizer(" " + pkg).input_ids[:1]` 定位，完整包名只在编辑阶段的 sequence-level unlikelihood 中出现。不能只统计 token 数，还需逐项记录：

- 原始包名和 normalization 后名称；
- 实际回答前缀、前导空格策略、special token 和 chat template；
- tokenizer 完整 token IDs/tokens；
- 代码实际取到的 token 位置；
- 该 token 是否确为预期包名的首 token；
- 不同上下文/前缀下 tokenization 是否变化。

## 全量离线审计

对三模型四折全部 $G_i/H_i$ 统计单/multi-token 比例、长度分布、同类共享首 token、valid/hallucinated 跨类共享首 token、去重前后候选数、完全 collision 数和 collision 与下游收益的关系。

必须单独统计极端情况：当

$$G_i^{\mathrm{tok}}=H_i^{\mathrm{tok}},\quad \lambda_a=1$$

时，两项 LSE 完全相消，风险分数及梯度为零。编辑阶段的完整包名 unlikelihood 可以区分名称，但不能补救定位阶段已消失的代理信号。

## 敏感性实验优先级

1. 当前 first-token risk；
2. length-normalized full package sequence log-probability risk；
3. prefix-trie/多 token 聚合 risk，仅在前两项显示实质差异且资源允许时执行。

先在每模型一个预注册 fold 上比较 localization rank overlap、零梯度案例恢复率、运行成本、实际参数预算和 unseen metrics；差异达到预设门槛后再扩展四折。不能根据哪一折结果最好再选择 fold。

## 结论边界

- 当前方法如实称为与 next-token logits 对齐的首 token 代理。
- sequence-level unlikelihood 只说明编辑阶段覆盖完整包名，不消除定位代理的 collision 限制。
- collision 影响小则用比例和敏感性支持；影响明显则收窄声明并提交修订方向。

## 输出

- `results/tokenization_context_audit.csv`
- `results/collision_cases.jsonl`
- `results/zero_gradient_cases.jsonl`
- `results/localization_variant_results.csv`
- `results/summary.md`

## 实验结果

状态：已核实现有实现使用首 token；全量比例、打分位置和 collision 影响尚未计算。

