# E1——实验过程记录

本文件按时间顺序追加，记录设计冻结、样本生成、标注批次、异常、决策和结果版本。

## 2026-09-23

- 发现只使用 Task-Relevant Precision 和“至少一个相关包”的 Useful-Answer Rate 无法识别严重漏推荐。
- 将 Useful-Answer Rate 更名并限缩解释为 Relevant-Package Hit Rate。
- 新增 Recommendation Adequacy Rate、requirement-slot coverage 和可靠 reference 子集上的 Reference Dependency Recall。
- 将标注拆成包级任务作用和回答级整体充分性两层。
- 明确 `cannot-judge` 不得静默移出分母，必须做保守/宽松敏感性分析。
- 重新估算完整工作量为 7,500 条回答、双人 15,000 次回答审查，决定先做小规模试标再冻结正式样本。
- 明确该实验不是用户研究。
- 按“先查数据集 ground truth、再设计人工标注”的顺序审计 Spracklen 官方 GitHub、Zenodo artifact 文件索引和本地数据派生代码。
- 确认公开 `Data/Python/LLM_LY.json` 仅含 prompt 字符串，没有逐 prompt 包名、参考依赖或 ground-truth 字段；公开 PyPI 包名全集仅服务于存在性检查。
- 确认 Zenodo 压缩包未发布 prompt→源包映射或代码中提到的上游 `package_prompts_master`；该压缩包约 9.9 GB，本次通过 HTTP range 读取 ZIP 中央目录完成文件清单审计，未下载整个压缩包。
- 确认本地 `valid_reference` 来自模型输出中的 registry-valid 包并集，而非数据集标签，因此禁止将其用于 Reference Dependency Recall。
- 新增 `ground_truth_status` provenance 分级；把作者提供映射或可验证重建设为使用 source label 的前提，将 prompt 明文包名降格为 anchor。
- 根据第二轮设计意见进一步收紧 E1，保持实验规模受控，重点修改操作定义和分析规则。
- 将 E1 定位为“任务相关性、依赖覆盖和明显退化”的专家审计；明确它不单独验证安装、API/版本兼容、端到端执行或真实用户体验。
- 要求在展示任何 Base/BOUND 正式回答前，由两位标注者独立提取并冻结 prompt 级 requirement slots；禁止使用 `G_i`、`y_i`、Base/BOUND 推荐或 `valid_reference` 反推需求。
- 将 slot 限定为与依赖选择有关的主要能力或约束，新增标准库/普通逻辑可满足和无需第三方依赖标记，避免奖励不必要的多包推荐。
- 删除“覆盖全部或大部分即可 adequate”的模糊规则：只有所有必要 dependency-relevant slots 都由实际存在且适用的包覆盖，才标为 `adequate`；漏掉任一必要 slot 则至多为 `partially_adequate_with_clear_omission`。
- 将语义充分性与存在性风险解耦：额外幻觉包不自动使 Adequacy 归零，但幻觉包不能满足 slot；联合安全指标只作辅助结果。
- 将包级标签进一步拆成独立的 `registry_status`、`cutoff_status` 与 `task_role`，避免用一个 `nonexistent` 互斥标签再次混淆存在性和语义作用。
- 固定人工审计的实际存在性日期为 2026-09-23 UTC，并与原论文 model cutoff 标签分开；post-cutoff 真实包可参与语义覆盖。
- 将试标难例、校准案例与正式随机样本分开；正式阶段先随机抽 prompt，再纳入 Base 和四个 BOUND folds 的完整配对条件，不为覆盖异常而过采样。
- 暂定时间受限起始方案为每模型 30 prompts、每条件 1 条 generation，共 450 条回答、900 次独立回答级判断；是否扩样必须在方法差异揭盲前冻结。
- 指标层次收敛为一个主要指标 Recommendation Adequacy、三个关键次要指标和三类退化检查；strict-core、Jaccard、distinct packages 与原包保留率降为探索性解释。
- 明确 inclusive precision 的分母包含不存在包和无关包；按规范化 distribution name 在回答内去重，空推荐不记为 precision=1。
- 将目标明确为 non-inferiority；只有 Base→BOUND Adequacy 差异区间下界高于预先给出理由的 `-δ` 才支持非劣性，不把不显著解释为保持。
- 明确先在 prompt 内平均 generations、再对四折 BOUND 求平均；bootstrap 以 prompt 为 cluster，不复制 Base 形成伪独立样本。
- 修正 `cannot_judge` 差异边界：最不利情形为 BOUND 未知判失败、Base 未知判成功；最有利情形反向赋值。
- 要求共享文档事实但保持两名标注者判断独立，保存两份原始标签；复制缓存标签不重复进入一致率计算。
- 披露已查看的 fold A 自动退化信号；内部文件只称“冻结的预分析计划”，除非提交带时间戳的外部注册平台。
- 启动 E1 小规模双代理独立标注。主线程新增 `script/prepare_pilot_manifest.py`，以固定 seed `20260923` 从 DeepSeekCoder fold-A 现有评估中抽取 5 prompts，每个 prompt 取匿名 Base/BOUND 各一条，共 10 条回答；共享文件仅含 blind ID、prompt、answer 和 packages，盲键暂存 `/tmp/e1_pilot_blind_key.json`。
- 标注者1主动披露：其在查询本地 registry 证据时执行全库搜索，意外看到共享样本中部分包的旧自动 valid/hallucinated 字段。虽然没有看到 Base/BOUND 条件映射，但该批次不再用于严格独立一致率或确认性结果，只保留为污染披露和标注指南校准。主线程将另建与首批不重叠的共同盲样本供两名标注者重新独立标注。
- 已生成严格独立的 round-2 共享盲样本：seed `20260924`，排除首批 prompt IDs `61/2841/3047/3131/3551` 后另抽 5 prompts、10 条匿名回答；文件为 `results/pilot_round2_prompt_manifest.jsonl` 和 `results/pilot_round2_manifest.jsonl`，新盲键暂存 `/tmp/e1_pilot_round2_blind_key.json`。两名标注者均被要求只读 round-2 manifests 和外部官方证据，禁止搜索本地旧评估文件；首批及标注者2自行构造的批次全部降格为 calibration。
- 两名标注者完成 round-2 独立标签后才揭盲。回答级 Adequacy 精确一致率 90.0%、Cohen's κ=0.839；registry status 一致率 86.5%、κ=0.730；task role 一致率 62.2%、κ=0.468。原始比较与全部分歧保存在 `results/round2_interannotator_agreement.json`。
- 完成唯一一条回答级分歧仲裁：prompt 3119 的回答使用 `graphql-server` 覆盖 query/mutation execution 能力，但遗漏 graphql-tag schema generation 且未满足全部显式库约束，最终标为 `partially_adequate_with_clear_omission`。仲裁记录保存在 `results/adjudicated_labels_round2.jsonl`。
- 仲裁后揭盲：Base 为 3/5 adequate，fold-A BOUND 为 1/5 adequate、2/5 partially adequate、2/5 inadequate。该结果只作小样本校准与风险预警，不作正式效果估计。
- 根据低 task-role 一致率新增 `results/annotation_guideline.md`：加入 `candidate_type/name_relation`、标准库/外部工具状态、`claimed_role` 与真实文档能力分离，以及原子 slot 规则。

## 下一步

- 联系数据集作者申请 `package_prompts_master` 或逐 prompt 源包映射，并记录版本、字段语义和对齐依据。
- 编写 provenance manifest；在作者映射不可得时，将公开数据全部标为 `prompt_explicit_anchor` 或 `unavailable`，不把当前 `valid_reference` 混入 ground truth。
- 编写第一版标注指南、slot 模板和五类校准案例。
- 生成与正式样本隔离的试标 manifest，完成耗时和分歧测量。
- 在展示正式回答前冻结正式 prompts、requirement slots、generation 索引和盲化表。
- 记录两位标注者的耗时与仲裁前分歧。
- 在查看正式方法差异前为 non-inferiority margin 提供任务层面理由，并冻结样本量、扩样停止条件和统计脚本。

## 2026-09-23：独立标注者 2 小规模试标

- 标注者 2 在未查看任何 Base/BOUND 待评回答和标注者 1 判断的情况下，先选取 3 个多能力任务（prompt ID 270、4126、2845），独立冻结了 requirement slots；结果保存为 `results/annotator_2_pilot_frozen_slots.jsonl`。
- slots 仅包含依赖选择相关能力，并明确记录标准库/普通逻辑是否允许以及题目是否指定库；其中 SIP 任务不允许仅以音频或图像处理库替代 SIP 信令能力，`pylabelstudio` 任务保留显式生态约束。
- 随后从 DeepSeekCoder 已有 RQ2 输出中机械抽取每个 prompt 的 Base 与四个 BOUND folds 各 1 条 generation，共 15 条回答；随机化回答顺序并用不含模型、方法和 fold 的 `blind_answer_id` 替换来源标识。
- 盲化回答保存为 `results/annotator_2_pilot_blinded_answers.jsonl`；映射密钥单独保存为 `results/annotator_2_pilot_blinding_key_DO_NOT_OPEN_DURING_LABELING.jsonl`。标注者 2 在独立标注结束前不读取映射密钥。
- 当前阶段属于定向小规模试标，不进入正式确认性均值；其目标是检验操作规则和记录耗时/歧义。
- 主线程随后冻结了供两位标注者共同使用的盲化样本：`results/pilot_prompt_manifest.jsonl`（5 个 prompts）与 `results/pilot_manifest.jsonl`（10 条回答）。标注者 2 即刻切换到该共享批次，以便计算真正的独立标注一致性。
- 先前由标注者 2 自选的 3-prompt/15-answer 批次降格为标注规则校准材料，禁止混入共享 pilot 的一致率或方法比较；标注者 2 不再继续对该批次正式打标。
- 标注者 2 不读取 `/tmp/e1_pilot_blind_key.json`，也不再查看源评估输出；共享批次继续严格执行“只看 prompt 冻结 slots，再查看盲化回答”的顺序。
- 标注者 2 只读取共享 `pilot_prompt_manifest.jsonl`，在未打开 `pilot_manifest.jsonl` 的情况下完成 5 个 prompt 的独立需求分解，保存至 `results/annotator_2_shared_pilot_frozen_slots.jsonl`。
- 本次 slots 保留 ConfigCat、DNSpython、cdxj、NCCL 与 spark-html 的显式生态约束；同时把“库支持的核心依赖能力”和可由普通逻辑完成的结果组织区分开，避免把所有编程步骤机械设成独立第三方依赖。
- 在标注者 2 完成首批 10 条回答的标签后，主线程为排除任何可能的样本污染，重新生成了与旧批次完全不重叠的严格独立 round 2：`results/pilot_round2_prompt_manifest.jsonl` 与 `results/pilot_round2_manifest.jsonl`。
- 标注者 2 的全部旧批次及 `annotator_2_raw_labels.jsonl` 均降格为校准材料，不进入独立一致率或方法比较。确认性 pilot 只使用 round 2，并输出到 `results/annotator_2_raw_labels_round2.jsonl`。
- round 2 再次从 prompt-only manifest 开始，禁止读取旧 eval、任何 blind key、旧方法映射和标注者 1 判断；过程继续按“冻结 slots→包级证据→回答级 Adequacy”执行。
- 标注者 2 仅查看 round 2 的 prompt-only manifest，独立冻结 5 个任务的 slots，保存为 `results/annotator_2_frozen_slots_round2.jsonl`；冻结完成前未打开 round 2 回答 manifest。
- 对 `json`、`typing` 和控制台打印等标准库/普通逻辑要求，保留为非第三方任务约束但不机械设为 dependency slot；对 GraphQL 库、Minidump、projen preset 等题目明示生态则保留严格约束。
- 标注者 2 在 slots 冻结后打开 round 2 盲化回答，对 10 条回答、37 个包候选逐项查询 PyPI、Python 官方文档及项目官方文档，并完成 `registry_status`、`task_role`、slot coverage 和回答级 Adequacy 独立标注；原始结果保存为 `results/annotator_2_raw_labels_round2.jsonl`。
- JSONL 完整性检查通过：5 个 prompts 各 2 条回答，共 10 条；标注者 2 独立结果为 `adequate=4`、`partially_adequate_with_clear_omission=2`、`inadequate=4`，未出现回答级 `cannot_judge`。
- 37 个候选中记录 `exists_at_audit_date=23`、`nonexistent_at_audit_date=9`，另有 5 个 Python 标准库模块。试标暴露出当前三值 registry schema 缺少“标准库/非 registry 对象”状态，因此 round 2 原始标签显式使用 `not_applicable_stdlib`，避免把 `json`、`typing`、`traceback` 错记为不存在或未知；正式指南冻结前需决定是否将其并入名称/映射维度。
- 标注严格保留原始名称：例如 `git` 不因代码使用 `git.Repo` 而静默改成 `GitPython`，`pyminidump` 不改成 `minidump`，`opencv` 不改成 `opencv-python`。这些别名/近名关系只写入 `name_relation`，原推荐是否可安装仍按原名判定。
- Adequacy 与存在性保持分离：两个 3D pose 回答均可由 TensorFlow/Keras 覆盖全部 slots，其中一个额外包含错误名 `opencv`，仍标为语义充分但保留存在性错误；同理，额外错误包不自动把完整覆盖置零。

## 2026-09-23：标注者 2 正式盲标

- 标注者 2 已读取正式指南、预分析冻结说明和 `formal_prompt_manifest.jsonl`，确认正式规模为 60 tasks/300 answers，并确认禁止读取 `/tmp/e1_formal_blind_key.json`、eval source、方法映射、标注者 1 文件及正式揭盲结果。
- 完成第 1 个可恢复 slots 批次（任务 1–20），写入 `results/annotator_2_formal_slots.jsonl`。当前仍未打开 `blinded_answers.jsonl`。
- 本批严格拆分原子能力，例如 ECS/CDK、CloudWatch、IAM 分开，OpenJPEG 读/写/元数据/格式转换分开；环境变量赋值等普通逻辑保留为非依赖任务要求，不机械增加第三方 slot。
- 完成第 2 个可恢复 slots 批次（任务 21–40），累计冻结 40/60 个 tasks；仍未打开匿名回答。
- 对多组件云原生任务分别冻结 gRPC、Docker、Kubernetes、OpenTelemetry、Prometheus、Jaeger 六个原子槽；对 YAML 冲突 union、线程负载等可由普通逻辑完成的步骤不设额外第三方依赖槽。
- 完成第 3 个 slots 批次（任务 41–60）；在打开回答前对 `annotator_2_formal_slots.jsonl` 做结构 QA：60 行、60 个唯一 `task_id`、0 个重复，共冻结 152 个 dependency-relevant 原子 slots，另有 1 个明确无需第三方依赖的 SARIF 任务。
- 至此正式 60 个 prompts 的 slots 已全部独立落盘并冻结。后续才允许打开 `blinded_answers.jsonl`；slots 不因回答内容修改。
- slots 冻结后，标注者 2 首次打开 `blinded_answers.jsonl`；文件 QA 为 300 行、300 个唯一匿名回答 ID、60 个 tasks，每 task 5 条回答，共出现 413 个唯一原始候选名。
- 仅从匿名回答提取候选名，通过 PyPI 官方 JSON API 建立 `results/annotator_2_registry_cache.jsonl`。第一次沙箱内请求被操作系统网络策略拒绝，未据此把候选误判为不存在；随后在获准网络环境下重新查询并修正变量转义错误后成功完成。
- Registry 缓存最终包含 413 个名称：截至审计日期 PyPI 存在 272 个、HTTP 404 不存在 131 个、Python 标准库模块 10 个。缓存保留 canonical name、PyPI summary、证据 URL 与 HTTP 状态；原始错误名不被静默替换。

## 2026-09-23：独立标注者 1 启动记录

- 已完整阅读当前 E1 设计，确认本轮仅开展不占用 GPU 的小规模试标，不把试标结果混入正式确认性结果。
- 为保持盲法，拒绝直接从含有 `baseline`、`edited`、`valid` 和 `hallucinated` 字段的现有评估 JSON 人工挑选回答；已请求主线程生成两位标注者共用的匿名 pilot manifest。
- 要求共享 manifest 仅暴露匿名回答 ID、prompt、原始回答及原始包名，不暴露模型、方法、fold 或自动存在性标签；方法映射在独立标注完成前不得揭盲。
- 后续严格按“先独立冻结 requirement slots，再做包级 registry/task-role 判断，最后做回答级 Adequacy”的顺序记录到 `annotator_1_raw_labels.jsonl`。
- 收到 5 个 prompt、10 条匿名回答的共享 pilot manifest 后，标注者 1 在检索包名的本地 registry 证据时误用全库 `rg`，输出意外命中了旧评估文件并暴露 `cdxj`、`spark-html` 等候选的自动 `valid/hallucinated` 标签。标注者没有读取盲化 key，也仍不知道每对回答的 Base/BOUND 身份，但严格的 registry 标签盲法已经被污染。
- 已立即向主线程披露该事件。本批只能降格为指南调试/校准材料，不得用于两名标注者的独立一致率或正式结果；若需要有效独立试标，应为标注者 1 更换不重叠的新 prompt，并限制证据检索到官方外部页面。
- 主线程随后提供了与污染批次完全不重叠的 round 2：5 个 prompt、10 条匿名回答。标注者 1 先只读取 prompt manifest，在未打开 round 2 回答文件前独立冻结 5 个 prompt 的 requirement slots，结果保存于 `results/annotator_1_requirement_slots_round2.jsonl`。
- round 2 的 slot 提取没有使用模型回答、自动存在性标签、`valid_reference` 或盲化映射；对于 prompt 明确指定的库保留其生态/库约束，对于 `json`、`typing` 等标准库步骤以及普通实现逻辑不额外设置第三方依赖槽。
- 标注者 1 在 slots 冻结后才打开 round 2 匿名回答，未读取 `/tmp` 中的 blind key、方法、模型、fold 或旧评估文件。包存在性只通过 PyPI 官方 JSON API 当前状态和外部官方项目页面核验。
- 已完成 round 2 的 10 条独立原始标签，保存至 `results/annotator_1_raw_labels_round2.jsonl`；结构校验结果为 10 条记录、10 个唯一匿名回答 ID，标签取值覆盖 `adequate`、`partially_adequate_with_clear_omission` 与 `inadequate`。
- 标注者 1 本轮结果：3 条 `adequate`、1 条 `partially_adequate_with_clear_omission`、6 条 `inadequate`。这些仍是未揭盲的试标判断，不能按 Base/BOUND 解释，需等待标注者 2 独立完成及后续仲裁。
- 试标暴露两个需在正式指南前修正的问题：（1）`json`、`traceback`、`typing` 等标准库/import 名与 PyPI distribution 不能只靠三值 `registry_status` 表达，应新增独立 `candidate_type/name_relation`，且不能把标准库模块机械算作 hallucinated distribution；（2）prompt 206 的单一 slot 同时包含版本递增和分支/标签，过于复合，导致部分覆盖无法用二元 slot coverage 清楚表达，正式 slots 应在展示回答前拆成原子能力。
- 对额外不存在候选遵循“存在性与充分性分离”：若其他真实且适用包已经覆盖全部 slots，Adequacy 不归零；不存在或 registry 未确认的候选本身不能用于满足 slot。

## 2026-09-23：独立标注者 1 正式批次

- 严格按正式冻结要求启动：只读取 `formal_prompt_manifest.jsonl`、`annotation_guideline.md` 和 `prior_exposure_and_analysis_freeze.md`，尚未打开匿名回答文件，也未读取 blind key、旧 eval、方法映射或标注者 2 文件。
- 已为 60 个正式 tasks 独立冻结 105 个原子 dependency-relevant slots，保存至 `results/annotator_1_formal_slots.jsonl`；QA 为 60 行、60 个唯一 `task_id`。
- slot 提取把标准库和普通实现逻辑留作非依赖约束；对 prompt 明确指定的库/生态保留显式约束，但没有把来源描述中的包名自动当作可用 ground truth。
- 在 60 个 tasks 的 slots 全部落盘后，标注者 1 才打开 300 条匿名回答；全程未读取正式 blind key、eval source、方法映射、标注者 2 文件或揭盲结果。
- 对匿名回答中的 413 个 unique candidate names 通过 PyPI 官方 JSON API 做 2026-09-23 存在性核验，并把查询结果缓存到 `results/annotator_1_registry_cache.json`。300 条回答共形成 960 个包级原始标签；按 mention 计为当前存在 761、不存在 173、标准库 24、外部工具 2。
- 对容易产生“真实但无关”误判的名称额外核查官方项目页。例如 `tor` 的官方 PyPI 页面明确说明其为 TOR proxy client，可覆盖 Tor 路由能力；`pytoolkit` 虽真实存在，但官方描述只有通用工具集合且没有 `Maybe` 证据，因此没有把它用于覆盖提示中的 `pytoolkit.Maybe` slot；`datahub` 被识别为指向 `acryl-datahub` 的官方占位包，而不是仅凭名称判定。
- 已将独立正式标签写入 `results/annotator_1_formal_labels.jsonl`。未揭盲 Adequacy 计数为：`adequate=78`、`partially_adequate_with_clear_omission=72`、`inadequate=150`。这些计数只用于标注完整性检查，不得在揭盲前解释为 Base/BOUND 差异。
- 正式 QA 通过：slots 60 行/60 个唯一 task；labels 300 行/300 个唯一匿名回答 ID；匿名回答顺序与包名逐项对齐；所有 `covered_slots` 均引用对应 task 的冻结 slot。没有删除难例、未知项或不利标签。

## 2026-09-23：正式样本启动

- 完成目标审计后确认 round-2 仅是校准，不能把 E1 判定为完成；按时间受限方案冻结每模型20 prompts、Base+四折各1条 generation-0，共60 tasks/300匿名回答。
- 新增 `script/prepare_formal_manifest.py`，从每个模型四折共同 unseen ID 交集中稳定抽样，排除两轮试标的10个 prompt ID；seed=`20260925`。
- 已生成 `results/formal_prompt_manifest.jsonl`（60行）和 `results/blinded_answers.jsonl`（300行）。模型/方法/fold映射只写入 `/tmp/e1_formal_blind_key.json`，独立标注完成前禁止读取。
- 写入 `results/prior_exposure_and_analysis_freeze.md`，披露已查看的探索结果，并冻结主要指标、task-cluster bootstrap、未知标签处理与5个百分点非劣性 margin；不得按正式标签效果扩样或换折。
- 两名标注者各自完成60 tasks/300 answers后，发现原流程遗漏了“独立提槽后、看回答前形成共同槽表”这一中间仲裁：标注者1为105槽，标注者2为152槽。主线程在不读取正式回答和盲键的情况下仅基于prompt与两份槽表审计，确认标注者2多次把普通实现步骤或单一依赖的内部操作拆成额外依赖槽。
- 共同 `results/frozen_requirement_slots.jsonl` 因而采用更符合指南的105槽版本，并写入 `results/slot_adjudication_note.md`。标注者2将在仍未揭盲时基于共同槽重新映射；原始各自槽标签不删除，只作为流程偏差与敏感性材料。
- 完成性复核进一步发现原 `task_id` 直接包含 `deepseekcoder/qwen3-release/llama3.1-release`，虽然回答方法和fold仍被隐藏，但没有满足“隐藏模型”的正式要求。该批双标与仲裁保留为模型可见敏感性，不作为最终主分析。
- 新增 `script/anonymize_formal_tasks.py`，将60个任务重键为不可逆哈希式 `TASK-*`，生成 `formal_prompt_manifest_anonymous.jsonl`、`blinded_answers_anonymous.jsonl` 和 `frozen_requirement_slots_anonymous.jsonl`；模型映射只在 `/tmp/e1_anonymous_task_key.json`。文本扫描确认清单字段不含模型、方法、fold或condition标签。将使用未接触旧标签的新标注者重新完成共同槽下的正式双标。
- 两名全新标注者在匿名任务ID与共同105槽下完成300回答/960候选独立标注；仲裁前Adequacy一致率89.33%（κ=0.834），registry 98.44%（κ=0.955），task role 71.77%（κ=0.569）。第三方在不读任何key或模型/方法映射的情况下完成盲态仲裁，最终83 adequate、71 partial、146 inadequate，QA全部通过。
- 独立标签与仲裁全部落盘后才将 `/tmp` 两个key复制为 `formal_unblinded_key.json` 与 `formal_task_unblinded_key.json`。新增 `script/analyze_final_e1.py`，按prompt成组做2,000次bootstrap并使用冻结的5个百分点非劣性margin。
- 揭盲结果：三模型等权Base/BOUND Adequacy为0.367/0.254，差值-0.113，95% CI [-0.208,-0.025]；slot coverage 0.510→0.377，empty 0.017→0.125。Inclusive precision反而0.606→0.688，说明precision升高由删除/收缩推荐驱动，不能解释为整体utility保持。所有非劣性区间下界均低于-0.05，正式结论是不支持保持适用性，并量化存在漏推荐代价。
- 新增 `script/finalize_e1_artifacts.py`，补齐设计约定的标准交付文件：60行匿名正式manifest、两份300行原始独立标签、300行最终仲裁、413名称共享事实证据、逐任务ground-truth provenance、来源关联恢复报告和校准/一致性表。旧模型可见或pilot文件在覆盖前复制为明确的calibration/sensitivity文件，未删除。

## 2026-09-23：独立标注者 2 正式回答标注与质检

- 在 60 个任务的 requirement slots 全部冻结之后，标注者 2 根据题目约束及 PyPI 官方元数据，独立冻结任务—候选覆盖规则，保存为 `results/annotator_2_formal_coverage_rules.jsonl`。该规则不包含 Base/BOUND、fold 或模型条件信息；用途是让同一任务中重复出现的候选复用事实证据，但每条回答的整体充分性仍独立计算。
- 标注者 2 对 300 条匿名回答完成逐条标注，原始结果保存为 `results/annotator_2_formal_labels.jsonl`。共标注 960 个 package mentions、413 个唯一原始候选名；原始名称没有被别名或猜测的正确分发名覆盖。
- 回答级 Adequacy 的未揭盲完整性计数为：`adequate=95`、`partially_adequate_with_clear_omission=95`、`inadequate=110`、`cannot_judge=0`。这些计数仅用于确认标签覆盖和发现异常，尚未读取方法映射，不能解释为任何方法差异。
- 960 个包级标签按审计日 registry 状态计为：PyPI 当前存在 759、PyPI 当前不存在 173、Python 标准库 24、外部工具/产品 4；按任务角色计为：核心功能支持 367、可选辅助 340、明显无关 80、无法据现有证据判定用途 173。所有 package mention 均保留至少一条证据记录。
- 最终结构 QA 通过：slots 文件 60 行/60 个唯一 `task_id`；labels 文件 300 行/300 个唯一匿名回答 ID；每个任务恰有 5 条回答；回答 ID 集与 `blinded_answers.jsonl` 完全一致；960 个包名与匿名输入逐项、逐序对齐。
- 语义一致性 QA 通过：每个包和回答的 `covered_slots` 均是对应任务冻结槽的子集；回答覆盖集合等于其包级覆盖并集；`uncovered_slots`、slot coverage 与 Adequacy 标签按冻结规则一致。标签顶层未写入 `model`、`method`、`fold`、`condition` 或来源条件字段。
- 本轮独立标注始终未读取 `/tmp/e1_formal_blind_key.json`、旧 eval source、方法映射、标注者 1 文件或正式揭盲结果。标注者 2 的 152 个 slots 与另一标注者的分解不应在仲裁前被强行统一；两者差异本身应进入仲裁前一致性与指南敏感性分析。

## 2026-09-23：独立标注者 2 按共同 slots 恢复正式标签

- 主线程在仅依据 prompts 与两份独立 slot 文件完成 prompt-only 仲裁后，冻结了 `results/frozen_requirement_slots.jsonl`（60 tasks、105 个共同 slots）。标注者 2 阅读 `results/slot_adjudication_note.md` 后接受共同槽定义，但没有读取盲键、方法映射或标注者 1 的回答标签。
- 原始 `annotator_2_formal_slots.jsonl` 和 `annotator_2_formal_labels.jsonl` 均保持不变，作为流程偏差和敏感性分析记录；正式可比版本另存为 `results/annotator_2_formal_labels_common_slots.jsonl`。
- 新增可复现脚本 `script/remap_annotator2_common_slots.py`。映射不是简单替换槽 ID：对于共同槽合并了多个依赖能力的情况，仅支持局部步骤的包降为可选辅助，不能单独满足完整槽；显式库/生态约束继续保留。
- 典型保守修正包括：单个 AWS CDK ECS/CloudWatch/IAM 子模块不能独自覆盖完整 service-extension construct；通用 OpenTelemetry 包不能替代指定的 scikit-learn instrumentation；KCachegrind/QCachegrind 查看器不能替代 cProfile→callgrind 转换器；MySQL connector 不自动视为题目明确指定的 MariaDB Connector/Python。
- 对共同槽带来的合理变化也显式处理：SARIF 是 JSON 格式，因此标准库 `json` 可直接覆盖解析与字段提取槽；同时仍保留其 `candidate_type=stdlib_module`，不把它伪装成 PyPI distribution。
- 重新完成 300 条匿名回答、960 个 package mentions 的包级 `covered_slots`、回答级 slot coverage 与 Adequacy。未揭盲计数为：`adequate=103`、`partially_adequate_with_clear_omission=71`、`inadequate=126`、`cannot_judge=0`。
- 最终恢复 QA 通过：300 行、300 个唯一匿名回答 ID、60 个 tasks、每 task 5 条回答；ID 集与匿名输入完全一致；960 个包名逐项逐序对齐；全部包级和回答级槽引用均属于对应任务的 105 槽共同表；回答覆盖集合等于包级覆盖并集，coverage 数值与 Adequacy 标签一致，所有 package mentions 均保留证据。
- 恢复阶段只共享需求槽定义，没有共享另一标注者的 registry、task-role、covered-slots 或 Adequacy 判断；因此该文件仍是标注者 2 基于自身事实判断得到的独立标签，可用于共同槽下的仲裁前一致性分析。

### 2026-09-23：正式双标一致性分析启动

- 两名标注者已完成独立盲标，现按计划进入非独立的仲裁前一致性分析阶段。
- 本阶段仅读取两份正式 slots 与两份正式 labels；不读取盲化映射、不揭示方法条件，也不修改任何原始标签。
- 已核对两套 JSONL 的字段结构。后续将以 `blind_answer_id` 对齐回答、以回答内规范化后的 `raw_name` 对齐候选，输出回答级和候选级分歧清单。

### 2026-09-23：正式双标仲裁前一致性分析完成

- 新增可复核脚本 `script/compare_formal_annotations.py`。脚本只读取两份正式 slots 与 labels，未读取 `/tmp/e1_formal_blind_key.json`，也未覆盖任何原始标签。
- 回答对齐 QA：两侧各 300 条回答，300 个 `blind_answer_id` 全部匹配；共同候选 960 个，所有回答的候选集合均一致。
- Adequacy 仲裁前 exact agreement 为 225/300（75.00%），未加权 Cohen's κ=0.6203；75 条回答存在 Adequacy 分歧。
- 候选级 `registry_status` exact agreement 为 958/960（99.79%），κ=0.9939；`task_role` exact agreement 为 596/960（62.08%），κ=0.4858。
- 候选级 covered/not-covered 以“是否覆盖至少一个各自冻结 slot”的布尔值比较：exact agreement 为 822/960（85.62%），κ=0.6800。由于两套 slot 的粒度不同，不把 slot ID 完全一致作为该指标。
- 回答级 `cannot_judge` 两侧均为 0/300；候选级 `task_role=cannot_judge` 分别为 76/960（7.92%）与 173/960（18.02%），未静默删除未知项。
- Requirement slots 逐任务比较完成：60 个共同任务中 19 个任务的 slot 数相同、41 个不同；两侧总 slots 分别为 105 与 152。词面最佳匹配相似度仅作为审计线索，不解释为语义一致性或仲裁结果。
- 已输出 `results/formal_interannotator_agreement.json`、`results/formal_interannotator_agreement.md`、`results/formal_disagreements.jsonl`（441 行：75 条回答分歧、366 条候选分歧）和 `results/formal_slot_differences.jsonl`（60 行）。
- 输出 QA 通过：comparison 脚本可编译；JSON/JSONL 均可完整解析；分歧清单与 slots 差异文件行数符合汇总统计。

### 2026-09-23：共同 slots 主一致性分析启动

- 标注者 2 已在不揭盲条件下基于共同冻结的 105 个 requirement slots 完成重新映射，文件为 `results/annotator_2_formal_labels_common_slots.jsonl`（300 行）。
- 现将 `annotator_1_formal_labels.jsonl` 与该 common-slot 标签作为正式仲裁前主一致性比较；此前基于两套独立 slots 的一致率继续保留为 slot 粒度敏感性结果。
- 本轮仍不读取盲化映射、不覆盖任何独立原始标签，先核对 300 条回答和共同 slots 文件结构，再生成单独命名的主结果文件。

### 2026-09-23：共同 slots 主一致性分析完成

- 新增 `script/compare_common_slot_annotations.py`，以共同冻结的 60 个任务/105 个 slots 为唯一 coverage 词表，对齐标注者 1 正式标签与标注者 2 common-slot 标签。300 条回答和 960 个候选全部对齐，候选集合不一致回答数为 0。
- 主 Adequacy 仲裁前 exact agreement 为 255/300（85.00%），Cohen's κ=0.7671；Adequacy 分歧由独立 slots 敏感性分析中的 75 条降为共同 slots 下的 45 条。
- 候选级 `registry_status` exact agreement 为 958/960（99.79%），κ=0.9939；`task_role` 为 623/960（64.90%），κ=0.5227。
- 候选 covered/not-covered exact agreement 为 853/960（88.85%），κ=0.7386；候选 covered-slot 集合精确一致为 832/960（86.67%），κ=0.7428。
- 回答 covered-slot 集合精确一致为 245/300（81.67%），κ=0.7618。数值 slot coverage 有 295 条双方均为数值，其中 240 条精确一致（81.36%），平均绝对差 0.1359；另有 5 条一侧为 null 的回答，未从总体分歧清单中删除。
- 共同 slots 下有 45 条 Adequacy 分歧回答、60 条 coverage 分歧回答；若计入 registry/task_role/package coverage 等所有报告字段，共 170/300 条回答至少含一个分歧。详细文件共 420 行（60 条回答级记录、360 条候选级记录）。
- 已输出 `results/formal_common_slot_agreement.json`、`results/formal_common_slot_agreement.md` 和 `results/formal_common_slot_disagreements.jsonl`；原 `formal_interannotator_agreement.*` 与 `formal_disagreements.jsonl` 完整保留为独立 slots 粒度敏感性材料。
- QA 通过：脚本可编译，JSON 与 420 行 JSONL 全部可解析；汇总中的回答数、候选数和分歧行数与文件一致。全程未读取 blind key。

- 2026-09-23T18:58:42Z：最终匿名双标仲裁在未揭盲条件下完成。对300条回答、960个候选计算仲裁前一致性，并依据提示、冻结需求槽、原始名称、PyPI及项目/官方文档复核全部分歧；输出一致性JSON/Markdown、分歧JSONL、300行仲裁JSONL和仲裁摘要。QA通过：300个唯一回答ID、960个候选、60×5设计、需求槽引用有效、回答覆盖等于候选覆盖并集、任务角色/覆盖与Adequacy规则一致。该阶段未读取模型/方法/fold映射。

## 2026-09-24：标注结果CSV与详细报告整理

- 按用户要求新增`script/export_formal_annotations_csv.py`，将最终匿名批次的回答、需求槽、两名独立原始标签、最终仲裁标签、候选包存在性/任务作用/覆盖槽/证据，以及揭盲后的模型、condition、fold和prompt ID连接为一张回答级CSV。
- 输出`results/formal_annotation_results.csv`：300行、42列、300个唯一`blind_answer_id`；模型各100行，Base 60行、BOUND 240行；`candidate_count`合计960，与正式候选总数一致；最终Adequacy分布为83 adequate、71 partially adequate、146 inadequate。CSV使用UTF-8 BOM，数组与嵌套证据以JSON字符串保存在单元格中，兼顾Excel打开和无损复算。
- 为便于详细解读，新增可移植报告`E1_detailed_report.html`及规范化输入`E1_detailed_report_artifact.json`。报告包含4个headline指标、1个Base/BOUND分组柱图、逐模型结果表和一致性表。打包器验证与结构校验通过；当前环境没有Chromium，因此浏览器级桌面/窄屏验证未运行，交付状态为`structural_only`，语义HTML fallback仍完整。
- 按用户后续要求，将详细结果完整并入`design_and_results.md`，不再要求读者跳转HTML才能理解主结论。新增正式样本/槽分布、Base与BOUND标签计数、960候选标签分布、主要非劣性表、三个模型全部A/B/C/D逐折结果、precision—coverage权衡、一致性、ground-truth缺失、CSV字段说明以及rebuttal允许/不允许结论。所有数值均来自最终匿名仲裁和`relevance_metrics_by_model_fold.json/csv`，未混入校准或早期模型可见批次。
