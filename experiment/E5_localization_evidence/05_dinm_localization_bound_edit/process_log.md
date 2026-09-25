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

## 2026-09-25：12折RQ3完成与三方对照

- 三个GPU队列正常退出，12/12折`run_metadata.json`均标记complete。逐折核对100条原RQ3 unseen prompt、500次生成及实际注入模块数；DeepSeekCoder各折2模块，Qwen3和Llama-3.1各折1模块，adapter和输入SHA-256已记录。
- 新增`../script/analyze_dinm_layer_bound_edit.py`，逐fold核对混合条件与历史BOUND的prompt ID/文本、每prompt五次生成，按prompt配对bootstrap 10,000次；同样从原DINM完整RQ1输出中抽取相同的100条RQ3提示作辅助对照。输出`paired_rq3_per_fold.csv`、`paired_rq3_summary.json`及`cost_per_fold.csv`。
- 混合条件相对BOUND的四折Package-HR在DeepSeekCoder/Qwen3/Llama-3.1分别高9.17/15.06/8.40百分点，Valid-Rate分别低15.00/20.95/12.55百分点；全部95%区间不跨0。Empty-Rate三模型也更高。结果和限制已写入设计结果表。原DINM的某些低幻觉率伴随高空输出率；原DINM与混合条件的训练目标不同，不将辅助差异解释为定位单独效应。
- 成本表中的原DINM定位时间来自历史运行，混合条件编辑时间/峰值显存为本次GPU实测；没有把跨时间/GPU的耗时直接解释为严格速度优势。本次未运行HumanEval，符合用户最新范围。

## 2026-09-25：Llama A折seed纠正

- 最终对照adapter的`blast_config.json`审计发现，Llama-3.1 A折论文BOUND使用训练seed 43，但原`blast_50.yaml`仍记录42；其余11折两者一致。首轮混合baseline的Llama A折从YAML继承42，不满足同折训练seed控制。
- 将该首轮输出保留为`DINM-layer+BOUND-edit_seed42_superseded/`，不再计入正式汇总；运行脚本改为从**实际论文BOUND adapter的`blast_config.json`**读取seed。在GPU 3单独重跑Llama A折seed43，完成后重新计算12折汇总并更新表格。

## 2026-09-25：seed43重跑完成与最终审计

- GPU 3的Llama A折seed43运行完成，summary核对100条提示×5次生成；分析脚本增加逐折检查混合条件训练seed与最终论文BOUND adapter的`blast_config.json`完全一致，12/12格全部通过。
- 重新生成`paired_rq3_per_fold.csv`、`paired_rq3_summary.json`、`cost_per_fold.csv`并更新结果表。Llama混合条件四折Sample-HR 49.30%、Package-HR 30.22%、Valid-Rate 72.65%、Empty-Rate 15.40%。superseded的seed42文件留存但排除。实验05完成。
