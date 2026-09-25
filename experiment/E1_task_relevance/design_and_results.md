# E1——推荐适用性、充分性与退化行为审计

## 实验目标

回答 Reviewer A/B/C 的核心问题：BOUND 降低 registry-existence hallucination 后，是否仍能覆盖任务明确要求的主要依赖，而不是只留下一个真实但不充分的包、热门通用包或空回答。

冻结的确认性假设应写成“存在性风险下降，同时任务适配性在预先定义的容忍范围内得到保持”。只有适配性或覆盖指标本身有统计与实际意义上的改善，才声称“提高推荐有用性”。

## 阶段零：数据源 ground truth 溯源门

在任何试标和 Reference Dependency Recall 计算前，先确认 Spracklen 数据源是否提供 prompt→包名或 prompt→参考依赖映射。当前审计结论如下：

- 官方公开的 `Data/Python/LLM_LY.json` 是逐行 JSON 字符串，每条仅含自然语言 prompt，没有 `package`、`dependencies`、`ground_truth` 或稳定来源 ID 字段。
- 官方 README 只说明 `LLM_LY` 基于“过去一年最热门包”生成，并提供用于存在性检测的 PyPI 包名全集；包名全集不是 prompt 级标准答案。
- Zenodo `Artifacts_Submission.zip` 的中央目录包含 `LLM_LY.json`、`pypi_package_names.csv` 和运行脚本，但未发现 prompt→源包映射、`package_prompts_master` 或参考依赖文件。`generate_code.py` 的注释提到生成 prompt 时曾使用 `package_prompts_master`，说明内部流程可能存在过上游文件，但该文件不在公开 artifact 中。
- 官方 `generate_package_names.py` 仅将 prompt 送入模型以生成推荐包，不读取或保留源包标签。
- 本仓库的 `valid_reference` 不是数据集 ground truth。`extract_high_risk_prompts.py` 先对模型回答抽包并按 PyPI/cutoff 分类，再把多次生成中的真实包取并集；`build_edit_examples.py` 和 `robust_highrisk_experiment.py` 随后把这个并集写入 `valid_reference`。

因此，正式协议采用以下 provenance 分级，并把状态写入冻结 manifest：

| `ground_truth_status` | 含义 | 可否用于 Reference Dependency Recall |
| --- | --- | --- |
| `official_prompt_mapping` | 数据集作者提供且能逐条对齐的映射 | 可以，但仍需审查它是否只是源包而非完整依赖集 |
| `verified_reconstruction` | 可由公开上游文件、稳定顺序和哈希无歧义重建 | 可以，但需公开重建脚本和审计样本 |
| `prompt_explicit_anchor` | 仅从 prompt 明文提到的包名提取 | 不可作为完整 recall ground truth；只可报告锚点命中 |
| `model_generated_valid_reference` | 当前 `valid_reference`：模型曾生成且 registry 中存在 | 不可；只能作为输出保留率等描述性指标的参考 |
| `unavailable` | 无可靠映射 | 不可 |

后续动作：通过论文公开联系人申请未发布的 `package_prompts_master` 或 prompt→源包映射。在收到并完成逐条对齐、版本和语义审计前，不把任何推断出的源包称为 ground truth，也不计算 Source-Package Hit。即使获得源包映射，它最多提供一个生成来源锚点；只有经任务需求审查的参考依赖集合才能用于 Reference Dependency Recall。

详细证据见 `results/source_ground_truth_audit.md`。

## E1 的问题边界

E1 只验证“推荐集合在语义上是否与任务相关、是否覆盖主要依赖需求、是否出现明显退化”。它能够直接回答真实但无关的替换、漏推荐和过度拒答，但不把以下问题包装成已经解决：

- E1 不是用户研究，也不测量真实开发者体验；
- E1 不验证安装、import、API/版本兼容或端到端执行，这些由 E4、E7、E8 补充；
- E1 不把 `adequate` 称为“完全安全”或“代码一定正确”；
- 若仍在原 model-specific high-risk unseen 集上抽样，结论只适用于该风险层，不替代 E3 的未筛选共同集。

| Reviewer 关切 | E1 的交付边界 |
| --- | --- |
| A-Q2：真实但无关的替换 | 由包级任务作用、slot coverage、Adequacy 和退化案例直接回答 |
| B-Q3：来源包关联 | 强制交付来源关联的可恢复性、恢复比例、失败原因；无官方映射时明确报告不可恢复，不用模型输出反推 |
| B：实用性与漏依赖 | 提供专家语义审计证据，但不称为真实项目或用户研究 |
| C-Q4：错误替换与过度拒答 | E1 覆盖语义适用性和拒答副作用；安装、导入、API/版本与执行正确性留给 E4/E7/E8 |

## Requirement slots 的冻结流程

### 先定义需求，再展示回答

对正式样本中的每个 prompt，两位标注者先在看不到 Base/BOUND 回答、模型、fold、`G_i`、`y_i`、`valid_reference` 和 registry 标签的条件下，依据完整任务提示及输出要求独立提取 requirement slots。完成独立提取和仲裁后冻结一份 prompt 级 slot 表；同一 prompt 在所有模型、Base、四个 BOUND folds 和 generations 下共用该表。

来源包描述可以作为理解上下文的证据，但不能自动把来源包变成唯一正确答案；Base 或 BOUND 推荐集合也不得反向决定 slots。

### Slot 的纳入标准

Requirement slot 定义为：**任务明确提出、与依赖选择有关的主要能力或约束，而不是实现任务所需的所有编程步骤。**

每个候选 slot 必须记录：

- `slot_text`：能力或约束；
- `dependency_relevant`：是否合理需要第三方依赖支持；
- `stdlib_or_plain_logic_allowed`：标准库或普通实现逻辑是否足够；
- `explicit_library_constraint`：提示是否明确要求某个库或生态；
- `evidence`：提示片段及必要的可信文档；
- `adjudication_note`：分歧与最终决定。

不把读取、循环、结果组织、保存等普通步骤机械拆成必须由不同第三方包覆盖的槽。对确实无需第三方依赖的任务单独标记 `no_third_party_dependency_needed`。

### Slot 覆盖规则

- 一包可以覆盖多个 slots，多个包也可以共同覆盖一个 slot；
- 只认可官方/可信文档支持的直接功能，或通过正常集成即可实现的用途；
- 不假定回答未提及的大量额外依赖、完整自实现算法或不现实的胶水代码；
- 通用或热门包不自动判错，但必须有证据证明它直接支持当前 slot；
- 合理替代方案可以计入覆盖；若 prompt 明确要求特定库或生态，跨技术栈替换不得无条件视为等价；
- 只有在固定人工审计日期实际存在且任务适用的包才能满足 slot。不存在或无法确认存在的包不能满足 slot。

## 双层盲标体系

registry 存在性由 E7 独立提供。人工审计的实际存在性时间基准冻结为 **2026-09-23 UTC**，并与原论文的 model-cutoff validity 分开保存。cutoff 后发布但截至审计日期真实存在的包，可以参与语义充分性判断，同时保留 `post_cutoff` 标签，不能仅因原 cutoff 规则被当成不存在。

标注者可查询 PyPI、官方文档、项目文档或其他可信资料并记录证据；禁止仅凭包名、模型自述用途或流行度判断。若原回答只有包名列表，标注者可以结合任务和文档推定其支持能力，但必须标记 `purpose_inferred_by_annotator=true`；不得让模型事后生成用途说明后再评价增强后的回答。

### 层次 A：单个包的两个独立维度

存在性和任务作用不得合并成一个互斥标签。

| `registry_status` | 定义 |
| --- | --- |
| `exists_at_audit_date` | 截至 2026-09-23 UTC，权威 registry 证据表明 distribution 已存在 |
| `nonexistent_at_audit_date` | 截至该日期，按 E7 规则有充分证据判定不存在 |
| `registry_cannot_determine` | 网络、元数据、名称映射或其他证据不足，无法确认 |

另存 `cutoff_status = pre_cutoff / post_cutoff / date_unknown`，不改变上述实际存在性标签。

| `task_role` | 可执行定义 |
| --- | --- |
| `core_function_support` | 有可信功能证据，直接支持至少一个预先冻结的必要 dependency-relevant slot |
| `optional_support` | 有可信功能证据且与任务有关，但只提供非必要辅助、便利或增强 |
| `irrelevant` | 不支持冻结需求、违反明确约束，或只是无证据的通用推荐 |
| `cannot_judge` | 完成允许的资料查询后仍无法可靠判断任务作用 |

同时记录覆盖的 `slot_id`、替代关系、证据 URL/版本、置信度和判断耗时。包“必要与否”由完整任务、slot 和替代方案共同决定。只有 `registry_status=exists_at_audit_date` 且任务作用为 `core_function_support` 的推荐才能满足必要 slot；不存在或 registry 未知的包即使名字看起来相关也不能满足 slot。

### 层次 B：整体推荐集合

| 标签 | 可执行定义 |
| --- | --- |
| `adequate` | 至少存在一种合理实现方案；所有冻结的必要 dependency-relevant slots 都由实际存在且适用的推荐包覆盖，并满足明确库/生态约束 |
| `partially_adequate_with_clear_omission` | 至少覆盖一项必要 slot，但仍有至少一项明确必要 slot 未被实际存在且适用的推荐覆盖 |
| `inadequate` | 没有支持任何主要必要 slot，或与任务关键约束明显冲突 |
| `cannot_judge` | 根据允许查询的证据仍无法判定整体充分性 |

“覆盖大部分”只反映在 slot coverage，不足以获得 `adequate`。额外出现一个不存在包不自动把 Adequacy 置零：如果真实且适用的推荐已经覆盖全部 slots，回答仍可在语义覆盖上为 `adequate`，但存在性风险另行计入；如果不存在包是唯一被指望覆盖剩余 slot 的候选，则该 slot 未覆盖。

明确说明“不需要第三方依赖”只有在 `no_third_party_dependency_needed=true` 且理由与任务一致时才可能充分；纯空白、无能力回答或不加说明的拒答不自动充分。

## 两阶段样本设计

### 阶段一：定向试标与校准

试标有目的地覆盖空输出、热门包集中、长回答、多依赖任务、不同包数和高分歧候选，用于暴露规则漏洞、测量耗时和修订指南，不进入正式确认性均值。

额外构造少量不进入正式均值的校准案例：

| 案例 | 预期行为 |
| --- | --- |
| 所有任务都输出同一常见真实包 | 不适用或不足时，相关性/Adequacy 降低 |
| 从充分答案删除唯一支持某必要 slot 的包 | Adequacy 或 slot coverage 降低 |
| 向充分答案添加一个真实但无关的包 | Precision 降低，原覆盖可不变 |
| 用有文档支持的合理替代包覆盖同一需求 | 不因与 reference 名称不同而判错 |
| 充分答案额外包含一个不存在包 | Adequacy 可保持，存在性风险上升 |

两名标注者独立完成 slot、包级和回答级判断，记录每条回答和每个 unique `package + 声明用途` 的耗时、查询次数及分歧。依据试标修订指南后冻结正式版本；试标标签不得复用为确认性结果。

### 阶段二：随机完整配对正式样本

正式样本先随机抽 prompt，再纳入该 prompt 的完整配对条件，不按回答内容、空输出或初步效果挑选：

- 对每个模型先从目标风险层随机固定一批 unseen prompts；该模型的 Base 与四个 BOUND folds 共用这批 prompts；
- 每个 prompt 同时纳入 Base 和四个 BOUND folds；
- 每个条件按预先固定的 seed/索引随机抽相同数量的已有 generations；
- 不要求 Base 回答总数与四折 BOUND 合计回答数相等；统计时先对四折求平均；
- 异常输出定向检查单列为案例审计，不混入正式主均值。

时间受限时的冻结起始方案是每模型 30 prompts、每条件 1 条 generation，共 `3 × 30 × (1 + 4) = 450` 条回答和 900 次独立回答级判断。该规模不预先声称足以证明狭窄 margin 下的非劣性。若试标表明预算不足，可在揭盲前把正式规模冻结在每模型 20–30 prompts；是否增加 prompts 或 generations 同样必须依据耗时与目标区间精度提前决定，不能看到效果后继续扩样。

回答顺序随机化并隐藏模型、方法、fold、registry/cutoff 标签；正式 sample manifest、generation 选择、标注者、指南版本、主要指标、margin 和分析脚本在正式标注前冻结。

## 指标层次与计算规则

### 主要指标

**Recommendation Adequacy Rate**：`adequate` 回答数除以正式样本回答数。主要决策量为 Base→BOUND 的 prompt 配对差异。它衡量语义覆盖，不与“无存在性错误”合并。

### 关键次要指标

1. **Inclusive Task-Relevant Precision**：分母包含回答内去重后的所有推荐候选，包括不存在包和无关包；分子只包含实际存在且标为 `core_function_support` 或 `optional_support` 的包。回答内按冻结的规范化 distribution name 去重，同时保存 raw name。空推荐的回答级 precision 记为未定义，不以 1 计；聚合时同时报告空推荐率和 pooled package-level precision。
2. **Requirement-slot coverage**：被实际存在且适用的推荐覆盖的必要 dependency-relevant slots 数 / 全部必要 dependency-relevant slots 数；无此类 slots 的任务单独报告。
3. **来源/参考覆盖**：Prompt-Explicit Anchor Hit 为现阶段强制交付；记录来源关联能否恢复、恢复比例和无法恢复原因。只有作者映射通过 provenance 审计后才报告 Source-Package Hit；Reference Dependency Recall 只用于人工清理的可靠参考依赖子集，并允许合理替代。

### 退化检查

- Empty/Refusal Rate；
- 明显必要依赖遗漏率、每回答相关包数量；
- 热门包集中度。

热门包本身不构成退化，只有结合低相关性或低 slot coverage 才能解释为通用包塌缩。

### 探索性解释指标

- Strict-core Precision；
- Base→BOUND Jaccard；
- distinct packages；
- model-generated valid package retention。

Strict-core precision 升高可能只是删除有价值的辅助包；Jaccard 或原包保留率下降可能来自合理替代或删除无关真实包。因此不单独把这些变化称为质量损伤。

可另报“`adequate` 且无实际存在性错误”的联合辅助指标，但它不是主要指标。Sample-HR、Package-HR、实际日期存在性和 model-cutoff validity 始终分别报告。

## 四折配对聚合与非劣性

设回答充分性二元变量为 `A`。在模型内，对同一 prompt 先求 Base 与各 BOUND fold 已标注 generations 的平均充分性，再计算：

$$
\widehat{\Delta}_{\mathrm{adequacy}}
=
\frac{1}{n}\sum_{i=1}^{n}
\left(
\frac{1}{4}\sum_{f=1}^{4}\overline{A}^{\,\mathrm{BOUND}}_{i,f}
-\overline{A}^{\,\mathrm{Base}}_i
\right).
$$

四个 fold 的结果和平均结果都必须报告。Base 不能复制四遍并视为四个独立观测。Bootstrap 以 prompt 为 cluster，用同一组索引同时重采样该 prompt 下的 Base、四 folds 和所有已标注 generations；跨模型总体分析若共享原始任务，也保留任务对应关系。

正式目标是**非劣性**而非双向 equivalence。定义可接受下降幅度 `δ > 0`，并在揭盲前给出任务层面的理由。若使用预先约定的 95% 双侧 bootstrap 区间，只有差异区间下界严格高于 `-δ` 才支持该 margin 下的非劣性：

$$
\mathrm{LCB}_{95\%}(\Delta_{\mathrm{adequacy}})>-\delta.
$$

均值下降小于 `δ`、`p > 0.05` 或区间跨 0 均不能自动证明保持。若区间不足以排除超过 margin 的下降，正式结论为“当前审计证据不足以确定是否保持”，不得事后放宽 margin。小样本区间主要反映测试 prompt 组成的不确定性，不覆盖任意重训数据、训练 seed 或适配器的全部不确定性。

## `cannot_judge` 与敏感性分析

不得静默删除未知标签。每项结果同时报告：

1. `cannot_judge` 数量与比例；
2. 仅已知标签上的描述性估计，明确其条件性；
3. Base→BOUND 差异的最不利边界：BOUND 未知判失败、Base 未知判成功；
4. 最有利边界：BOUND 未知判成功、Base 未知判失败。

双方未知都判失败不一定是配对差异的保守下界。包级 precision 和 slot coverage 同样给出未知候选的保守/宽松界。

## 标注独立性、证据复用与一致性

- 两位标注者可复用同一份官方文档事实，以减少重复检索，但不得在独立阶段共享 `core/optional/adequate` 判断；
- 保留两份独立原始标签、证据表、仲裁结果和指南版本；
- 复制或缓存的包用途标签不作为新的独立观察进入一致率计算；
- κ/α 和原始一致率只使用仲裁前、确实由两人独立判断的项目；
- 每条回答的整体 Adequacy 必须独立判断，不能由包级缓存自动复制。

## 冻结与披露

这不是完全未查看数据的事前研究。已知的探索性信息包括 fold A 可能出现 empty rate 和热门包集中度上升，以及现有自动存在性结果。正式文件必须披露这些已知结果。

在人工相关性/充分性标签和方法差异揭盲前，冻结带时间戳的分析计划，至少记录：已查看的探索结果、尚未查看的结果、sample manifest、generation 索引、slots、指南版本、主要/次要指标、`δ`、bootstrap 规则、未知标签规则和停止/扩样条件。内部文档中的“预注册”仅称为“冻结的预分析计划”；只有提交至带时间戳的外部注册平台后才称正式预注册。

## 结论判定

| 结果 | 允许的结论 |
| --- | --- |
| Package-HR 下降，且 Adequacy 差异下界高于 `-δ` | 降低包幻觉，同时在该 margin 和样本范围内保持推荐适用性 |
| Adequacy/slot coverage 本身有支持的改善 | 可以进一步声称提高推荐有用性 |
| 区间不能排除超过 `δ` 的下降 | 证据不足以确定适用性是否保持 |
| Adequacy 明确下降超过 `δ` | 量化并报告存在推荐质量代价，收窄论文结论 |
| Relevant hit 高但 Adequacy 低 | 存在漏推荐，不能称为完整有用回答 |

## 输出

- `results/source_ground_truth_audit.md`
- `results/prompt_ground_truth_provenance.csv`
- `results/source_association_recovery.md`
- `results/pilot_manifest.jsonl`
- `results/calibration_cases.jsonl`
- `results/pilot_timing_and_disagreement.csv`
- `results/annotation_guideline.md`
- `results/prior_exposure_and_analysis_freeze.md`
- `results/formal_sample_manifest.jsonl`
- `results/frozen_requirement_slots.jsonl`
- `results/blinded_answers.jsonl`
- `results/annotator_1_raw_labels.jsonl`
- `results/annotator_2_raw_labels.jsonl`
- `results/shared_evidence_registry.jsonl`
- `results/adjudicated_labels.jsonl`
- `results/formal_annotation_results.csv`（回答级单表；包含两名原始标签、最终仲裁、需求槽、候选包标签、证据及揭盲后的模型/条件信息）
- `results/relevance_metrics_by_model_fold.json`
- `results/relevance_summary.md`
- `results/E1_detailed_report.html`（中文详细结果报告，可移植HTML）
- `results/E1_detailed_report_artifact.json`（报告的规范化数据与结构）

## 方法学依据

- van der Lee 等人的文本生成人工评估最佳实践用于约束标注者、指南、样本、一致性和可复核性报告：https://aclanthology.org/W19-8643/
- Lakens 的区间假设与 equivalence/non-inferiority 说明用于区分“未显著下降”和“有证据支持非劣性”：https://lakens.github.io/statistical_inferences/09-equivalencetest.html
- Center for Open Science 的 preregistration 说明用于区分内部冻结分析计划和带时间戳的正式预注册：https://www.cos.io/initiatives/prereg

## 实验结果

### 1. 结果摘要

E1没有支持“BOUND降低包幻觉，同时保持推荐适用性”这一确认性主张。在60个high-risk unseen任务、300条正式匿名回答中，三模型等权的Recommendation Adequacy由Base的36.67%降至BOUND的25.42%，差值为−11.25个百分点，95% prompt-cluster bootstrap区间为[−20.83,−2.49]个百分点。与此同时：

- requirement-slot coverage由50.97%降至37.74%；
- empty recommendation rate由1.67%升至12.50%；
- Inclusive Task-Relevant Precision反而由60.56%升至68.77%。

这些指标的组合说明：BOUND留下的候选包中，真实且至少与任务有关的包比例更高，但回答更保守、空回答更多，并且更常漏掉完成任务所需的其他依赖能力。因而precision改善不能解释为整体recommendation usefulness改善。

### 2. 校准阶段不进入正式效果估计

正式实验前进行了两轮小规模校准。最终采用的round-2包含5个prompts、10条回答，Adequacy一致率为90.0%（κ=0.839），registry status一致率为86.5%（κ=0.730），task role一致率为62.2%（κ=0.468）。校准暴露并修订了以下规则边界：

- Python标准库与PyPI distribution必须分开记录；
- 真实但与任务无关的包不能因“确实存在”而获得有用标签；
- 通用包只有在文档支持其直接覆盖冻结需求槽时才计入覆盖；
- 一条回答只命中一个相关包，不足以自动判为充分；
- 合理替代方案允许覆盖需求，但不能无条件违反提示中的明确库或生态约束。

校准样本有目的地覆盖难例，只用于修改指南和估算工作量，不进入下面任何正式均值、区间或显著性解释。

### 3. 正式样本与标签规模

正式主样本按模型分别从原high-risk unseen集合随机冻结20个prompts。每个任务包含Base和四个BOUND folds各一条generation-0回答，形成：

| 项目 | 数量 |
|---|---:|
| 模型 | 3 |
| 每模型prompts | 20 |
| 总任务数 | 60 |
| 每任务回答条件 | 5（Base + BOUND A/B/C/D） |
| 总回答数 | 300 |
| Base回答 | 60 |
| BOUND回答 | 240 |
| 候选包/名称 | 960 |
| 冻结requirement slots | 105 |

60个任务中，27个任务包含1个必要依赖槽，23个包含2个，6个包含3个，2个包含4个，1个包含6个；另有1个任务经prompt-only审查判定不需要第三方依赖。需求槽在展示正式回答前冻结，同一任务的Base和四个BOUND folds共用同一槽集合。

初版正式manifest的任务ID意外携带模型名称，因此被降格为模型可见敏感性结果。最终主结果重新使用匿名`TASK-*`标识；两名未接触旧标签的新标注者在看不到模型、Base/BOUND、fold、registry自动标签和揭盲键的情况下独立标注，并由第三名标注者在揭盲前完成仲裁。

### 4. 最终仲裁标签分布

300条回答的最终标签为：

| 条件 | 回答数 | Adequate | Partially adequate | Inadequate | Empty |
|---|---:|---:|---:|---:|---:|
| Base | 60 | 22（36.67%） | 15（25.00%） | 23（38.33%） | 1（1.67%） |
| BOUND四折合计 | 240 | 61（25.42%） | 56（23.33%） | 123（51.25%） | 30（12.50%） |
| 总计 | 300 | 83 | 71 | 146 | 31 |

包级仲裁结果覆盖全部960个候选：

| 维度 | 标签分布 |
|---|---|
| Registry status | 审计日存在758；审计日不存在152；标准库24；外部工具/产品26 |
| Task role | 核心功能支持266；可选辅助419；无关275 |
| Candidate type | distribution name 758；ambiguous name 138；external tool/product 26；stdlib 24；import name 14 |

最终仲裁没有保留包级或回答级`cannot_judge`。这不代表判断天然简单，而是所有初始不确定项都在允许的PyPI、官方文档和项目文档查询后得到仲裁结论；未知项没有从分母中静默删除。

### 5. 主要结果与非劣性判断

| 模型 | Base Adequacy | BOUND四折均值 | 差值 | 95% prompt-bootstrap CI | Base→BOUND slot coverage | Base→BOUND empty |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeekCoder | 40.00% | 25.00% | −15.00 pp | [−30.00,−1.25] pp | 55.42%→44.69% | 0.00%→10.00% |
| Llama-3.1 | 40.00% | 25.00% | −15.00 pp | [−35.00,+5.00] pp | 54.17%→34.38% | 0.00%→8.75% |
| Qwen3 | 30.00% | 26.25% | −3.75 pp | [−16.25,+5.00] pp | 43.33%→34.17% | 5.00%→18.75% |
| 三模型等权macro | 36.67% | 25.42% | −11.25 pp | [−20.83,−2.49] pp | 50.97%→37.74% | 1.67%→12.50% |

冻结的非劣性margin为5个百分点，即只有Adequacy差异区间下界严格高于−5个百分点，才能支持“在该margin内保持适用性”。所有模型和三模型macro的区间下界都低于−5个百分点，因此全部未通过非劣性判定。

统计解释需要区分两件事：

1. DeepSeekCoder和三模型macro的区间上界低于0，支持平均Adequacy下降；Llama-3.1和Qwen3的单模型区间跨0，单独看这两个模型时差异方向仍不确定。
2. DeepSeekCoder和macro的区间上界仍高于−5个百分点，因此不能进一步声称“下降幅度必然超过5个百分点”。正确结论是：观察到平均下降，而且现有证据不能排除超过预设容忍范围的损伤，所以不支持非劣性。

Bootstrap使用2,000次重采样、seed `20260925`，cluster为模型内prompt。同一prompt下的Base、四个BOUND folds及对应标签一起进入同一次重采样；Base没有复制四次后当作独立观察。区间主要反映测试任务组成的不确定性，不覆盖重新训练、不同编辑数据或训练seed的不确定性。

### 6. 逐模型、逐fold结果

下表的BOUND macro先在模型内对四折等权平均。`Relevant hit`只表示回答至少包含一个实际存在且任务相关的候选，不能替代Adequacy。

| 模型 | 条件 | Adequacy | Partial | Inadequate | Slot coverage | Empty | 平均候选数 | Relevant hit | Inclusive precision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeekCoder | Base | 40.00% | 25.00% | 35.00% | 55.42% | 0.00% | 3.35 | 80.00% | 68.66% |
| DeepSeekCoder | BOUND-A | 25.00% | 30.00% | 45.00% | 40.83% | 20.00% | 3.05 | 75.00% | 81.97% |
| DeepSeekCoder | BOUND-B | 30.00% | 40.00% | 30.00% | 50.83% | 0.00% | 3.80 | 95.00% | 75.00% |
| DeepSeekCoder | BOUND-C | 20.00% | 45.00% | 35.00% | 42.92% | 15.00% | 4.00 | 85.00% | 75.00% |
| DeepSeekCoder | BOUND-D | 25.00% | 35.00% | 40.00% | 44.17% | 5.00% | 3.45 | 80.00% | 72.46% |
| DeepSeekCoder | BOUND macro | 25.00% | 37.50% | 37.50% | 44.69% | 10.00% | 3.58 | 83.75% | 76.11% |
| Llama-3.1 | Base | 40.00% | 25.00% | 35.00% | 54.17% | 0.00% | 4.05 | 80.00% | 58.02% |
| Llama-3.1 | BOUND-A | 10.00% | 20.00% | 70.00% | 19.17% | 15.00% | 3.70 | 75.00% | 59.46% |
| Llama-3.1 | BOUND-B | 20.00% | 15.00% | 65.00% | 28.33% | 20.00% | 3.95 | 75.00% | 63.29% |
| Llama-3.1 | BOUND-C | 40.00% | 20.00% | 40.00% | 50.83% | 0.00% | 3.20 | 95.00% | 67.19% |
| Llama-3.1 | BOUND-D | 30.00% | 20.00% | 50.00% | 39.17% | 0.00% | 4.15 | 90.00% | 62.65% |
| Llama-3.1 | BOUND macro | 25.00% | 18.75% | 56.25% | 34.38% | 8.75% | 3.75 | 83.75% | 63.15% |
| Qwen3 | Base | 30.00% | 25.00% | 45.00% | 43.33% | 5.00% | 3.00 | 85.00% | 55.00% |
| Qwen3 | BOUND-A | 30.00% | 20.00% | 50.00% | 41.67% | 10.00% | 2.15 | 70.00% | 62.79% |
| Qwen3 | BOUND-B | 20.00% | 20.00% | 60.00% | 32.50% | 30.00% | 1.55 | 60.00% | 70.97% |
| Qwen3 | BOUND-C | 30.00% | 5.00% | 65.00% | 32.50% | 15.00% | 2.55 | 70.00% | 68.63% |
| Qwen3 | BOUND-D | 25.00% | 10.00% | 65.00% | 30.00% | 20.00% | 2.05 | 65.00% | 65.85% |
| Qwen3 | BOUND macro | 26.25% | 13.75% | 60.00% | 34.17% | 18.75% | 2.08 | 66.25% | 67.06% |

逐折结果显示明显异质性。例如Llama-3.1 fold C的Adequacy与Base相同且没有空回答，而fold A只有10% Adequacy；Qwen3 fold B的inclusive precision达到70.97%，但empty rate为30%、平均只输出1.55个候选、Adequacy只有20%。这进一步证明不能挑选单折或只报告precision来代表BOUND整体效果。

### 7. Precision提高为什么不等于推荐质量提高

三模型等权Inclusive Task-Relevant Precision从60.56%升至68.77%，增加8.21个百分点。该指标的分母包含实际存在、不可用、不存在以及无关候选；分子只包含实际存在且标为核心支持或可选辅助的候选。因此它确实说明BOUND输出中“留下的候选”更少掺杂明显无关或不存在的名称。

但同一批回答中：

- Adequacy下降11.25个百分点；
- slot coverage下降13.23个百分点；
- empty rate增加10.83个百分点；
- 三模型等权平均候选数约由3.47降至3.13；
- Relevant-Package Hit约由81.67%降至77.92%。

一个回答只保留一个真实相关包时，inclusive precision可能等于1，但如果任务的其他必要槽未覆盖，它仍是`partially_adequate_with_clear_omission`。Qwen3 fold B正是这种退化的明显例子。E1因此支持“候选级precision改善伴随回答级coverage损失”，而不支持“推荐整体更有用”。

探索性strict-core precision也不是统一改善：DeepSeekCoder约为35.82%→35.29%，Llama-3.1为25.93%→18.25%，Qwen3为21.67%→30.13%。该指标会奖励删除可选但有价值的辅助包，因此不作为主结论。

### 8. 仲裁前一致性与分歧来源

| 维度 | 单位/N | 精确一致率 | Cohen's κ | 分歧数 |
|---|---:|---:|---:|---:|
| Adequacy | 回答/300 | 89.33% | 0.834 | 32 |
| Registry status | 候选/960 | 98.44% | 0.955 | 15 |
| Task role | 候选/960 | 71.77% | 0.569 | 271 |
| 候选covered-slot集合 | 候选/960 | 92.40% | 0.849 | 73 |
| 回答covered-slot集合 | 回答/300 | 89.33% | 0.863 | 32 |
| 回答-slot二元覆盖 | 回答-slot对/525 | 93.33% | 0.867 | 35 |

主要终点Adequacy具有较高一致性。最难的判断不是包是否存在，而是`optional_support`与`irrelevant`之间的任务角色边界，以及通用包是否能直接覆盖某个原子槽。Registry分歧主要集中在同时可能指代外部产品或distribution的名称，例如`aws-cdk`、`powerdns`、`openstack`和`pugjs`。

一致性全部使用仲裁前的两份独立标签计算；仲裁后共识没有被重新当作独立标注。两名标注者对300条回答均认为可以判断，回答级`cannot_judge`恒为false，因此该维度κ不定义。

### 9. 来源包关联与Reference Recall未计算

正式60个任务的ground-truth provenance审计结果为：

- `official_prompt_mapping=0`；
- `verified_reconstruction=0`；
- `unavailable=60`。

公开Spracklen数据只保留prompt文本；PyPI名称全集不是逐prompt参考依赖，本仓库`valid_reference`又是历史模型输出中registry-valid名称的并集，不能作为ground truth。因此本实验没有用模型输出反推“正确包”，也没有计算Source-Package Hit或Reference Dependency Recall。当前能够可靠报告的是人工冻结需求槽上的覆盖；若作者后续提供`package_prompts_master`或逐prompt来源映射，仍需先验证对齐、版本和“来源包是否等于完整依赖集”，才能补算reference指标。

### 10. 标注CSV与复算文件

所有正式标注已整理为单一回答级文件`results/formal_annotation_results.csv`。该文件包含300行、42列，使用UTF-8 BOM；每行对应一条回答，主要字段包括：

- 匿名回答/任务ID以及揭盲后的模型、prompt、Base/BOUND、fold和generation；
- 原始question、answer和package列表；
- 冻结requirement slots及无需第三方依赖标志；
- 两名标注者的原始Adequacy、覆盖槽、cannot-judge及完整标签JSON；
- 最终仲裁Adequacy、slot coverage和回答仲裁状态；
- 每个候选的registry status、task role、covered slots、证据、仲裁状态与仲裁原因；
- 审计日期及来源结果文件的相对路径。

变长数组和嵌套证据使用JSON字符串保存于CSV单元格，避免宽表丢失包级信息。QA确认300个回答ID唯一，三个模型各100行，Base/BOUND为60/240行，候选计数合计960，Adequacy分布与仲裁JSON完全一致。生成脚本为`script/export_formal_annotations_csv.py`。

### 11. 可支持与不可支持的rebuttal结论

E1能够直接支持以下结论：

> 在本次high-risk unseen人工审计中，BOUND提高了剩余候选的任务相关precision，但Recommendation Adequacy和requirement-slot coverage下降，空回答增加。结果不支持“降低包幻觉同时在5个百分点margin内保持推荐适用性”；它揭示了存在性风险与推荐覆盖之间的utility trade-off。

E1不能单独支持以下结论：

- 不能称为真实开发者用户研究；
- 不能证明包可以成功安装、import、API调用或端到端运行；
- 不能外推至自然开发请求分布；样本仍来自high-risk unseen层；
- 不能声称所有模型、fold或重新训练seed都会产生同样幅度；
- 不能因precision提高而声称recommendation usefulness提高。

对Reviewer A-Q2，结果表明BOUND不只是将不存在包无代价地替换为真实相关包，还会漏掉必要依赖能力。对Reviewer B，E1提供了语义充分性与覆盖审计，但数据源没有逐prompt依赖ground truth，必须透明说明reference recall不可计算。对Reviewer C-Q4，E1量化了错误替换、漏推荐和过度拒答风险，但安装、版本/API兼容和真实执行仍需E4/E8补充。

正式统计摘要见`results/relevance_summary_formal.md`和`results/relevance_metrics_by_model_fold.json/csv`；完整逐回答标签见`results/formal_annotation_results.csv`；中文可移植结果报告见`results/E1_detailed_report.html`。
