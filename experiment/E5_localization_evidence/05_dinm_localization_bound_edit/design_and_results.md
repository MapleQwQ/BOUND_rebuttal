# 实验5：DINM层定位 + BOUND编辑

## 问题与唯一干预

检验将BOUND的模块定位替换为仓库原有DINM隐藏状态距离层定位后，保留BOUND的LoRA注入、valid NLL、hallucinated-package unlikelihood、locality KL及全部训练超参数，RQ3 unseen package质量与成本如何变化。

原定位实现为`baselines2/dinm.py::locate_dinm_layers`：对每个编辑case的合法包答案与幻觉包答案分别取模型各层hidden state，按L2距离最大值选择一层。原DINM的`rewrite_module_tmp`指向该层`model.layers.{layer}.mlp.down_proj`；混合baseline沿用**50个case所选层的去重集合**，对这些`down_proj`插入BOUND的rank-8 LoRA并训练。这里比较的是原DINM层选择及其原始模块映射与BOUND定位的组合效果，实际编辑模块数可能不同；参数预算差异须与性能一起报告。

三模型×四折，沿用论文BOUND的同一50个编辑case、原RQ3相同100条unseen prompts×5次生成。只读取原DINM运行保存的`dinm_localization_report.json`和`dinm_requests.json`，它们由原实现计算，**不使用DINM的直接权重更新或其训练损失**。已核对12/12折DINM requests与BOUND selected edit cases的50个case ID在集合和顺序上完全一致。训练从原始模型开始，LoRA/目标损失/seed等由原BOUND配置构建，只替换`target_modules`。历史DINM定位时间单独标注，新增训练/推理时间实测；不将不同GPU历史时间视为严格同GPU速度对照。

## 评估与结果

1. 每折核对DINM定位报告包含50个逐case层号、方法标识、对应的原编辑case ID和实际`down_proj`模块名；记录输入与报告SHA-256、层频数、模块数、trainable参数和adapter大小。
2. 使用原RQ3的100条unseen prompts×5次生成，计算Sample-HR、Package-HR、Valid-Rate、Empty-Rate。与同折BOUND按prompt成组配对bootstrap 10,000次，四折等权。
3. 成本报告原DINM定位计时、新增BOUND编辑计时、GPU训练峰值显存和adapter MiB。由于模块预算不同，不能把差异完全归因于定位算法的优劣。**本次暂不测HumanEval。**

状态：**设计和历史定位输入核验完成；训练及RQ3评估待运行。** 新增脚本与结果只写E5目录；模型计算仅用GPU 1、2、3。
