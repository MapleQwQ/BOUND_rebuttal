# 实验5过程记录

## 2026-09-25：定义混合baseline并核对历史定位输入

- 找到原DINM实现`baselines2/dinm.py::locate_dinm_layers`，其每case层选择依据是合法/幻觉答案的隐藏状态L2距离；原DINM将选中层映射至`model.layers.{layer}.mlp.down_proj`。
- 找到`knowledgeEdit/results/robust_nonedit_highrisk_20260605/{model}/fold_{A-D}/dinm_50/dinm_localization_report.json`全部12份。逐折对照`dinm_requests.json`与原BOUND的`selected_task_recommend_cases.jsonl`，50个case ID的顺序及集合完全一致；因此可复用原实现算出的层号，避免重复定位。
- 用户将此条件命名为E5的05实验，并允许GPU 1、2、3。后续训练从原始模型开始，只改LoRA目标模块，沿用BOUND训练损失与超参数；新脚本、adapter、RQ3结果和日志写在E5的05结果目录。

## 2026-09-25：评估范围按用户最新要求固定为RQ3

- 用户先提出RQ1设置，随后明确改为RQ3设置，并要求暂不测HumanEval。因此正式运行只覆盖原RQ3的每模型四折、每折同一100条unseen prompt×5次生成；与同折BOUND比较。先前RQ1全量unseen规模（541/409/934）仅用于核对，不进入本实验。

## 2026-09-25：脚本与三GPU队列启动

- 新增`../script/run_dinm_layer_bound_edit.py`，逐折核对DINM报告、requests、50个编辑case和原DINM rewrite weight，并记录所有源文件哈希。12折预检通过：DeepSeekCoder各折选层28/30（2个`down_proj`），Qwen3各折选层34（1个），Llama-3.1各折选层31（1个）。这是原DINM定位结果；该baseline的实际LoRA模块数明显少于BOUND，解释时需注明预算差异。
- GPU 1、2、3空闲后分别启动DeepSeekCoder、Qwen3、Llama-3.1的四折队列。每折从基础模型训练BOUND编辑损失，随后评估原RQ3同一100条unseen prompt×5次生成；输出adapter、配置、逐提示结果、编辑成本及队列日志均在`../results/05_dinm_localization_bound_edit/`。当前仅记录启动，不报告未完成的性能值。
