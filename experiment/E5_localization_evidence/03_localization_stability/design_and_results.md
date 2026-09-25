# 实验3：定位层/模块的集中性、稳定性和任务关联

## 目标与统计单位

回答“包幻觉风险函数把高saliency集中在哪些层和投影、跨编辑fold是否稳定”。已存RQ4分析包含三模型各200个编辑提示（四折各50条）、每提示top-5及完整候选分数，合计600提示、3000个top-5命中。按**提示**统计命中频率，按**fold**核对top-5集合；不把3000条命中视为3000个独立提示。图上需标注模型层数、归一化层位置、候选投影家族与各家族候选模块基数。

来源：`knowledgeEdit/results/rq4_localization_analysis_20260615/rq4_prompt_level_scores.jsonl`、`rq4_prompt_top5_modules.jsonl`、层/家族频率CSV和`rq4_fold_overlap.csv`。本目录的`../results/03_localization_stability/existing_summary.json`由只读脚本重算摘要。

## 现有描述性结果

| 模型 | 占比最高的投影家族（top-5命中） | 频率最高的5层合计 | 跨fold top-5模块Jaccard均值 |
| --- | ---: | ---: | ---: |
| DeepSeekCoder | `o_proj` 98.3% | 78.3% | 1.000 |
| Qwen3 | `v_proj` 96.7% | 77.4% | 0.778 |
| Llama-3.1 | `v_proj` 98.7% | 92.2% | 1.000 |

DeepSeekCoder主要集中在层11–15附近，Qwen3在14/16/17/18附近，Llama-3.1在9–13附近；精确频数见原RQ4 CSV。fold重合度高描述的是该定位流程对当前编辑样本划分的稳定性，不能直接外推为所有提示或所有“包有效性边界”的稳定几何结构。

## 补强设计

1. 对四折分别报告top-1/top-5层位置和模块家族；在每个提示上归一化top-k命中，再计算模型内平均及按提示bootstrap CI。报告六个非对角fold对的Jaccard、位置偏移和rank correlation，不只取平均。
2. 对相同模型与候选模块空间设置**负对照**：例如仅valid候选的`LSE(G)`定位、随机匹配候选token或与包推荐无关的代码任务。保持提示长度、候选token数、候选模块和梯度聚合方式尽量相同。比较full风险函数在已集中区域的富集量是否超过这些对照；可用按层/家族基数校正后的频率或相同预算随机排名作为参照。
3. 检验定位的任务关联，而非仅看热图：把full风险高排名模块与负对照高排名模块分别作为相同模块数/相近可训练参数预算的LoRA目标，使用同一编辑loss与case；在RQ3 unseen prompts比较package hallucination与Valid-Rate。若选择相同模块或质量无差异，应弱化“包幻觉特异位置”的说法。
4. 将实验2的full与hall-only模块重合纳入解释：目前10/12折完全重合，说明现有top-k位置对valid anchor并不敏感。应检验完整排名和prompt级别分数是否有更细微变化。

## 新增同提示valid-only负对照

`../script/run_valid_only_localization.py`在同一个原RQ4编辑提示、同一模型、相同七类linear候选模块、相同首token约定和`mean(abs(gradient×weight))`评分下，将目标单独设为`LSE(G)`。没有valid reference的提示无法定义该对照，逐条记于`../results/03_localization_stability/valid_only/{model}/skipped_no_valid.jsonl`；只在两种目标都可计算的提示上配对。`../results/03_localization_stability/valid_only_comparison_per_prompt.csv`和summary保存每提示top-1、top-5以及全模块排名比较；95%区间按提示bootstrap 10,000次。

| 模型 | 可配对提示/200 | top-1相同 | top-5 Jaccard [95% CI] | 全模块Spearman |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 190 | 68.9% | 0.719 [0.678, 0.759] | 0.960 |
| Qwen3 | 163 | 54.0% | 0.686 [0.645, 0.725] | 0.955 |
| Llama-3.1 | 188 | 86.7% | 0.863 [0.833, 0.893] | 0.965 |

两种目标都高度集中于原先相同的投影家族：DeepSeekCoder的`o_proj`、Qwen3和Llama-3.1的`v_proj`。valid-only与full-risk的top-5平均重合约3.91–4.55个模块，全排名相关均高于0.95。这说明现有热点位置**并非hallucination-risk目标独有**；它们可能反映更一般的包推荐/语言建模敏感模块。此负对照仍与包推荐任务相关，因此不能排除相对完全无关代码任务的特异性；若要声称“包幻觉专属边界”，还需无关任务与相同预算编辑效果对照。

## 允许的结论

当前已有数据足以说**该风险函数的高saliency模块在给定三个模型、编辑提示和候选空间中集中且跨fold较稳定**。新增valid-only对照显示这些热点并不专属于hallucination-risk目标。实验4可支持未见候选上的操作层面分数区分，但不能将其解释为独立、稳定的表示空间几何边界。若需更强的任务特异性因果主张，仍需无关代码任务和同预算模块编辑对照。

状态：**现有集中性/跨fold摘要和同提示valid-only负对照完成；完全无关任务与同预算编辑因果对照尚未运行**。新增模型计算仅使用GPU 2、3。
