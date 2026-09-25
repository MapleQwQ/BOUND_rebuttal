# E3new：未按风险筛选的1,000条共同提示集

## 目标与范围

从原始4,892条合成benchmark提示中，去除规范化重复和所有模型/折实际编辑提示后，在3,961条候选中以seed `20260924`简单随机、不放回抽取1,000条。样本不按历史高风险比例配额；DeepSeekCoder、Qwen3、Llama-3.1使用同一批prompt。该设计回答未筛选benchmark上的绝对收益，不代表真实开发者请求分布。

原始Base五次回答直接复用；每模型各4个既有BOUND folds，对每条提示重新生成5次。用户指定GPU2和GPU3。BOUND生成上限128 tokens，与原始Base脚本默认值一致；temperature=0.7、top_k=40、top_p=0.95，逐条生成seed由`20260926|prompt_id|generation_id`派生。原始Base的随机流不同，不能称逐回答共同seed配对。

旧E3 confirmatory-200的BOUND回答使用64-token上限；此次不能直接复用，即使随机样本与其重合58条。所有新条件的逐条输出落在`results/raw/`，完整后与原始Base合并成replication package式的`{"summary": ..., "details": ...}`，目录为`results/merged/{model}/fold_{A|B|C|D}/BOUND/eval_unfiltered_prompts.json`。

生成与PyPI标注分开执行。早期已保存回答含原脚本即时PyPI标签；后续回答的标签为临时值。**任何原始输出中的`valid/hallucinated`字段都不能直接用于最终BOUND指标**；须先收集全部候选包，通过PyPI JSON API建立首发时间缓存，然后用同一模型cutoff对全部BOUND回答统一重标。原始Base回答及原始标签按用户要求直接复用，额外披露标签时点差异。查询失败的候选单列并做敏感性分析。

## 指标与分析

按照replication package的聚合逻辑，先对每条prompt的5次回答计算Sample-HR、Package-HR、Valid-Rate，再对1,000条prompt取平均；四折等权平均，三模型另报等权平均。每折保留独立结果，不以最优折代替平均。

另报按全部回答累计的指标、每千条含幻觉回答数、无可抽取包率、平均候选包数，以及使用历史Base定义的clean/low/high风险层。以prompt为cluster重采样计算Base与四折BOUND均值的差值区间；区间不覆盖重新编辑、不同模型或真实开发请求。所有结果从逐条trials重算，不使用旧通用评估脚本已知有误的顶层`edited_*` summary。

直接复用Base满足本次执行要求，但不能消除原始Base与新BOUND在采样时间、模型加载路径、随机流和可能的软件环境方面的差异。生成后的包名标签需要单独核对时间口径，不能把“当前索引未列名”“模型cutoff之后才发布”和“从未存在”混称。包名存在性改善也不等于任务适用性提高；E1/E8相关质量审计仍须单独呈现。

## 当前状态

12个BOUND条件均已完成，每条件1000条prompt × 5次生成，共60,000条新回答；历史Base原始输出直接提供15,000条回答。合并脚本核实全部12个条件的1000个唯一prompt ID、原文、5个replicate及BOUND逐条seed，失败则停止汇总。旧E3的64-token回答没有混入。

### 论文口径主指标

按replication package的实现，先对每条prompt的5次回答计算指标，再对1000条prompt取平均；BOUND先四折等权平均，跨模型再等权平均。下表的差值为BOUND−Base，负值表示幻觉率下降。

| 模型 | Sample-HR Base→BOUND | 差值及95% prompt bootstrap CI | Package-HR Base→BOUND | Valid-Rate Base→BOUND | 无可抽取包 Base→BOUND |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 9.70%→9.94% | +0.24 pp [−1.01,+1.48] | 5.56%→4.26% | 82.74%→83.46% | 5.40%→11.02% |
| Qwen3 | 6.44%→3.04% | −3.40 pp [−4.60,−2.30] | 3.16%→1.65% | 71.90%→66.41% | 19.94%→30.00% |
| Llama-3.1 | 17.36%→15.01% | −2.36 pp [−3.86,−0.94] | 8.96%→7.28% | 84.40%→81.24% | 4.94%→9.81% |
| 三模型等权 | 11.17%→9.33% | −1.84 pp [−2.687,−1.035] | 5.89%→4.39% | 79.68%→77.04% | 10.09%→16.94% |

三模型等权的回答级事件由每千条生成111.7条降至93.3条，绝对减少18.4条；此数只是上表Sample-HR的另一种单位，不是包mention数。三模型方向不一致：DeepSeekCoder的Sample-HR点估计增加，而Qwen3和Llama-3.1下降。四折异质性也明显，例如DeepSeekCoder fold A/D的Sample-HR分别为5.36%/15.64%；Qwen3 fold B的无可抽取包率为49.64%。因此不能只报告四折平均而声称所有编辑模型稳定改善。

Valid-Rate不是任务召回率，也不证明语义适用。尤其Qwen3和Llama-3.1的Valid-Rate下降、三个模型的无可抽取包率均增加；存在性改善伴随输出覆盖风险。当前E3没有人工Adequacy、需求槽覆盖、真实项目依赖命中或执行成功标签，不能据此宣称总体推荐质量提高。此前E1的high-risk人工充分性审计还观察到下降，应与本实验一并呈现。

### 风险层与解释限制

历史Base五次回答定义的clean/low/high数量分别为：DeepSeekCoder 776/159/65、Qwen3 879/69/52、Llama-3.1 627/233/140。对所有模型，BOUND在历史high层的Sample-HR低于Base；历史clean层的BOUND率为DeepSeekCoder 6.30%、Qwen3 1.81%、Llama-3.1 7.91%。**这些分层使用的就是主对照Base的五次回答**，clean层Base率按定义为0，存在回归到均值和同样本定义层的影响，不能把该层差值直接称作经过独立验证的“新增错误因果效应”。分层数据只作诊断，不替代未筛选总体结果。

### 标注、复用和统计核查

- 9127个不同的规范化第三方候选完成PyPI JSON API日期缓存：4559有首发日期、4480返回not_found、88无可用发布日期，最终无`query_unknown`。缓存文件经去重并存档SHA-256；BOUND所有回答在合并时统一按模型cutoff重标。`not_found`和`no_release_date`沿论文实现计为hallucinated，但两者在审计中分列。
- 原始Base回答和原标签按用户要求直接复用。用同一最终日期缓存另行重标历史Base时，三个模型的Sample-HR分别从9.70%变为9.76%、6.44%变为6.52%、17.36%变为17.32%；差异很小，但仍表明原始标签与新查询时点并非完全一致。主表始终使用原始Base标签。
- 95%区间用2000次prompt-cluster bootstrap；同一prompt的Base、四个BOUND folds及五次生成一起重采样，三模型macro共用prompt索引。区间只反映此benchmark任务组成的不确定性，不覆盖新训练seed、其他模型、真实开发流量或历史Base与新BOUND的生成时点差异。本次1000条样本是在旧200条结果已知后确定的，不能称为未看结果前独立预注册确认。
- 旧E3 confirmatory-200使用fresh Base和64-token BOUND，本次使用历史Base和128-token BOUND；两次结果不可直接合并，也不能把差异归因于单一因素。与replication package论文设置的`top_p=0.9`相比，本次`top_p=0.95`是为了与原始Base筛选脚本保持一致，须在rebuttal中注明。

### 复现入口

- 抽样与排除：`prepare_manifest.py`、`results/sample1000_manifest.jsonl`、`results/manifest_audit.json`；
- 生成：`run_generation.py`、`run_queue.sh`、`results/raw/`及`results/logs/`；
- 日期缓存及统一标注：`build_release_cache.py`、`results/release_dates_final.jsonl`、`results/release_cache_audit.json`；
- 论文格式合并与统计：`merge_and_summarize.py`、`results/merged/{model}/fold_{A|B|C|D}/BOUND/eval_unfiltered_prompts.json`、`results/merged/paper_style_summary.csv`、`results/merged/four_fold_macro.json`、`results/merged/baseline_relabel_sensitivity.json`、`results/merged/relabel_audit.json`。

`eval_unfiltered_prompts.json`保留replication package的`summary`和`details`结构及论文六项主键；每条detail另有来源字段，注明Base历史复用及BOUND新生成。完整时间线和断点续跑记录见`process_log.md`。
