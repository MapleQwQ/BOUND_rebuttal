# E5：Localization 与包有效性区分的四项补充实验

本目录按四个独立问题组织实验。各自的设计、已有结果、待完成工作和过程记录分别在下表所列文件中；现有结果清单由 `script/reanalyse_existing.py` 只读重算，输出统一写入本目录的 `results/01`—`04` 子目录。已完成新增的12折单样本HumanEval、24格同GPU成本重测、定位负对照以及完整序列概率与敏感性分析；论文主表对应的四折HumanEval队列仍在运行。

| 实验 | 核心问题 | 独立设计与结果 | 当前可复用证据 |
| --- | --- | --- | --- |
| 1 All-module LoRA | 宽覆盖 LoRA 的质量、HumanEval 与成本 | [01](01_all_module_lora/design_and_results.md) | 12折单样本HumanEval与24格同GPU成本已完成；10样本×每折1run的论文主表对照运行中 |
| 2 Full risk vs hallucination-only | valid anchor 是否改变定位和最终编辑 | [02](02_risk_score/design_and_results.md) | 12折adapter审计及真正改变模块的两折共同随机数评估已完成；未确认稳定质量收益 |
| 3 定位集中性与稳定性 | 哪些层/模块反复出现，是否具有包幻觉特异性 | [03](03_localization_stability/design_and_results.md) | RQ4及新增valid-only对照完成；热点不专属于hallucination-risk目标 |
| 4 Unseen候选完整序列概率 | Base→BOUND 是否扩大 valid/hallucinated score separation | [04](04_sequence_margin/design_and_results.md) | 原RQ2标签和registry敏感性两套12折评分已完成，历史首发日期已审计 |

## 统一边界与来源

- 以论文三模型、四个edit folds和同一批RQ2 unseen prompts为主。编辑效果对照保持编辑样本、训练loss、rank、学习率、epoch、生成评估规则一致；每折先算，四折等权，再对模型等权。
- 现有历史运行读取 `knowledgeEdit/results/rq3_ablation_20260613` 与 `knowledgeEdit/results/robust_nonedit_highrisk_20260605`；论文RQ3快照中的BOUND指标与历史对应12格逐项相同。RQ4位置数据读取 `knowledgeEdit/results/rq4_localization_analysis_20260615`。
- “定位集中”只证明该风险函数的梯度排名集中，不能单凭热图称已发现稳定的包有效性几何边界。实验4的完整序列分数与实验2的定位分数回答不同问题。
- 所有**新增**模型训练、推理和HumanEval只允许GPU 1、2、3（用户于2026-09-25扩大允许范围）。只读重分析不使用GPU。GPU不可用时约每30分钟复查；每个运行记录GPU、源输入哈希或路径、配置、开始/结束时间和状态。
- `results/04_sequence_margin/candidate_manifest_preliminary.jsonl`沿用原RQ2 cutoff-aware标签、排除四折编辑中出现过的包，作为主分析；当前PyPI快照筛选版`candidate_manifest_registry_screened.jsonl`为敏感性分析。历史首发时间审计支持全部489次valid候选出现早于cutoff；27次当前存在但缓存无日期的hallucinated候选仍未独立核实。分数差异只支持操作层面的区分，不能直接声称确认了稳定几何边界。

## 当前优先顺序

1. 实验1已有12折单样本HumanEval，三个模型的All-module−BOUND配对区间均跨0；同GPU重测表明adapter扩大43–73倍、编辑阶段峰值显存增加7.6–9.1 GiB、总耗时增加约59–65秒。已核对论文主表取每个模型四个编辑折各一次、每题10样本；对应的12个All-module run在GPU 1/2/3并行运行，完成后与论文表格按同fold/run比较。
2. 实验3的同提示valid-only对照已完成，显示full-risk与valid-only热点高度重合；不能宣称包幻觉专属位置。若需更强特异性结论，仍须无关代码任务及同预算编辑效果对照。
3. 实验4已完成Base与四折BOUND同候选teacher-forced评分和prompt配对统计；原RQ2标签主分析的三模型宏平均`Δmargin=+0.735`，95%区间`[0.233,1.280]`；当前PyPI筛选敏感性结果为`+0.908 [0.429,1.464]`。所有候选和逐token分数保留在逐条结果中。

本轮CPU清单复算命令：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E5_localization_evidence/script/reanalyse_existing.py
```
