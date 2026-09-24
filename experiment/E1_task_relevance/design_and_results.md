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

### 校准阶段

5 prompts/10 answers 的 round-2 试标中，Adequacy 一致率为90.0%（κ=0.839），registry status为86.5%（κ=0.730），task role为62.2%（κ=0.468）。该批只用于修订候选类型、标准库、原子slot和真实但无关包规则，不进入正式效果。

### 正式匿名双标

最终正式样本为每模型20个high-risk unseen prompts；每个任务包含Base与四个BOUND folds各一条generation-0，共60 tasks/300 answers/960候选。初版任务ID意外含模型名，已降格为敏感性；正式主结果由两名未接触旧标签的新标注者在匿名 `TASK-*` ID、共同105-slot表下独立完成，并在揭盲前由第三方盲态仲裁。

仲裁前一致性：Adequacy exact=89.33%，κ=0.834；registry exact=98.44%，κ=0.955；task role exact=71.77%，κ=0.569；回答slot-set exact=89.33%，κ=0.863。两名标注者均无回答级 `cannot_judge`。仲裁后为83 adequate、71 partial、146 inadequate。

| 模型 | Base Adequacy | BOUND四折均值 | 差值 | 95% prompt-bootstrap CI | Base/BOUND slot coverage | Base/BOUND empty |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeekCoder | 0.400 | 0.250 | -0.150 | [-0.300,-0.013] | 0.554/0.447 | 0.000/0.100 |
| Llama-3.1 | 0.400 | 0.250 | -0.150 | [-0.350,+0.050] | 0.542/0.344 | 0.000/0.087 |
| Qwen3 | 0.300 | 0.263 | -0.037 | [-0.162,+0.050] | 0.433/0.342 | 0.050/0.188 |
| 三模型等权macro | 0.367 | 0.254 | -0.113 | [-0.208,-0.025] | 0.510/0.377 | 0.017/0.125 |

冻结的非劣性margin为5个百分点。所有模型和macro的区间下界均低于`-0.05`，因此不能支持“在该margin内保持适用性”。DeepSeekCoder与三模型macro的区间上界低于0，支持平均Adequacy下降；但其上界未低于`-0.05`，不能用该区间检验声称下降必然超过5个百分点。Inclusive Task-Relevant Precision 从三模型等权0.606升至0.688，但同时Adequacy、slot coverage下降且empty上升，正好说明precision提高可能来自删除推荐，而不是完整有用性改善。

因此E1直接回答Reviewer A/B的核心担忧：在本high-risk正式审计中，BOUND并非只是无代价地移除不存在包；它平均漏掉更多必要依赖能力。论文结论必须明确量化这一utility trade-off，不能声称“降低幻觉同时保持推荐适用性”。详细结果见 `results/relevance_summary_formal.md`、`relevance_metrics_by_model_fold.json/csv` 与最终匿名双标/仲裁文件。
