# E1 小规模双盲试标结果

## 范围

- 5 个 DeepSeekCoder high-risk unseen prompts；
- 每个 prompt 包含一条匿名 Base 回答和一条 fold-A BOUND 回答；
- 共 10 条回答、37 个唯一回答内包候选；
- 两名独立标注者先冻结 requirement slots，再进行包级和回答级盲标；
- 首批因一名标注者意外看到旧自动 registry 标签而整体降格为 calibration，本文件只汇总完全不重叠的 round-2。

## 仲裁前一致性

| 层级 | 精确一致率 | Cohen's κ |
| --- | ---: | ---: |
| 回答级 Adequacy | 90.0% | 0.839 |
| Registry status | 86.5% | 0.730 |
| Task role | 62.2% | 0.468 |

回答级仅有 1/10 条分歧。Task-role 一致性明显较低，主要来自标准库、import 名、与真实 distribution 相近但不存在的名称，以及“预期用途”与“真实文档能力”的混淆。正式标注前已据此修订 `annotation_guideline.md`。

## 仲裁后 Adequacy

| 条件 | adequate | partially adequate | inadequate | Adequacy Rate |
| --- | ---: | ---: | ---: | ---: |
| Base | 3 | 0 | 2 | 60% |
| BOUND fold-A | 1 | 2 | 2 | 20% |

该差异只用于规则校准和风险预警，不能作为正式效果估计：样本只有 5 prompts、仅含一个模型和一个 fold，且来自 high-risk 层。它与此前 fold-A empty/concentration 信号方向一致，支持继续进行正式配对随机样本审计，而不支持当前就声称 BOUND 普遍降低推荐适用性。

## 本轮产生的规则修改

1. 新增 `candidate_type` 与 `name_relation`；
2. registry 增加 `not_applicable_stdlib` 和外部工具状态；
3. 不存在名称的推测意图写入 `claimed_role/name_relation`，不得作为真实 task support；
4. requirement slots 必须保持原子性；
5. 正式阶段在任务作用校准通过前，不扩大人工样本。

