# ICSE 2027 BOUND Rebuttal 实验总计划

> 文档性质：rebuttal 实验索引、优先级与进度入口  
> 最后更新：2026-09-25  
> 当前阶段：仅保留已经开展的实验目录；未开展的方向暂留在本索引中  
> 状态：`[ ]` 未开始，`[~]` 进行中，`[x]` 已完成，`[!]` 存在阻塞或需决策

本文件只保留每个实验的大致内容、依赖、优先级和状态。详细实验设计、指标、统计方法、过程和最终结果均维护在对应实验目录中。

## 1. 总体目标

现有论文主要证明 BOUND 能在三个模型的 model-specific high-risk prompts 上降低 registry-existence 意义的 Package-HR。Rebuttal 补充证据需要回答：

1. 是否同时保持任务相关性和依赖覆盖，而不是空输出、热门包集中或只保留一个相关包；
2. 与 authoritative verifier、PackMonitor 相比，BOUND 是否仍有独立或组合价值；
3. 收益是否扩展到未按风险筛选的共同提示集和其他模型风险集合；
4. RQ2 的代码质量、import 映射和完整分母是否可信；
5. localization、风险分数和 tokenization 代理是否具有独立证据；
6. cutoff、alias、namespace、post-cutoff package 等标签边界是否可靠；
7. 是否能提供小规模真实任务、HumanEval 和更大模型的补充证据。

## 2. 目录规范

已开展的 rebuttal 实验放在 `experiment/` 下，每个实验一个英文目录；**尚未开展的方向不预先保留空文件夹**：

```text
experiment/
├── E0_version_audit/
├── E1_task_relevance/
├── E2_verifier_packmonitor/
├── E2new_verifier/
├── E3_unfiltered_shared_prompts/
├── E3new_unfiltered_prompts/
├── E4new_Syntactic_Validity/
├── E5_localization_evidence/
├── E6_tokenization_collision/
└── E7_RQ2_pacakge_mapper/
```

每个实验目录固定包含：

```text
E*_english_name/
├── results/                  # 原始输出、派生指标、manifest 和最终汇总
├── script/                   # 该实验可复算脚本
├── design_and_results.md     # 中文：详细设计、冻结决策和最终实验结果
└── process_log.md            # 中文：按时间顺序记录实验过程
```

维护规则：

- 两个 Markdown 文档和本总计划均使用中文；目录名、脚本名和机器字段可使用英文。
- `process_log.md` 只按时间追加，不删除失败记录或改写历史过程。
- `design_and_results.md` 在实验前冻结详细设计，实验后追加结果、限制和可用于 rebuttal 的结论。
- 不覆盖 `../knowledgeEdit/results/` 等历史结果；新输出只写入对应实验的 `results/`。
- 每项实验保存输入哈希、代码 commit、resolved config、模型版本、seed、运行时间和失败状态。

## 3. 全局测量与统计原则

- 主 Package-HR 沿用论文口径：每折累计 hallucinated/全部 classified packages 的比值，再对四折取 macro-average；回答内按原集合规则去重。
- bootstrap 以 prompt 为 cluster；同一 prompt 下的重复生成、folds、方法和模型保持成组，并在每次重采样后重新计算 ratio。
- 四折和每个随机 seed 单独报告；prompt bootstrap 不代表重新训练或编辑集选择的不确定性。
- “至少一个相关包”只称为 Relevant-Package Hit，不代表完整推荐质量；依赖覆盖由 Recommendation Adequacy 和可靠 reference 子集上的 Reference Dependency Recall 衡量。
- `cannot-judge`、无代码、截断、映射未知、网络失败和零分母均保留在完整分母或明确的敏感性分析中。
- E1 若声称“保持适用性”，必须预先冻结并论证 non-inferiority margin；未发现显著差异不等于非劣。
- 只有适配性/覆盖指标本身有支持的改善，才声称“提高推荐有用性”。
- 人工一致率使用仲裁前标签计算；人工适配性审计不称为用户研究。

## 4. 实验索引

### E0：版本冻结与一致性审计

- 目标：建立论文 cell→原始结果 provenance，冻结主 adapter、cutoff 和结果版本。
- 状态：`[x]` 已完成。
- 关键发现：321 cells 中 55 个 RQ2 实质差异、1 个成本语义差异；克隆版两个 cutoff 冲突；12 个 BOUND delta 均可读取。
- 详细文档：[E0 设计与结果](experiment/E0_version_audit/design_and_results.md)；[E0 过程记录](experiment/E0_version_audit/process_log.md)。

### E1：推荐适用性、充分性与退化审计

- 目标：同时衡量单包相关性、整体依赖需求覆盖、漏推荐、空输出和热门包集中。
- 前置步骤：先审计数据集是否提供 prompt→包名/参考依赖 ground truth；目前公开 `LLM_LY` 不含该映射，现有 `valid_reference` 是模型输出派生值，不能作为标准答案。
- 先在看不到回答时冻结每个 prompt 的依赖需求槽，再做双人试标；正式阶段随机抽 prompt，并完整配对 Base 与四个 BOUND folds，异常案例不混入主均值。
- 主要指标为 Recommendation Adequacy；inclusive relevance、slot coverage 和来源/参考覆盖作为关键次要指标，并与实际存在性及原 cutoff 标签分开。
- 使用 prompt 配对 bootstrap 和预先论证的 non-inferiority margin；允许“证据不足以确定是否保持”的正式结论。
- 状态：`[x]` 已完成60任务、300回答的最终匿名双标与独立仲裁；任务标识和模型/方法/折映射均在盲标后恢复。Adequacy精确一致率89.33%、κ=0.834；三模型等权Adequacy由Base 0.367降至BOUND 0.254，5个百分点非劣性标准不成立。
- 详细文档：[E1 设计与结果](experiment/E1_task_relevance/design_and_results.md)；[E1 过程记录](experiment/E1_task_relevance/process_log.md)。

### E2：Verifier、PackMonitor 与 BOUND 对照

- 目标：分别回答“参数编辑 × 外部验证”和“BOUND × PackMonitor”。
- PackMonitor 兼容性试运行是重点任务；必须真实执行生成中约束解码。
- one-shot repair 的最终回答必须重新验证，并显式记录 filter/refusal/failure 终态。
- 已完成三模型×四折×100 prompts 的 one-shot repair sensitivity；历史在线标签冲突使旧post-hoc表仅作探索性描述。
- PackMonitor官方commit已冻结；在共同支持的`pip install`协议上完成DeepSeekCoder 100-task原生生成中约束，并加入BOUND fold-A+PackMonitor组合。Base→PackMonitor的invalid率为0.45→0.04，BOUND→BOUND+PackMonitor为0.29→0.04；残余4%均为64-token预算截断的包名前缀。
- 状态：`[x]` 小规模对照已完成。结论限定于registry成员约束和共同安装命令语法；Adequacy、执行正确性及E7时间快照仍分别报告，不由本实验替代。
- 详细文档：[E2 设计与结果](experiment/E2_verifier_packmonitor/design_and_results.md)；[E2 过程记录](experiment/E2_verifier_packmonitor/process_log.md)。

### E3：未按风险筛选的共同提示集

- 目标：证明收益不只存在于预筛 high-risk prompts；不将合成 benchmark 称为自然分布。
- Primary 从完成跨模型/折 leakage exclusion 的 eligible pool 中做一次简单随机抽样；risk/popularity/token length 只用于事后分析，不决定主样本配额。
- 主终点为 Sample-HR 绝对差；历史 screening 只定义 risk strata，E3 使用 fresh Base/BOUND generations，并在 historical-clean prompts 上报告 induced hallucination。
- 候选规模为 200–300 shared prompts；优先 Base+4 folds×5 generations，预算不足时预先指定单 fold并在较小固定子集做四折 sensitivity。
- Generation 不等待 E7：后续同时标注 model-cutoff validity 和共同 deployment snapshot validity；cross-risk matrix 与 E1 nested Adequacy 均为 secondary。
- 状态：`[x]` 主实验已完成。纠正后的eligible pool为3,961条，从中简单随机冻结200条；三模型Base+四折共15,000次fresh generations、双registry标签与共享prompt bootstrap均已完成。Cross-model risk matrix与E1 nested人工子集保留为secondary/P1，未纳入本轮主完成条件。
- 详细文档：[E3 设计与结果](experiment/E3_unfiltered_shared_prompts/design_and_results.md)；[E3 过程记录](experiment/E3_unfiltered_shared_prompts/process_log.md)。
- small-100 preliminary 已完成三个模型的 Base+四折，共 7,500 次生成且 common-seed mismatch=0。三模型等权 Base/BOUND Sample-HR 为 0.0467/0.0590，差值 `+0.0123`（95% 共享-prompt bootstrap CI `[-0.0045,+0.0270]`）；DeepSeekCoder 与 Llama 点估计恶化，仅 Qwen3 改善。联合结果不能支持未筛选集合上的总体改善，且 Empty rate 从 0.1067 升至 0.1835。该结果尚缺 source-group/near-duplicate audit 与共同 deployment snapshot，不能作为最终确认性结论，也不得通过更换 seed/fold 追求有利结果。
- confirmatory-200 已纠正preliminary的过度排除：三模型等权Base/BOUND Sample-HR为0.1050/0.1025，差值`-0.0025`（95% CI `[-0.0202,+0.0148]`）；Package-HR反而由0.0607升至0.0630，Empty由0.1133升至0.1828。Qwen3改善、Llama-3.1恶化、DeepSeekCoder接近不变，不能支持未筛选共同集上的稳定总体收益。

### E4：RQ2 代码质量与 Import→Distribution 映射

- 目标：使用完整分母审计 no-code、trivial、截断、AST/compile 失败、无 imports 和映射未知。
- 明确 `packages_distributions()` 不是全 PyPI 映射；同时报告 unique-macro 和频次加权 mapper accuracy。
- E0 的 RQ2 版本差异必须先解决。
- 状态：`[~]` [E7 RQ2 mapper 审计](experiment/E7_RQ2_pacakge_mapper/design_and_results.md) 已启动并完成全量代码/AST 导入清点，独立的代码语法审计已在 [E4new](experiment/E4new_Syntactic_Validity/design_and_results.md) 完成。

### E5：Localization 独立贡献与 Boundary 证据

- 目标：优先回答同实际参数预算随机位置对照、w/o Valid Anchor，以及固定 held-out candidates 上的 score separation。
- 先复用已有 random/hard-random/RQ3/RQ4 结果，再决定最小新增训练。
- 状态：`[~]` 已有资产待预算重核。
- 详细文档：[E5 设计与结果](experiment/E5_localization_evidence/design_and_results.md)；[E5 过程记录](experiment/E5_localization_evidence/process_log.md)。

### E6：Multi-token 与 Token Collision

- 目标：检查首 token 代理的实际打分位置、上下文 tokenization、共享前缀和零梯度 collision。
- 与 E5 统一规划，先离线全量审计，再决定是否运行 full-sequence/prefix 变体。
- 状态：`[x]` 已完成 12 组 first-token / full-sequence 对照；后续变体仍可另行规划。
- 详细文档：[E6 设计与结果](experiment/E6_tokenization_collision/design_and_results.md)；[E6 过程记录](experiment/E6_tokenization_collision/process_log.md)。

### E7：PyPI 有效性与 Cutoff 边界

- 目标：将注册表状态、时间状态、名称/映射关系、查询证据拆成独立维度，并同时报告论文 cutoff 与固定评估日期口径。
- 状态：`[ ]` 正式多维审计尚未进行，原占位目录已清理；已有的 cutoff 结果分别保留在已开展实验中。

### E8：真实项目分阶段验证

- P1：少量可复现任务、依赖证据和隔离环境可行性验证。
- P2：流程稳定后扩展至更多项目和执行维度。
- “命中一个必要依赖”称为 Required-Dependency Hit；只有通过功能验收/测试才称为 Task Success。
- 状态：`[ ]` 未开始。
- 原占位目录已清理；若启动，再建立实验目录。

### E9：HumanEval 统计复核

- 目标：冻结 harness、解释论文 run 选择、汇总全部 repeats，并用预注册 equivalence margin 描述能力变化。
- 状态：`[ ]` 尚未开展独立复核；E0 已追溯部分原结果，但不计作 E9 完成。原占位目录已清理。

### E10：更强/更大模型扩展

- 目标：在 E3 共同提示集上先评估 Base prevalence，再预注册一个候选模型和 fold 做范围扩展。
- 状态：`[ ]` 扩展实验未开展；另处已有的 preliminary Base 输出不计为本实验。原占位目录已清理。

## 5. 推荐执行顺序

### 第一阶段：离线与低成本

1. 解决 E0 的 RQ2/cutoff 阻塞；
2. E2 PackMonitor 兼容性 smoke test；
3. E4 RQ2 完整分母和 mapper 审计；
4. E6 tokenization/collision 全量统计；
5. E7 registry 多维标签与 cache；
6. E1 ground-truth provenance manifest 与小规模试标；
7. E5 现有结果的参数预算重分析；
8. E8 小规模项目环境可行性检查。

### 第二阶段：正式标注与无需重训的比较

1. E1 正式盲标；
2. E2 post-hoc verifier；
3. E5 固定候选 score separation；
4. E9 HumanEval 全 repeats 复核。

### 第三阶段：GPU 实验

1. E2 PackMonitor/repair；
2. E3 unfiltered shared primary generation；
3. 仅在必要时执行 E5/E6 的最小新增训练；
4. E8 小规模 Base/BOUND 执行；
5. E10 模型扩展。

## 6. Rebuttal 最小充分实验包

1. E1：Recommendation Adequacy + 任务相关性双层盲标及 empty/concentration；
2. E2：Base/BOUND × verifier，并完成 PackMonitor 兼容性和共同任务对照；
3. E3：严格排除编辑数据后的简单随机 unfiltered shared set、Sample-HR 绝对差和 historical-clean 回归；cross-risk matrix 作为次要任务；
4. E4：Base/BOUND 代码完整分母、AST/compile 与 mapper sensitivity；
5. E6：首 token 位置、multi-token、collision 和零梯度全量审计；
6. E5：已有随机定位的实际参数预算重分析、w/o Valid Anchor 或明确缺口；
7. E7：cutoff/评估日期双口径和多维标签；
8. E8：至少完成真实任务环境可行性和少量严格案例。

## 7. 结论与负结果规则

- Package-HR 下降且 Adequacy 配对差异区间下界高于冻结的 `-δ`：可在该 margin 和样本范围内声称“降低包幻觉，同时保持推荐适用性”。
- Adequacy/Recall 有支持的改善：才声称“提高推荐有用性”。
- verifier/PackMonitor 更优：如实报告，BOUND 只保留有数据支持的独立或组合价值，不能自动诉诸“离线场景”。
- E3 收益小：将原结果限定为 high-risk stress test，不外推真实部署总体收益。
- mapper/完整分母改变 RQ2 结论：修订或撤回相应跨任务声明。
- budget-matched random 与 BOUND 无差异：弱化 localization 独立贡献和 stable boundary 表述。
- collision 明显：承认 first-token proxy 限制，并将 full-sequence 作为修订方向。
- 真实项目环境不可稳定复现：报告可行性阻塞，不用基础设施失败评价模型。

## 8. 进度总表

| ID | 实验 | 优先级 | 状态 | 结果目录 | 当前结论 |
| --- | --- | --- | --- | --- | --- |
| E0 | 版本冻结 | P0 | `[x]` | `experiment/E0_version_audit/results/` | 审计完成，RQ2/cutoff 待处理 |
| E1 | 适用性与充分性 | P0 | `[x]` | `experiment/E1_task_relevance/results/` | 60任务/300回答最终匿名双标完成；Adequacy 0.367→0.254，非劣性不成立且存在漏推荐代价 |
| E2 | Verifier/PackMonitor | P0 | `[x]` | `experiment/E2_verifier_packmonitor/results/` | 三模型四折repair100及DeepSeekCoder原生PackMonitor100完成；约束继续降低invalid，但utility与截断边界仍需单列 |
| E3 | 未筛选共同提示集 | P0 | `[x]` | `experiment/E3_unfiltered_shared_prompts/results/` | confirmatory-200共15,000次生成完成；Sample-HR差-0.0025且CI跨0，Package-HR/Empty恶化，不支持稳定总体改善 |
| E4 | RQ2 import 映射审计 | P0 | `[ ]` | — | 尚未开展；E4new 语法审计已完成但不替代映射审计 |
| E5 | Localization/boundary | P1 | `[~]` | `experiment/E5_localization_evidence/results/` | 已有资产待重分析 |
| E6 | Tokenization/collision | P0/P1 | `[x]` | `experiment/E6_tokenization_collision/results/` | 12 组审计已完成 |
| E7 | 有效性/cutoff | P1 | `[ ]` | — | 多维审计未开展 |
| E8 | 真实项目验证 | P1 小规模/P2 扩展 | `[ ]` | — | 未开展 |
| E9 | HumanEval 复核 | P1 | `[ ]` | — | 独立复核未开展 |
| E10 | 模型规模扩展 | P2 | `[ ]` | — | 扩展实验未开展 |

## 9. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-09-25 | 清理未开展的 E4/E7/E8/E9/E10 占位目录；保留已运行的 E4new 语法审计及其他有结果目录，更新索引状态。 |
| 2026-09-23 | 创建 E0–E10 rebuttal 实验计划。 |
| 2026-09-23 | 完成 E0；发现 RQ2、成本表示和 cutoff 版本差异。 |
| 2026-09-23 | 根据新审阅意见修订 E1–E8：新增 Adequacy/Recall、PackMonitor、严格 shared unseen、完整分母、预算匹配、token collision、多维 registry 状态和分阶段真实项目验证。 |
| 2026-09-23 | 改为 `experiment/E*_english_name/` 组织；每项实验包含 `results/`、`script/`、中文设计结果文档和中文时间顺序过程文档；总计划压缩为索引和状态。 |
| 2026-09-23 | E1 增加数据源 ground-truth 溯源门；确认公开 `LLM_LY` 无逐 prompt 包名映射，当前 `valid_reference` 不可作为 ground truth。 |
| 2026-09-23 | E1 收紧 requirement slots、Adequacy、完整配对抽样、非劣性、未知标签、标注独立性和已有探索结果披露规则。 |
| 2026-09-23 | E3 将 Primary 固定为 leakage exclusion 后的简单随机 unfiltered sample，以 Sample-HR 绝对差为主终点；历史 risk、双 registry 口径、common seeds、nested 人工子集和 cross-risk P1 均明确分层。 |
| 2026-09-23 | E1匿名双标、E2三模型四折repair及DeepSeekCoder原生PackMonitor100、E3纠正后confirmatory-200均完成；结果显示存在性风险下降并不自动保持Adequacy，未筛选共同集上总体收益很小且不确定。 |
