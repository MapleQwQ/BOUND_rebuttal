# 实验5：DINM层定位 + BOUND编辑

## 问题与唯一干预

检验将BOUND的模块定位替换为仓库原有DINM隐藏状态距离层定位后，保留BOUND的LoRA注入、valid NLL、hallucinated-package unlikelihood、locality KL及全部训练超参数，RQ3 unseen package质量与成本如何变化。

原定位实现为`baselines2/dinm.py::locate_dinm_layers`：对每个编辑case的合法包答案与幻觉包答案分别取模型各层hidden state，按L2距离最大值选择一层。原DINM的`rewrite_module_tmp`指向该层`model.layers.{layer}.mlp.down_proj`；混合baseline沿用**50个case所选层的去重集合**，对这些`down_proj`插入BOUND的rank-8 LoRA并训练。这里比较的是原DINM层选择及其原始模块映射与BOUND定位的组合效果，实际编辑模块数可能不同；参数预算差异须与性能一起报告。

三模型×四折，沿用论文BOUND的同一50个编辑case、原RQ3相同100条unseen prompts×5次生成。只读取原DINM运行保存的`dinm_localization_report.json`和`dinm_requests.json`，它们由原实现计算，**不使用DINM的直接权重更新或其训练损失**。已核对12/12折DINM requests与BOUND selected edit cases的50个case ID在集合和顺序上完全一致。训练从原始模型开始，LoRA/目标损失/seed等由原BOUND配置构建，只替换`target_modules`。历史DINM定位时间单独标注，新增训练/推理时间实测；不将不同GPU历史时间视为严格同GPU速度对照。

## 评估方法

1. 每折核对DINM定位报告包含50个逐case层号、方法标识、对应的原编辑case ID和实际`down_proj`模块名；记录输入与报告SHA-256、层频数、模块数、trainable参数和adapter大小。
2. 使用原RQ3的100条unseen prompts×5次生成，计算Sample-HR、Package-HR、Valid-Rate、Empty-Rate。与同折BOUND按prompt成组配对bootstrap 10,000次，四折等权。
3. 成本报告原DINM定位计时、新增BOUND编辑计时、GPU训练峰值显存和adapter MiB。由于模块预算不同，不能把差异完全归因于定位算法的优劣。**本次暂不测HumanEval。**

## RQ3结果：同一100条unseen prompt×5次生成

12/12折已完成，每格均有100个原RQ3 unseen prompt、500次生成，prompt ID和文本与同折BOUND逐条匹配。下表为四折等权均值，差值是**DINM层定位+BOUND编辑 − BOUND**，单位为百分点；95%区间按prompt成组配对bootstrap 10,000次，fold固定。完整逐折结果见`../results/05_dinm_localization_bound_edit/paired_rq3_per_fold.csv`，汇总及区间见`paired_rq3_summary.json`。

| 模型 | BOUND Sample-HR | 混合条件 Sample-HR | ΔSample-HR [95% CI] | BOUND Package-HR | 混合条件 Package-HR | ΔPackage-HR [95% CI] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 36.20% | 44.25% | +8.05 [2.50, 13.65] | 16.18% | 25.36% | +9.17 [5.36, 13.12] |
| Qwen3 | 13.00% | 22.90% | +9.90 [4.15, 15.55] | 7.02% | 22.07% | +15.06 [9.76, 20.56] |
| Llama-3.1 | 47.00% | 49.30% | +2.30 [−2.85, 7.35] | 22.04% | 30.22% | +8.18 [4.14, 12.02] |

| 模型 | BOUND Valid-Rate | 混合条件 Valid-Rate | ΔValid-Rate [95% CI] | BOUND Empty-Rate | 混合条件 Empty-Rate | ΔEmpty-Rate [95% CI] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 88.35% | 73.35% | −15.00 [−18.75, −11.30] | 6.95% | 15.20% | +8.25 [5.45, 11.10] |
| Qwen3 | 72.65% | 51.70% | −20.95 [−26.60, −15.20] | 25.50% | 39.20% | +13.70 [7.15, 20.25] |
| Llama-3.1 | 86.45% | 72.65% | −13.80 [−18.20, −9.55] | 9.90% | 15.40% | +5.50 [2.00, 9.20] |

混合条件在三个模型的Package-HR、Empty-Rate均更高，Valid-Rate均更低；DeepSeekCoder和Qwen3的Sample-HR也更高，Llama-3.1的Sample-HR区间跨0。**因此在此RQ3配置下，原DINM层选择加BOUND编辑未达到BOUND定位的质量平衡。** 更高的Empty-Rate还说明只看幻觉率会漏掉输出可用性问题。

作为辅助对照，从原DINM完整RQ1结果中抽取相同100条RQ3 unseen prompt（每条也是5次生成），与同提示混合条件比较。原DINM、混合条件的四折Sample-HR依次为DeepSeekCoder 29.35%/44.25%、Qwen3 73.05%/22.90%、Llama-3.1 3.10%/49.30%；对应Valid-Rate为36.30%/73.35%、74.40%/51.70%、24.90%/72.65%。原DINM在DeepSeekCoder及Llama-3.1的低幻觉率伴随Empty-Rate 55.0%及73.8%，不能单独称为更好。完整三方逐折指标与混合−原DINM的prompt配对区间也保存在上述CSV/JSON。原DINM同时使用不同的直接权重更新目标，此辅助对照**不能**单独归因于编辑损失。

## 定位与成本

原DINM定位报告在50个case上的选层高度集中：DeepSeekCoder四折的去重层均为28和30，Qwen3均为34，Llama-3.1均为31。按原DINM `rewrite_module_tmp`映射后，混合条件实际LoRA模块数分别为**2、1、1**；对应BOUND为**7、9、7**，12折模块名无交集。因而这是忠于原DINM映射的比较，但**同时改变定位方法、层位置和可训练参数预算**，不能把质量差距解释为单一评分函数的纯因果效应。

| 模型 | 混合条件模块/参数/adapter | 原DINM定位时间 | 新增LoRA编辑时间 | 新增编辑峰值reserved显存 |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 2 / 0.242M / 0.46 MiB | 0.94 s | 49.0 s | 13.6 GiB |
| Qwen3 | 1 / 0.131M / 0.25 MiB | 0.93 s | 53.5 s | 17.2 GiB |
| Llama-3.1 | 1 / 0.147M / 0.28 MiB | 0.90 s | 53.3 s | 16.9 GiB |

表中四折等权。定位时间读取原DINM历史运行，新增编辑时间和显存在GPU 1/2/3实测；它们不是一次完整同机重跑的总耗时。逐折原值、输入/adapter SHA-256及GPU编号见`../results/05_dinm_localization_bound_edit/cost_per_fold.csv`。新训练的12个adapter均在本实验结果目录。

**状态：完成。** Llama-3.1 A折按最终论文BOUND adapter的训练seed 43重跑后，12/12折的seed一致性检查通过；首轮seed 42结果保留为`DINM-layer+BOUND-edit_seed42_superseded/`，不进入表格。使用`../script/run_dinm_layer_bound_edit.py`复跑训练和RQ3评估，使用`../script/analyze_dinm_layer_bound_edit.py`复算逐提示差值与区间；本次未运行HumanEval。
