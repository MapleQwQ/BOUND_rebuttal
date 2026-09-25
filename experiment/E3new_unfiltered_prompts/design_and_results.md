# E3new：未按风险筛选的1,000条主样本与500条独立补充样本

> 2026-09-25 cutoff 校正：replication package 的 DeepSeekCoder/Qwen3/Llama-3.1 cutoff 分别为 2023-10-29/2025-04-29/2023-12-31。此前`results/merged/`使用了错误的 DeepSeekCoder 和 Llama-3.1 cutoff，仅作历史记录；正确cutoff的1000/500/1500条结果分别在`results/cutoff_corrected_1000/`、`results/sample500/merged_500/`、`results/sample500/merged_1500/`。

## 目标与范围

从原始4,892条合成benchmark提示中，去除规范化重复和所有模型/折实际编辑提示后，在3,961条候选中以seed `20260924`简单随机、不放回抽取1,000条。样本不按历史高风险比例配额；DeepSeekCoder、Qwen3、Llama-3.1使用同一批prompt。该设计回答未筛选benchmark上的绝对收益，不代表真实开发者请求分布。

原始Base五次回答文本直接复用；每模型各4个既有BOUND folds，对每条提示重新生成5次。原1000条使用GPU2和GPU3，新增500条使用GPU1、2、3。BOUND生成上限128 tokens，与原始Base脚本默认值一致；temperature=0.7、top_k=40、top_p=0.95，逐条生成seed由`20260926|prompt_id|generation_id`派生。原始Base的随机流不同，不能称逐回答共同seed配对。

补充样本使用相同的源数据及编辑prompt排除规则，再排除原1000条的ID和规范化问题文本，从剩余2961条中以seed `20260925`简单随机抽取500条。新旧样本严格不重叠。三模型各四折在这500条上按原生成设置完成，共30,000条新回答；历史Base文本提供7,500条回答。先独立报告500条，再按prompt层合并为1500条总体；合并结果不能把四折共享的Base误当独立观测。

旧E3 confirmatory-200的BOUND回答使用64-token上限；此次不能直接复用，即使随机样本与其重合58条。原1000条逐条输出在`results/raw/`，补充500条在`results/sample500/raw/`。已校正的原1000条replication package格式结果在`results/cutoff_corrected_1000/{model}/fold_{A|B|C|D}/BOUND/eval_unfiltered_prompts.json`；补充500条及合并1500条将在`results/sample500/merged_500/`及`merged_1500/`。

生成与PyPI标注分开执行。早期已保存回答含原脚本即时PyPI标签；后续回答的标签为临时值。**任何原始输出中的`valid/hallucinated`字段都不能直接用于最终指标**；须先收集全部候选包，通过PyPI JSON API建立首发时间缓存，再用replication package的模型cutoff对Base和BOUND的已生成回答统一重标。历史Base只复用回答文本，不重生成。查询失败的候选单列并做敏感性分析。

## 指标与分析

按照replication package的聚合逻辑，先对每条prompt的5次回答计算Sample-HR、Package-HR、Valid-Rate，再对1,000条prompt取平均；四折等权平均，三模型另报等权平均。每折保留独立结果，不以最优折代替平均。

另报按全部回答累计的指标、每千条含幻觉回答数、无可抽取包率、平均候选包数，以及使用历史Base定义的clean/low/high风险层。以prompt为cluster重采样计算Base与四折BOUND均值的差值区间；区间不覆盖重新编辑、不同模型或真实开发请求。所有结果从逐条trials重算，不使用旧通用评估脚本已知有误的顶层`edited_*` summary。

直接复用Base满足本次执行要求，但不能消除原始Base与新BOUND在采样时间、模型加载路径、随机流和可能的软件环境方面的差异。生成后的包名标签需要单独核对时间口径，不能把“当前索引未列名”“模型cutoff之后才发布”和“从未存在”混称。包名存在性改善也不等于任务适用性提高；E1/E8相关质量审计仍须单独呈现。

## 当前状态

原1000条的12个BOUND条件均已完成，共60,000条新回答；历史Base原始输出提供15,000条回答。新增500条的12个条件也已完成，共30,000条新回答。全部按正确cutoff重新标注并汇总，合并脚本核实所有条件的唯一prompt ID、原文、5个replicate及BOUND逐条seed。旧E3的64-token回答没有混入。

### 论文口径主指标

按replication package的实现，先对每条prompt的5次回答计算指标，再对1000条prompt取平均；BOUND先四折等权平均，跨模型再等权平均。下表的差值为BOUND−Base，负值表示幻觉率下降。

| 模型 | Sample-HR Base→BOUND | 差值及95% prompt bootstrap CI | Package-HR Base→BOUND | Valid-Rate Base→BOUND | 无可抽取包 Base→BOUND |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 9.80%→9.98% | +0.18 pp [−1.04,+1.40] | 5.60%→4.27% | 82.74%→83.46% | 5.40%→11.02% |
| Qwen3 | 6.52%→3.04% | −3.48 pp [−4.69,−2.38] | 3.17%→1.65% | 71.90%→66.41% | 19.94%→30.00% |
| Llama-3.1 | 17.40%→15.09% | −2.32 pp [−3.79,−0.92] | 8.98%→7.33% | 84.40%→81.25% | 4.94%→9.81% |
| 三模型等权 | 11.24%→9.37% | −1.87 pp [−2.74,−1.09] | 5.92%→4.41% | 79.68%→77.04% | 10.09%→16.94% |

三模型等权的回答级事件由每千条生成112.4条降至93.7条，绝对减少18.7条；此数只是上表Sample-HR的另一种单位，不是包mention数。三模型方向不一致：DeepSeekCoder的Sample-HR点估计增加，而Qwen3和Llama-3.1下降。四折异质性需从逐折文件检查，不能只报告四折平均而声称所有编辑模型稳定改善。

Valid-Rate不是任务召回率，也不证明语义适用。尤其Qwen3和Llama-3.1的Valid-Rate下降、三个模型的无可抽取包率均增加；存在性改善伴随输出覆盖风险。当前E3没有人工Adequacy、需求槽覆盖、真实项目依赖命中或执行成功标签，不能据此宣称总体推荐质量提高。此前E1的high-risk人工充分性审计还观察到下降，应与本实验一并呈现。

### 风险层与解释限制

历史Base原标签定义的clean/low/high数量分别为：DeepSeekCoder 776/159/65、Qwen3 879/69/52、Llama-3.1 627/233/140。正确cutoff下，对所有模型，BOUND在历史high层的Sample-HR低于Base；历史clean层的BOUND率为DeepSeekCoder 6.31%、Qwen3 1.81%、Llama-3.1 8.00%。**分层使用的是主对照Base的原始五次回答**；重新标注后，历史clean层的Base率也可能非零。分层仍有回归到均值和同样本定义层的影响，不能把差值直接称作经过独立验证的因果效应。分层数据只作诊断，不替代未筛选总体结果。

### 标注、复用和统计核查

- 原1000条的9127个规范化第三方候选完成PyPI JSON API日期缓存；合并1500条后共12300个候选，5801有首发日期、6379返回not_found、120无可用发布日期，最终无`query_unknown`。缓存文件经去重并存档SHA-256；Base及BOUND所有回答在合并时统一按模型cutoff重标。`not_found`和`no_release_date`沿论文实现计为hallucinated，但两者在审计中分列。
- 原始Base回答文本直接复用，原标签保留于源文件；主表按replication package cutoff对Base及BOUND统一重标。原标签与新标签差异见`results/cutoff_corrected_1000/baseline_relabel_sensitivity.json`。
- 95%区间用2000次prompt-cluster bootstrap；同一prompt的Base、四个BOUND folds及五次生成一起重采样，三模型macro共用prompt索引。区间只反映此benchmark任务组成的不确定性，不覆盖新训练seed、其他模型、真实开发流量或历史Base与新BOUND的生成时点差异。本次1000条样本是在旧200条结果已知后确定的，不能称为未看结果前独立预注册确认。
- 旧E3 confirmatory-200使用fresh Base和64-token BOUND，本次使用历史Base和128-token BOUND；两次结果不可直接合并，也不能把差异归因于单一因素。与replication package论文设置的`top_p=0.9`相比，本次`top_p=0.95`是为了与原始Base筛选脚本保持一致，须在rebuttal中注明。

### 复现入口

- 抽样与排除：`prepare_manifest.py`、`results/sample1000_manifest.jsonl`、`results/manifest_audit.json`；
- 生成：`run_generation.py`、`run_queue.sh`、`results/raw/`及`results/logs/`；
- 日期缓存及统一标注：`build_release_cache.py`、`results/release_dates_final.jsonl`、`results/release_cache_audit.json`；
- 论文格式合并与统计：`merge_and_summarize.py`、`results/cutoff_corrected_1000/{model}/fold_{A|B|C|D}/BOUND/eval_unfiltered_prompts.json`及同目录`paper_style_summary.csv`、`four_fold_macro.json`、`baseline_relabel_sensitivity.json`、`relabel_audit.json`。新增500条及合并1500条使用`results/sample500/`中的相同结构。

`eval_unfiltered_prompts.json`保留replication package的`summary`和`details`结构及论文六项主键；每条detail另有来源字段，注明Base历史复用及BOUND新生成。完整时间线和断点续跑记录见`process_log.md`。

<!-- supplementary-results-start -->
## 补充实验最终结果（正确cutoff）

500条prompt与原1000条在ID和规范化文本上均无重叠。每模型四折，每prompt五次生成；原Base回答文本复用。Base与BOUND全部按replication package cutoff统一标注。表内先按prompt求平均，再按四折及模型等权平均；95% CI为2000次prompt cluster bootstrap。

### 500条prompt

| 模型 | Sample-HR Base→BOUND | 差值及95% CI | Package-HR Base→BOUND | Valid-Rate Base→BOUND |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 11.68%→10.82% | -0.86 pp [-2.63,+0.86] | 6.39%→4.80% | 81.80%→82.10% |
| Qwen3 | 5.68%→2.87% | -2.81 pp [-4.49,-1.33] | 3.11%→1.64% | 68.28%→66.01% |
| Llama-3.1 | 19.24%→14.48% | -4.76 pp [-7.04,-2.42] | 10.14%→7.17% | 84.60%→79.85% |
| 三模型等权 | 12.20%→9.39% | -2.81 pp [-4.24,-1.51] | 6.54%→4.54% | 78.23%→75.99% |

### 1500条prompt

| 模型 | Sample-HR Base→BOUND | 差值及95% CI | Package-HR Base→BOUND | Valid-Rate Base→BOUND |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 10.43%→10.26% | -0.17 pp [-1.27,+0.82] | 5.87%→4.44% | 82.43%→83.00% |
| Qwen3 | 6.24%→2.98% | -3.26 pp [-4.19,-2.30] | 3.15%→1.64% | 70.69%→66.28% |
| Llama-3.1 | 18.01%→14.88% | -3.13 pp [-4.39,-1.92] | 9.37%→7.28% | 84.47%→80.78% |
| 三模型等权 | 11.56%→9.37% | -2.19 pp [-2.88,-1.49] | 6.13%→4.45% | 79.20%→76.69% |

合并1500条后，三模型等权Sample-HR下降2.19个百分点，Package-HR下降1.67个百分点；Valid-Rate也下降2.51个百分点。DeepSeekCoder的Sample-HR差值为−0.17个百分点，95%区间跨0；Qwen3和Llama-3.1的下降更明显。因此不能据总体平均声称三个模型均稳定改善，也不能把较低的幻觉率直接等同于更好的任务适用性。新增500条是在已知原1000条结果之后补充的，不能称为事前独立预注册验证。

PyPI日期缓存涵盖12300个规范化第三方候选，状态分布为{'dated': 5801, 'no_release_date': 120, 'not_found': 6379}；无未知查询。补充样本逐条结果见`results/sample500/merged_500/`，合并结果见`results/sample500/merged_1500/`。原1000条校正结果见`results/cutoff_corrected_1000/`。
<!-- supplementary-results-end -->
