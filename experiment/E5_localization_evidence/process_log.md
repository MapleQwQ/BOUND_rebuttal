# E5 总过程记录

## 2026-09-23：原设计

- 将 E5/E6 合并为统一优先级规划，但保留独立目录便于产物管理。
- 将“同模块数”改为核对实际 LoRA 参数预算、projection 类型和矩阵形状。
- 将 `w/o Valid Anchor` 提升为风险分数独立贡献的首要对照。
- 明确 ordinary LoRA/SFT 同时改变损失，不能单独归因定位。
- 为 boundary 分析新增固定候选集合、长度归一化、seen/unseen hallucinated 分层和 valid score retention。
- 明确训练目标下降或表示图分离都不足以单独证明稳定几何边界。
- 当时计划：从delta/config生成预算表，重汇总random/hard-random；查找valid anchor运行，冻结held-out候选后计算score separation。此版已按用户要求改写为四个独立实验。

## 2026-09-24：四项实验拆分与只读资产审计

- 阅读论文approach、RQ3和实验设置，以及当前定位代码：full risk为`LSE(H) − 0.5 LSE(G)`，`wo_valid_anchor`在定位阶段令`anchor_penalty=0`，训练损失权重保持不变。
- 找到现有`wo_localization_all_lora`和`wo_valid_anchor`：均覆盖三模型×四折，12/12个配置和RQ3指标；all-module LoRA已有adapter、timing，但未找到该条件的HumanEval结果。
- 找到RQ4逐提示top-k及fold overlap。已有结果显示投影家族和层位置高度集中；但这不自动证明包幻觉特异性。
- 新建`script/reanalyse_existing.py`，只读历史文件，重算all-module参数/文件大小/RQ3指标、风险对照模块重合、RQ4摘要与unseen候选初稿；结果写入本目录四个`results/`子目录。运行时不使用GPU。
- 新增GPU约束：后续模型运行只用GPU 2和3。每项实验另有独立`process_log.md`，本文件仅记跨实验来源与决策。
- 小规模GPU验证：HumanEval脚本在GPU 2完成1题smoke，完整序列评分脚本在GPU 3完成1提示smoke；两者都仅用于核对模型/adapter加载和输出格式，不作为论文指标。沙箱内CUDA不可见，正式运行须在有GPU访问的环境中执行。

## 2026-09-24：GPU 2/3续跑

- GPU 2启动DeepSeekCoder四折All-module LoRA HumanEval；GPU 3完成三模型×四折的完整候选序列评分，并转入Qwen3/Llama-3.1的All-module LoRA HumanEval。队列仅使用GPU 2、3，模型评分和HumanEval输出均写在E5目录。GPU等待队列以30分钟为间隔复查占用。
- 序列margin的暂定结果和prompt配对区间已写入实验4设计结果文档；cutoff包标签仍需核验，不作为最终边界主张。

## 2026-09-24：全量队列完成与结果汇总

- 12折序列评分和12折All-module LoRA单样本HumanEval均完成，后者在GPU 2、3之间分配；两个E5 GPU队列均正常退出。实验4按prompt配对bootstrap汇总，实验1按题目配对bootstrap与历史单样本Base/BOUND比较。
- HumanEval三个模型的All-module−BOUND区间均跨0，不支持预设的性能下降结论；实验1已有精确的adapter大小/训练参数及历史成本，GPU同负载重测仍待完成。
- 实验4的候选历史标签尚未经模型cutoff首发时间逐项核验，因此虽已取得暂定正margin变化，仍不能作为最终“稳定边界”证明。

## 2026-09-24：原RQ2候选主分析补跑

- 原RQ2标签候选集也在GPU 3完成12折完整序列评分；原先的当前registry筛选结果保留为敏感性分析。历史首发时间缓存交叉审计支持所有valid候选早于原模型cutoff，另记录27次日期未能独立核验的hallucinated候选。原RQ2标签主分析的三模型宏平均margin变化为`+0.735 [0.233,1.280]`。

## 2026-09-24：RQ3两个对照的逐提示区间

- 对All-module LoRA与Hallucination-only风险分数，复用现有RQ3各100条unseen prompt的逐提示输出，按prompt配对、四折等权bootstrap 10,000次；结果与限制写入实验1、2各自的表格。无需追加GPU运行。

## 2026-09-24：定位负对照与风险审计

- 使用GPU 2、3完成三模型600条编辑提示的valid-only定位对照；559条有valid reference并可与原RQ4 full-risk逐提示配对。full-risk和valid-only全模块排名Spearman均超过0.95，热点不专属于hallucination-risk目标。
- 对风险项消融的12折adapter和seed做逐tensor审计：9折Full与Hall-only adapter完全相同，1折相同模块但seed不同，仅DeepSeekCoder B、D模块真正改变。因此先前历史生成差异不能作为风险项的因果质量效应。两项实验文档已按证据收窄结论。

## 2026-09-25：补全长期运行

- 实验1同GPU 24格成本重测全部完成并核对输入、定位模块；All-module编辑阶段显存高约7.6–9.1 GiB、总耗时高约59–65秒、adapter大约43–73倍。
- 实验2对真正改变模块的DeepSeekCoder B、D在同prompt×generation seed下完成原100提示×5次采样，未发现Full risk的稳定最终质量收益，已更正文档。
- 实验4完成前导空格与未归一化分数敏感性分析，宏平均margin变化保持正向。
- 实验1另启动论文HumanEval完整协议：GPU 2跑DeepSeekCoder、GPU 3跑Qwen3 thinking，各四折×5run×164题×10样本；Llama-3.1由等待队列在GPU 2空闲后自动启动。所有长期队列仍在运行，未完成run不进入结论表。

## 2026-09-25：HumanEval主表协议纠正

- 用户要求核对论文是否需要五次重复。查证论文表格与E0逐格来源后确认：每模型四折各选一次、每题10个completion；五次重复与Qwen3 thinking属于历史补充实验而非论文主表。已停止误设的长期队列，部分输出留存、不纳入主表比较。
- 用户允许GPU 1、2、3。三个模型的主表对应四折队列现分别在GPU 1、3、2运行；逐折选用的run编号、seed与历史BOUND对照见实验1过程记录和新脚本。完成后仍需逐题核对、汇总并更新实验1结果表。

## 2026-09-25：四项补充实验结果收束

- 实验1主表同配置12/12个HumanEval单元完成、逐题判分及参数核验通过；配对统计与表格已写入独立设计结果文档。与历史BOUND同fold/run的pass@1比较，Llama-3.1的All-module条件下降1.69百分点，95%题目bootstrap区间[−3.17,−0.24]；DeepSeekCoder和Qwen3区间跨0。
- 实验2的风险项结论保持审慎：历史12折中9折adapter完全相同，真正改变模块的DeepSeekCoder B/D共同随机数重评未发现Full风险稳定优势。实验3的valid-only负对照显示热点不具备包幻觉专属性。实验4的完整序列概率在原RQ2 unseen候选上显示正向valid/hallucinated margin变化，历史包日期不确定项另列敏感性分析。四项的脚本、逐条结果、设计结果和过程记录均在E5目录内；历史只读输入路径已记录。

## 2026-09-25：新增05 DINM层定位+BOUND编辑

- 用户新增05实验，并明确仅沿用RQ3设置、暂不测HumanEval；模型计算可用GPU 1、2、3。
- 已核验仓库原DINM的12份逐case隐藏状态距离定位报告和原BOUND同折50个编辑case ID一一对应。混合条件取原DINM所选层的去重集合，按原DINM的`mlp.down_proj`映射插入BOUND LoRA；训练损失及超参数由原BOUND配置构建。
- 新增`script/run_dinm_layer_bound_edit.py`，在GPU 1/2/3分别启动DeepSeekCoder/Qwen3/Llama-3.1四折队列；每折评估原RQ3同一100条unseen prompt×5次生成。结果写入`results/05_dinm_localization_bound_edit/`，未完成单元不计入结论。
