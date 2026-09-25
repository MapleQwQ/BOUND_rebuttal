# 实验2：Full risk score 与 Hallucination-only score

## 唯一干预

定位阶段原目标为 `R_full = LSE(z[H]) − λ_a LSE(z[G])`，论文配置`λ_a=0.5`、`family_penalty=0`。对照令`λ_a=0`，即`R_hall-only=LSE(z[H])`。两组保持相同模型、每fold的50个编辑case、候选七类linear模块、top-k/窗口规则、随机种子、LoRA rank和**完整训练目标**。注意这里移除的是**定位分数中的valid anchor**，不是训练损失中的valid NLL。

历史`knowledgeEdit/results/rq3_ablation_20260613/{model}/fold_{A-D}/wo_valid_anchor`已实现这一干预：12/12个`localization_report.json`、adapter、配置和RQ3指标齐全。`script/reanalyse_existing.py`核对了报告的anchor系数0.5→0及主要训练超参数一致。Full risk的定位报告和adapter取同fold`robust_nonedit_highrisk_20260605/.../blast_50`；RQ3 BOUND指标与论文快照12格一致。

## 已有结果与能支持的结论

| 模型 | Full risk Sample-HR / Valid-Rate | Hall-only Sample-HR / Valid-Rate | 所选模块Jaccard（四折） |
| --- | --- | --- | --- |
| DeepSeekCoder | 36.20% / 88.35% | 37.85% / 87.60% | 1.00, 0.75, 1.00, 0.75 |
| Qwen3 | 13.00% / 72.65% | 12.10% / 71.70% | 1.00, 1.00, 1.00, 1.00 |
| Llama-3.1 | 47.00% / 86.45% | 53.70% / 81.15% | 1.00, 1.00, 1.00, 1.00 |

现有12折中**10折选择完全相同的实际编辑模块**。进一步逐tensor核对`blast_delta.pt`（`../results/02_risk_score/same_module_adapter_audit.csv`）发现其中**9折adapter完全相同、训练seed相同**；剩余Llama-3.1 fold A虽然模块相同，但Full risk使用seed 43、Hall-only使用seed 42，adapter不同。只有DeepSeekCoder fold B、D的选中模块集合不同（Jaccard均0.75）。因此不能仅凭原RQ3生成指标差异声称valid anchor提高编辑质量。更完整的逐折数值见`../results/02_risk_score/existing_runs.csv`。

对每折两份定位报告所保存的top-200模块排名，在共同模块上计算Spearman相关：DeepSeekCoder、Qwen3、Llama-3.1四折均值分别为**0.999、0.996、0.997**；top-5模块Jaccard均值为**0.833、1.000、1.000**。逐折结果见`../results/02_risk_score/localization_rank_comparison.csv`。这表明valid anchor对当前saliency排序的影响也很小；相关只针对报告保留的top-200共同模块，不代表未保存的完整候选排名。

对同一100条unseen prompt按prompt成组配对bootstrap 10,000次，以下为Hall-only−Full risk差值（百分点）；正的幻觉率差值、负的Valid-Rate差值有利于Full risk。复算见`../results/02_risk_score/paired_rq3_summary.json`。

| 模型 | ΔSample-HR [95% CI] | ΔPackage-HR [95% CI] | ΔValid-Rate [95% CI] |
| --- | ---: | ---: | ---: |
| DeepSeekCoder | +1.65 [-0.95, 4.15] | +1.62 [0.16, 3.10] | -0.75 [-2.25, 0.70] |
| Qwen3 | -0.90 [-2.55, 0.75] | +0.28 [-0.99, 1.60] | -0.95 [-2.30, 0.40] |
| Llama-3.1 | +6.70 [4.05, 9.40] | +7.36 [4.99, 9.76] | -5.30 [-8.05, -2.85] |

**上述CI只描述历史生成输出的差异，不是valid anchor的因果效应区间。** 9折的adapter完全相同，却仍得到不同RQ3生成指标，直接表明独立采样/评估随机性足以产生这些差异。Llama-3.1 fold A还存在训练seed不匹配；因此Llama-3.1的表面优势不能归因于定位风险项。Qwen3四折的module和adapter均相同，当前结果没有显示valid anchor对其编辑模型的贡献。DeepSeekCoder B、D两折存在真实定位差异，但需要同seed、同生成随机数的受控对照才能量化最终质量贡献。

## 真正改变模块折的受控复测

DeepSeekCoder B、D两折的Full与Hall-only原adapter使用相同训练seed与超参数、相同50个编辑case，所选模块集合Jaccard为0.75。`../script/evaluate_risk_common_seeds.py`用原RQ3同一100条unseen prompt×5次采样，在每个相同prompt/generation对上设置相同确定性seed，保留原64新token、temperature 0.7、top-k 40和top-p 0.95。逐提示输出、adapter/input哈希、缓存首发时间新增项均在`../results/02_risk_score/common_seed_eval/full/`；`../script/analyze_risk_common_seeds.py`核对每对seed后按prompt bootstrap 10,000次。以下为Hall-only−Full差值（百分点）：

| 折 | ΔSample-HR [95% CI] | ΔPackage-HR [95% CI] | ΔValid-Rate [95% CI] |
| --- | ---: | ---: | ---: |
| DeepSeekCoder B | +0.40 [-3.40, 4.20] | +0.37 [-2.00, 2.77] | -0.40 [-3.00, 2.20] |
| DeepSeekCoder D | -0.40 [-4.40, 3.40] | -0.38 [-2.51, 1.89] | 0.00 [-2.60, 2.60] |
| 两折等权 | 0.00 [-2.70, 2.60] | -0.01 [-1.56, 1.61] | -0.20 [-2.10, 1.70] |

两折所有区间均跨0，方向也不一致。结合其余9折adapter完全相同、Llama-3.1 A折seed不匹配，**当前实验未能证明valid anchor项提高最终编辑质量**。它确实改变DeepSeekCoder B、D的定位模块，但质量贡献在本设置下无法确认。若论文要保留该项的积极因果表述，需要新的证据；现有结果应诚实报告为未见稳定收益。

## 复算与补充分析

1. 已核对每fold实际模块集合、adapter tensor、seed及已保存top-200共同模块的排名Spearman；未保存的候选尾部排名和绝对saliency尺度不在结论内。
2. 在同一100条unseen prompt×5次生成上计算Sample-HR、Package-HR、Valid-Rate、Empty-Rate；每fold分别报告，再四折宏平均。按prompt配对bootstrap给差值CI，不能把四折当400条独立prompt。若历史文件的生成seed不配对，CI只配对prompt，不声称逐次生成配对。
3. 已确认10个相同模块折中9折adapter完全相同，1折训练seed不同。DeepSeekCoder B、D（真正改变模块的两折）已完成同训练seed及同prompt×generation seed的受控评估，未发现稳定质量差异；相同adapter折说明历史独立采样会产生表面指标差异。
4. 判定语句应随结果：若模块及质量差异很小，则仅说明valid anchor未明显改变本设置的top-k定位；若跨模型、fold出现稳定改善且CI支持，才称full risk有额外贡献。

状态：**历史12折结果、逐提示统计、adapter/seed审计与真实模块变化折的受控重测均完成**。结论为“valid anchor在2/12折改变选中模块，但本实验没有确认其最终质量贡献”。
