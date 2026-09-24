# E3——未按风险筛选的共同提示集评估

## 实验目标与结论边界

本实验检验 BOUND 的收益是否仅存在于预先筛选的 high-risk prompts。
实验使用 Spracklen benchmark 中未经 Sample-HR 阈值筛选的共同提示集，但不将其称为自然开发者请求分布，因为这些 prompts 仍是基于特定时间和热门包构建的合成数据。

本实验只能支持如下结论：
1. BOUND 的收益是否扩展到未经风险筛选的 benchmark prompts；
2. BOUND 在低风险和原本 registry-clean prompts 上是否引入回归；
3. 在相同任务集合上，不同模型的绝对收益是否仍然存在。

本实验不能单独估计真实开发者请求中的 package hallucination prevalence。

## 1. Shared unseen prompt set

定义 eligible pool：

\[
\mathcal{D}_{eligible}
=
\mathcal{D}_{unfiltered}
\setminus
\bigcup_{m,f}
\mathcal{E}_{m,f},
\]

其中排除所有用于 editing、localization、hyperparameter selection 和 debugging 的 prompts。

泄漏排除与去重按确定性优先顺序执行：

1. 排除 exact prompt ID overlap；
2. 对 Unicode NFKC、大小写、首尾及连续空白规范化后，排除 normalized exact-text overlap；
3. 若 source task/source package 映射通过 E1 provenance 审计，排除与编辑/定位/调参数据同源的任务组；
4. 使用冻结的 lexical near-duplicate 规则产生候选，再人工确认是否属于同一任务；候选规则、阈值和仲裁规则必须在查看 E3 outcomes 前写入审计文件；
5. embedding similarity 只作为补充审计，默认不自动删除。若实际启用，必须事先冻结 embedding model、cosine threshold 和人工复核规则。

每一步都报告输入数、删除数、剩余数和删除原因。为避免过度去重改变 benchmark 组成，词法或 embedding 相似但任务实质不同的 prompts 保留；不得为了追求“完美去重”大规模删除正常长尾样本。

### Primary unfiltered sample

主测试集只从完成全部 leakage exclusion 后的 eligible pool 中，使用预先冻结的 sampling seed 做一次**不放回简单随机抽样**，并立即冻结 manifest。禁止根据 historical Base risk、package popularity、token length、是否含显式包名或其他属性设置配额，也禁止为保证 `clean/low/high` 各占固定比例而重抽。

### Secondary stratified/long-tail sample

Risk、popularity 和 token length 仅用于主随机样本的事后分层报告。如果长尾样本在主集合中过少，可另建明确标为 secondary 的 oversampled stratified sample；该样本不得替代 primary estimate，并必须使用 inclusion-probability weights 恢复 eligible pool 的总体估计，同时另报未加权分层结果。

## 2. Risk strata

Risk strata 仅用于 secondary analysis，不用于主测试集采样。其定义是硬冻结规则：**只能使用 E3 之前已经生成并保存的原始 high-risk screening outputs，不允许读取 E3 新生成结果后重定义。**

对每个模型和 prompt，使用历史 screening 的 5 次 generations 定义：

- clean: Sample-HR = 0；
- low/moderate risk: 0 < Sample-HR <= 0.5；
- high risk: Sample-HR > 0.5。

即：historical 5 generations 只负责定义 risk stratum；E3 fresh 5 generations 才用于报告 Base 与 BOUND 指标。禁止根据 E3 fresh Base 回答定义“原本正确”后，再在同一批回答上比较 Base/BOUND。

“registry-clean”与“task-appropriate”分别定义：

- **Registry-clean stratum**：对模型 `M`，历史 screening 满足 `HR_M^screen(x)=0`。在该层报告 fresh Base/BOUND HR、induced hallucination、Empty/Refusal 和 package-count change；
- **Task-appropriate stratum**：只能来自 E1 人工 Adequacy 标签或通过 provenance 审计的可信 reference。E3 全量不重新人工标注，只在预先冻结的 nested subset 复用 E1 protocol。

Registry-clean 只表示历史 5 次生成没有存在性错误，不等于推荐与任务适配。

## 3. Sample size and generation protocol

Sample size 在生成前、且在查看任何 E3 BOUND outcomes 之前冻结。先使用历史 screening 数据估计 Base prevalence 和 prompt-level variance；不使用 E3 结果调参。以 unfiltered shared set 上 Sample-HR absolute difference 的目标 95% CI 半宽为依据，结合预先写明的 paired-correlation 假设和 GPU 预算确定 prompt 数 `N`。样本量文件必须保存输入估计、目标半宽、计算/模拟方法、候选 `N` 和最终选择理由。

不得采用“先跑 100 条，效果不明显再加到 300 条”的顺序。停止条件只由冻结的 `N`、允许的基础设施失败补跑规则和预算决定，与显著性或效果方向无关。

所有模型使用相同的 frozen prompt manifest。

对于每个 prompt 和 generation replicate，Base 和所有 BOUND folds 使用相同的预定义 seed schedule、prompt template 和 decoding configuration。

Base 必须 fresh generate，不复用 high-risk screening generations。

### 计算配置优先级

优先完整配置：

- 200–300 个 shared prompts，具体 `N` 由上述精度规划冻结；
- 3 个模型；
- Base + 4 个已有 BOUND folds；
- 每个 prompt/condition 5 次 fresh generations。

若成本过高，降级配置在生成前一次性冻结：

- 仍优先保持 200–300 个 shared prompts 和 3 个模型；
- Base + 1 个**事先指定**且不得依据结果选择的 BOUND fold；
- 每条件 5 次 generations；
- 在另一个较小、预先固定且不与结果方向挂钩的 prompt subset 上运行 4 folds sensitivity。

Reviewer C 的主问题更直接依赖 prompt coverage，因此预算不足时优先保留 shared prompt 数，而不是用更多 folds 换取明显更少的 prompts。降级结果必须明确称为 scope-limited，不把单 fold 区间解释为训练/编辑集不确定性。

### Common random numbers

对每个 `(prompt_id, replicate_id)` 使用预先确定的 seed schedule，例如由固定 global seed 与稳定 prompt ID 派生。Base 和所有 BOUND folds 共享同一 seed schedule、prompt template、decoding config 和最大长度；共享 seed 不表示强求相同输出，而是降低采样噪声并提高复现性。不得因某个 seed 产生异常结果而单独重采样；仅允许按冻结的基础设施失败规则补跑。

## 4. Registry validity

Generation 与 registry labeling 解耦，E7 的 registry/cutoff 审计不得阻塞 E3 generation。输出完成后可分批补充并版本化以下两套标签：

1. model-specific cutoff validity，用于与原论文保持可比；
2. deployment-snapshot validity，使用所有模型共享的 frozen PyPI snapshot，并记录 snapshot date、构建脚本和文件哈希。

Post-cutoff but deployment-snapshot-existing packages 单独报告，不与 never-existing packages 混为一类。跨模型绝对部署收益以共同 snapshot 为主解释；model cutoff 口径只用于复现/对齐原稿。

## 5. Primary endpoint 与自动指标

主要终点：

\[
\Delta_{\mathrm{Sample-HR}}
=
\mathrm{Sample\mbox{-}HR}_{BOUND}
-
\mathrm{Sample\mbox{-}HR}_{Base}.
\]

其中 Sample-HR 的统计单元是单条 generation/response 是否至少包含一个 hallucinated package。完整配置中的 `Sample-HR_BOUND` 先按 fold 分别计算，再对四折等权平均；降级配置只代表预先指定的单 fold。`Δ < 0` 表示 BOUND 改善。分别报告：

- Base Sample-HR；
- BOUND Sample-HR；
- absolute percentage-point change；
- relative change；
- **hallucination-containing responses per 1,000 generations**；
- 95% prompt-cluster bootstrap CI。

Package-HR 为重要 secondary endpoint，并沿用论文原始“先累计包数再求比例、四折后平均”的聚合方式；回答内是否去重必须与原稿实现保持一致并在结果表注明。同时报告 **hallucinated package mentions per 1,000 generations**。前者是含幻觉回答数，后者是幻觉包 mention 数，禁止合并称为含糊的“hallucinated events”。

全量 E3 自动指标固定为：

- Sample-HR 与绝对差；
- Package-HR；
- 上述两种 per-1,000 指标；
- Empty/Refusal Rate；
- Avg Packages；
- distinct packages per 1,000 generations；
- top-1/top-5 package concentration。

所有结果按模型分别报告，再给出等权 macro-average；共同 deployment snapshot 与 model-cutoff 两套标签分表呈现。

## 6. Regression analysis

在 independent historical screening 定义的 registry-clean prompts 上报告：

- fresh Base Sample-HR 和 BOUND Sample-HR；
- **Induced Hallucination Rate on historically clean prompts**：历史 `HR_M^screen(x)=0` prompts 中，BOUND fresh generations 出现至少一个 hallucinated package 的比例；
- paired clean→hallucinated transition：同一 prompt/replicate 下 fresh Base 无幻觉而 BOUND 有幻觉的比例；
- fresh Base/BOUND Package-HR；
- Empty/Refusal change；
- Avg Packages change；
- package replacement/regression rate。

Induced Hallucination Rate 是预先定义的回归诊断，并与 fresh Base 同层结果一起解释，不能把有限随机生成下的任一事件直接写成确定的因果损伤。

E1 中有人工标签、且与 E3 manifest 相交的预注册 nested subset 才进一步报告 Recommendation Adequacy、Inclusive Task-Relevant Precision 和 requirement-slot coverage。E3 主生成和全量自动分析不得等待 E1 人工标注完成。

## 7. Secondary stratified analysis

在不改变主样本权重的情况下，按以下属性进行 secondary analysis：

- historical Base risk；
- source-package popularity；
- package-name token length；
- pre/post-cutoff status；
- registry-clean vs historically hallucination-prone prompts。

所有 secondary analyses 明确标记为 exploratory，并报告实际样本量、stratum 在 eligible pool 和主随机样本中的占比。若使用另行 oversampling 的分层样本，同时报告 sampling weights、加权总体估计和未加权层内估计。

## 8. Cross-model risk-set matrix（Secondary / P1）

该矩阵回应“在其他模型风险集合上交叉评估”，但不得阻塞 Primary unfiltered shared set。作为 secondary/P1，优先运行 off-diagonal cells。

若 eligible 数量允许，每个来源模型风险集固定抽取 100 prompts：DeepSeekCoder-risk、Qwen-risk、Llama-risk。所有 prompts 仍需排除跨模型/折的 editing、localization、tuning 和 debugging 数据及其确认近重复；不足 100 时使用全部 eligible prompts 并显式报告。

对于每个 evaluated model：
- 再次核验已排除所有模型、所有 folds 的 editing/localization/tuning/debugging prompts 并保存全局 exclusion-union 哈希；
- 在其他模型定义的 risk sets 上评估 Base 和 BOUND；
- 报告 risk-set overlap、unique prompts 和每个 cell 的有效样本量。

矩阵定义为：

| Evaluated model | DS risk | Qwen risk | Llama risk |
| --- | --- | --- | --- |
| DeepSeekCoder | diagonal/descriptive | off-diagonal primary cross-risk | off-diagonal primary cross-risk |
| Qwen | off-diagonal primary cross-risk | diagonal/descriptive | off-diagonal primary cross-risk |
| Llama-3.1 | off-diagonal primary cross-risk | off-diagonal primary cross-risk | diagonal/descriptive |

自身风险集可以报告，但必须与真正的 cross-risk transfer 分开；算力紧张时先完成 6 个 off-diagonal cells。

## 9. Statistics

- prompt 为 bootstrap cluster；
- 同一 prompt 下的五次 generation、methods 和 BOUND folds 成组重采样；
- 所有方法使用同一组重采样 prompt 索引；
- Package-HR 在每次 bootstrap 中按原 ratio 重新计算；
- 四折分别报告并计算 macro-average；
- CI 仅反映测试 prompt 组成的不确定性，不代表重新训练或重新选择 edit folds 的不确定性。

Primary analysis 只使用简单随机主样本，不混入 secondary oversample、试运行或 cross-risk matrix。多模型 pooled 分析若共享同一任务，应保持任务对应关系；单模型结果始终保留。

## 10. Outputs

- `results/shared_prompt_manifest.jsonl`
- `results/exclusion_audit.csv`
- `results/deduplication_rule_freeze.md`
- `results/sample_size_plan.md`
- `results/seed_schedule.csv`
- `results/base_fresh_generations/`
- `results/bound_generations/`
- `results/model_cutoff_labels.jsonl`
- `results/deployment_snapshot_labels.jsonl`
- `results/unfiltered_primary_metrics.csv`
- `results/regression_on_clean_prompts.csv`
- `results/metrics_by_risk_and_popularity.csv`
- `results/secondary_sampling_weights.csv`
- `results/e1_nested_subset_manifest.jsonl`
- `results/e1_nested_subset_metrics.csv`
- `results/cross_model_risk_matrix.csv`
- `results/bootstrap_intervals.json`
- `results/summary.md`

## 11. 完成标准

E3 只有在能够直接回答以下问题时才算完成：

1. 未按风险筛选的共同 benchmark 上，包幻觉的绝对发生率是多少？
2. 在完全相同的 prompts 上，BOUND 带来的 Sample-HR 绝对变化是多少？
3. BOUND 是否在历史 registry-clean prompts 上引入新的存在性错误或其他退化？
4. 结论是否在三个模型上成立；作为次要问题，是否能迁移到由其他模型定义的风险集合？

## 实验结果

### DeepSeekCoder small-100 preliminary

状态：已完成一个模型的计算试运行。该集合从 exact/normalized-exact leakage exclusion 后的 eligible pool 简单随机抽取 100 prompts，sampling seed 为 `20260923`；尚未完成 source-group/lexical near-duplicate audit，因此不是最终确认性 E3 主集合。Base 与四个 BOUND folds 均 fresh generate 5 次，global generation seed 为 42，并按 `(prompt_id, replicate_id)` 派生共同 seed。

| 条件 | Sample-HR | Package-HR | Empty rate | Avg packages |
|---|---:|---:|---:|---:|
| Base | 0.030 | 0.016 | 0.060 | 2.502 |
| BOUND fold A | 0.034 | 0.024 | 0.272 | 1.896 |
| BOUND fold B | 0.060 | 0.029 | 0.102 | 2.326 |
| BOUND fold C | 0.030 | 0.014 | 0.084 | 2.656 |
| BOUND fold D | 0.106 | 0.049 | 0.050 | 2.734 |

四折 macro Sample-HR 为 0.0575，相对 Base 的主要差值为 `+0.0275`，2,000 次 prompt-cluster bootstrap 95% CI 为 `[+0.0010,+0.0525]`；正值表示 BOUND 在该 preliminary unfiltered sample 上增加 hallucination-containing responses。Common-seed mismatch 为 0。

这是对“收益是否扩展到未筛选提示”的负面信号，不能表述为 BOUND 改善了 unfiltered 分布。fold 间差异较大，且 fold-A empty rate 明显升高；后续需完成预先规定的 exclusion audit、共同 deployment snapshot 复核和其他模型同协议结果。不得根据当前负结果更换 seed/fold 或决定是否继续扩样。

详细结果见 `results/summary.md`、`results/deepseekcoder_small100_metrics.json` 和 `results/deepseekcoder_small100_metrics.csv`。

### Qwen3 small-100 preliminary

Qwen3 使用同一 preliminary manifest、5 次 fresh generations、四个 folds 和相同 seed schedule：

| 条件 | Sample-HR | Package-HR | Empty rate | Avg packages |
|---|---:|---:|---:|---:|
| Base | 0.022 | 0.014 | 0.228 | 1.918 |
| BOUND fold A | 0.002 | 0.001 | 0.166 | 1.696 |
| BOUND fold B | 0.002 | 0.002 | 0.538 | 1.034 |
| BOUND fold C | 0.012 | 0.010 | 0.370 | 1.828 |
| BOUND fold D | 0.010 | 0.006 | 0.282 | 2.094 |

四折 macro Sample-HR 为 0.0065，相对 Base 的差值为 `-0.0155`，2,000 次 prompt-cluster bootstrap 95% CI 为 `[-0.039,+0.002]`；common-seed mismatch 为 0。点估计方向为改善，但区间跨 0，只能称证据不确定。与此同时 fold B/C/D 的 empty rate 均高于 Base，尤其 fold B 达 0.538，因此不能将较低幻觉率直接解释为推荐质量改善。

详细结果见 `results/qwen3_summary.md`、`results/qwen3_small100_metrics.json` 和 `results/qwen3_small100_metrics.csv`。

### Llama-3.1 small-100 preliminary

Llama-3.1 使用同一 preliminary manifest、5 次 fresh generations、四个 folds 和相同 seed schedule：

| 条件 | Sample-HR | Package-HR | Empty rate | Avg packages |
|---|---:|---:|---:|---:|
| Base | 0.088 | 0.049 | 0.032 | 2.634 |
| BOUND fold A | 0.090 | 0.067 | 0.076 | 2.370 |
| BOUND fold B | 0.156 | 0.113 | 0.228 | 2.800 |
| BOUND fold C | 0.118 | 0.064 | 0.012 | 2.634 |
| BOUND fold D | 0.088 | 0.044 | 0.022 | 2.924 |

四折 macro Sample-HR 为 0.1130，相对 Base 的差值为 `+0.0250`，2,000 次 prompt-cluster bootstrap 95% CI 为 `[-0.0095,+0.0615]`；common-seed mismatch 为 0。点估计方向为退化，但区间跨 0，因此当前样本不能确定存在损伤，也不能支持改善。fold B 的 Sample-HR 和 empty rate 同时明显高于 Base，提示折间异质性和 utility guardrail 风险。

详细结果见 `results/llama31_summary.md`、`results/llama31_small100_metrics.json` 和 `results/llama31_small100_metrics.csv`。

### 三模型 small-100 综合结果

三个模型均已完成 Base 与四个 BOUND folds，每条件 100 prompts × 5 generations，合计 7,500 次生成。15 个条件的 prompt ID 均与 frozen small100 manifest 完全一致，每条 prompt 均有 5 个 trials，common-seed mismatch 为 0。

| 模型 | Base Sample-HR | BOUND 四折 macro | 差值（BOUND−Base） | Base Empty | BOUND Empty macro |
|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | 0.0300 | 0.0575 | +0.0275 | 0.0600 | 0.1270 |
| Qwen3 | 0.0220 | 0.0065 | -0.0155 | 0.2280 | 0.3390 |
| Llama-3.1 | 0.0880 | 0.1130 | +0.0250 | 0.0320 | 0.0845 |
| 三模型等权 macro | 0.0467 | 0.0590 | +0.0123 | 0.1067 | 0.1835 |

联合 bootstrap 在每次重采样中对三个模型、Base 和四折使用同一组 shared-prompt 索引。2,000 次重采样得到三模型等权 macro Sample-HR 差值的 95% CI 为 `[-0.0045,+0.0270]`。Package-HR 的等权 macro 从 0.0263 升至 0.0351，差值 `+0.0089`；Empty rate 的等权 macro 差值为 `+0.0768`。

因此，这个 preliminary small-100 结果不能支持“BOUND 在未按风险筛选的共同提示集上降低 package hallucination”：两个模型的点估计恶化，仅 Qwen3 改善，联合点估计也为恶化方向，但联合区间跨 0。该结论只适用于尚未完成 source-group/lexical near-duplicate 排除的 small100 集合和 model-cutoff labels；不得外推为真实部署分布，也不得通过结果导向地更换 seed、fold 或继续扩样。确认性 E3 仍需完成冻结的 leakage audit、样本量方案与共同 deployment snapshot。

综合机器可读结果见 `results/all_models_small100_metrics.json`，中文摘要见 `results/summary.md`。

### confirmatory-200：纠正泄漏排除后的主结果

完成性审计发现前述small-100错误地排除了`LLM_LY_edits_valid/test`中的全部提示，从而把部分未参与参数编辑的高风险任务也排除，不能视为真正unfiltered。该批结果保留为preliminary，不进入主结论。确认性集合只排除仓库全部24个`edit_records.jsonl`中实际参与编辑的918个唯一提示；原池4,892条，另删除13条规范化池内重复后，eligible pool为3,961条。token 3-gram Jaccard候选阈值冻结为0.80、自动排除阈值0.90，本次没有额外非exact候选；数据源没有source-task/source-package映射，故无法执行同源组排除并作为限制披露。之后以seed `20260926`不放回简单随机抽取200条，不按risk、popularity或token length配额。

三个模型均完成fresh Base与四个BOUND folds，每条件200 prompts×5 generations，共15,000条；所有条件使用相同`(prompt_id, replicate_id)` seed schedule，mismatch为0。

| 模型 | Base Sample-HR | BOUND四折macro | 差值（BOUND−Base） | Base Empty | BOUND Empty macro |
|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | 0.1070 | 0.1035 | -0.0035 | 0.0560 | 0.1167 |
| Qwen3 | 0.0540 | 0.0355 | -0.0185 | 0.2300 | 0.3417 |
| Llama-3.1 | 0.1540 | 0.1685 | +0.0145 | 0.0540 | 0.0900 |
| 三模型等权macro | 0.1050 | 0.1025 | -0.0025 | 0.1133 | 0.1828 |

主要终点的三模型等权绝对差只有`-0.0025`（每千次生成少2.5条含幻觉回答），2,000次共享prompt cluster bootstrap 95% CI为`[-0.0202,+0.0148]`。区间跨0且包含实质恶化与改善，不能支持“BOUND在未筛选共同集上稳定降低Sample-HR”。模型方向也不一致：Qwen3改善1.85个百分点，Llama-3.1恶化1.45个百分点，DeepSeekCoder接近不变。

Package-HR的三模型等权macro由0.0607升至0.0630，与Sample-HR的微小下降方向相反；Empty rate由0.1133升至0.1828。因而即使只看点估计，结果也不支持“总体推荐质量提高”，而更符合收益集中在原high-risk stress-test集合、未筛选集合上绝对收益很小且伴随utility退化的收窄结论。

使用共同的706,618名称冻结snapshot重新标注时，含未列名候选的回答率在三模型等权macro上恰好均为0.0920；逐模型/逐折并非完全相同。`not-listed`只作为共同snapshot风险标志，不被解释为现实中从未存在。模型cutoff标签与共同snapshot标签均保留15,000行，分别见`model_cutoff_labels.jsonl`和`deployment_snapshot_labels.jsonl`。

历史screening-clean回归也不是零风险。historical-clean提示数分别为DeepSeekCoder 149、Qwen3 177、Llama-3.1 122；BOUND四折macro的induced hallucination rate分别为0.0641、0.0246、0.0906，对应fresh Base无幻觉而BOUND有幻觉的配对transition分别为0.0611、0.0232、0.0844。clean子集Empty rate也分别由0.0725→0.1359、0.2542→0.3684、0.0574→0.0795。该结果是回归诊断，不把历史5次clean误称为任务正确或绝对无风险。

确认性manifest、逐步排除审计、样本量说明、15个原始details、双registry标签、完整自动指标和bootstrap结果分别见`shared_prompt_manifest_confirmatory200.jsonl`、`exclusion_audit_confirmatory200.json`、`sample_size_plan.md`、`confirm200_*`、`dual_registry_label_summary.json`与`confirmatory200_metrics.json`。Cross-model risk-set matrix和E1 nested人工充分性属于预先声明的secondary/P1，本轮不作为确认性主结果完成条件，尚未运行。
