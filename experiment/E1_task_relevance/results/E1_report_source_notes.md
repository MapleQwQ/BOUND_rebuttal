# E1 详细结果报告源说明

## 报告任务

- 受众：论文作者及需要审查实验方法的技术读者。
- 问题：BOUND 降低不存在包推荐后，是否在 high-risk unseen prompts 上保持推荐充分性。
- 主比较：同一模型、同一提示下 Base 与四个 BOUND folds 的等权平均。
- 主终点：Recommendation Adequacy Rate 的 BOUND−Base 配对差异。
- 非劣性标准：预先冻结的 5 个百分点下降容忍界限。

## 图表映射

- `adequacy_chart`：分组柱状图；回答“各模型的 Base 与 BOUND Adequacy 有何差异”；横轴为模型，纵轴为 Adequacy，颜色为条件。使用蓝色系与橙色系区分 Base/BOUND，同时依靠图例和条件名称提供非颜色区分。
- `model_table`：精确列出 Adequacy、区间、slot coverage 与 empty rate；用于查数和审计，不替代主图。
- `agreement_table`：精确列出仲裁前一致性；一致性维度量纲不同，使用表格比混合柱图更诚实。

没有额外绘制 precision 图：核心解释依赖 precision 与 coverage/adequacy 的方向冲突，已通过指标卡、主图和精确表共同呈现；再增加单独图会重复证据。

## 报告结构映射

技术摘要、关键发现、范围与指标定义、实验设计、标注可靠性、限制与稳健性、建议和进一步问题均作为独立可见章节呈现。来源包映射不可恢复是证据限制，不作为顶层数据访问阻塞。
