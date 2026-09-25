# 06 Gradient Norm：定位评分消融

## 研究问题

在其余 BOUND 流程固定时，`Mean(|∇R⊙W|)` 相对 `Mean(|∇R|)` 是否改变 top modules 与 RQ3 编辑效果？这是定位评分的受控比较，不改变 package-validity risk、编辑样本、LoRA 或评估规则。

## 设计

- 三模型：DeepSeekCoder、Qwen3、Llama-3.1；每模型 A–D 四折。每折使用原 BOUND 的 50 个 task-recommend 编辑/定位 cases，同一风险函数、有效包锚点和候选 linear projections。
- 对同一梯度，原评分 `Mean(|∇_{W_m}R_i⊙W_m|)`；替换评分 `Mean(|∇_{W_m}R_i|)`。逐 case 取均值，再按原实现对 case 求均值并排序。实验脚本从原定位函数源码精确替换唯一评分表达式，在运行时断言不存在其他源码差异；原仓库定位实现不修改。
- 原 `top_k=5` 和 `window_family`、`window=1` 选模块规则保持一致。分别报告原始 top-5 模块和最终插入 LoRA 的模块集合的 overlap/Jaccard。原规则可能让最终集合大小不同；若发生，明确标记这项预算限制，不能把性能差异全部归因于评分本身。
- 对最终集合数量不同的折，增加相同预算敏感性分析：先按完全相同的 `window_family` 规则得到 Gradient Norm 模块序列。若多于原 BOUND 最终模块数，按排名截到 N 个；若少于 N 个，从同投影家族中按梯度范数排名补足。用相同训练和 RQ3 评估，并核对实际LoRA参数量相等。原规则不变的结果是主实验；补齐/截断结果用于检查模块预算是否驱动质量变化。
- 先重新计算梯度×权重评分，对比历史 BOUND 报告及最终 adapter 所记录的模块集合。只有选中集合一致才训练对照。每折编辑用 rank-8 LoRA、原编辑 losses、学习率、epoch、batch size及其他原 RQ3 参数。Llama A 使用最终 BOUND adapter 的训练 seed 43，其他折 42。
- RQ3 使用同一批 100 条 unseen prompts/折，每条 5 次生成。指标：Sample-HR、Package-HR、Valid-Rate、empty-output rate。前三项完全复用原 RQ3 聚合定义：先算每个 prompt 的五次生成指标，再对 100 prompts 求均值；Package-HR 的 prompt 值为该 prompt 内 hallucinated packages 占所有分类 packages 的比例。`empty-output rate` 严格指原始 `answer` 去空白后为空；另报告 `no-package rate`（未抽取到 package，含合法的 `None`），避免混淆。四折等权宏平均。
- 相对历史 BOUND 逐 prompt 配对；固定四折，对 100 prompt ID 有放回抽样 10,000 次，四折使用相同 ID 索引，取差值的 2.5%/97.5% 分位数作为 95% CI。
- 只使用 GPU 1、2、3。无 GPU 时每 30 分钟重试。

## 结果

运行中。逐折结果将写入 `../results/06_gradient_norm/paired_rq3_per_fold.csv`，模型宏平均和配对 CI 写入 `../results/06_gradient_norm/paired_rq3_summary.json`。每折保留定位报告、模块交集、配置、adapter、RQ3逐提示生成和运行日志。

| 模型 | 原评分 Sample-HR | Gradient Norm Sample-HR | Δ [95% CI] | 原评分 Package-HR | Gradient Norm Package-HR | Δ [95% CI] | 原评分 Valid-Rate | Gradient Norm Valid-Rate | Δ [95% CI] | 原评分 Empty-Rate | Gradient Norm Empty-Rate | Δ [95% CI] | top-5 Jaccard | 最终模块 Jaccard |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |
| DeepSeekCoder | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| Qwen3 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| Llama-3.1 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |

## 复现

```bash
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/run_gradient_norm.py --gpu 1 --models deepseekcoder
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/run_gradient_norm.py --gpu 2 --models qwen3-release
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/run_gradient_norm.py --gpu 3 --models llama3.1-release
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/analyze_gradient_norm.py
# 对实际模块数不等的折，在空闲 GPU 上运行相同预算敏感性分析：
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/run_gradient_norm_matched_budget.py --gpu 2 --model llama3.1-release
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/analyze_gradient_norm.py --matched-budget
```
