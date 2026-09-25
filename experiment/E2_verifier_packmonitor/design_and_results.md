# E2——Verifier、PackMonitor 与 BOUND 公平对照

## 实验目标

直接回答外部 authoritative verifier 已存在时 BOUND 是否仍有增益，并在共同支持的安装命令场景与 PackMonitor 比较。不能把简单过滤器当作 PackMonitor，也不能只以“离线”场景名称回避负结果。

## 当前完成范围与主要发现（2026-09-24更新）

已完成小规模名称有效性与验证流程对照：三模型post-hoc filter、三模型四折one-shot repair，以及DeepSeekCoder fold-A的Base/BOUND × PackMonitor四条件实验。原设计中的E2输出Adequacy和Task-Relevant Precision尚未完成标注；这些质量终点不能因存在性对照完成而记为完成。

主要发现如下：

- BOUND在三个模型上均减少初始invalid回答及一次修正后、最终过滤前的残余invalid；但Qwen3和Llama-3.1的最终空回答增加，保留候选数下降。
- 在DeepSeekCoder的100个共同安装命令任务中，Base、BOUND-A、Base+PackMonitor、BOUND-A+PackMonitor的invalid回答率分别为45%、29%、4%、4%。PackMonitor对Base与BOUND均提供进一步保护。
- 在已有PackMonitor时，加入BOUND没有显示更低的invalid回答率。组合后空候选率从1%变为0%，只相差一条回答，尚不足以证明额外推荐质量收益。
- PackMonitor在固定token预算下仍可能留下合法名称的未完成前缀，说明最终输出需要完整性检查和重新验证。

## 实际执行方法

### 三种干预及其比较对象

| 分支 | 干预时机 | 操作 | 是否新增生成 |
|---|---|---|---|
| Post-hoc filter | 回答生成后 | 删除被验证器判为invalid的候选，保留通过项及识别出的标准库 | 否，复用已有回答 |
| One-shot repair | 回答生成后 | 反馈拒绝名称，最多修正一次，重验全部新候选，过滤残余invalid | 仅初始含invalid时调用一次 |
| PackMonitor | 逐token生成时 | 在共同支持的安装命令语法下约束可生成名称 | 是，全部重新生成 |

BOUND是参数编辑；它分别与上述三个流程组合。相同模型、相同任务内的比较才是对应分支的配对比较。不同分支改变了输出协议、生成次数或registry口径，不能把其绝对率拼成一个未经控制的总排名。

### 样本冻结与计数

DeepSeekCoder、Qwen3、Llama-3.1分别使用自身的high-risk held-out池，eligible数量为541、409、934。固定seed `20260923`，按`SHA-256(seed:prompt_id)`排序选取每模型100个prompts，保存于`results/manifest.json`。这是模型内的共同任务集；三个模型的100个任务不一定相同，不应描述为跨模型shared set。

同一模型的Base与BOUND A/B/C/D使用相同100个prompts。Base的filter/repair分支共享Base自己的初始回答；每个BOUND fold的分支共享该fold自己的初始回答。已有Base文本在四折结果文件中相同，汇总只取一份，避免重复计权。

| 分支 | 模型/条件 | 每prompt使用的回答 | 汇总规模 |
|---|---|---|---:|
| Post-hoc filter | 3模型 × (Base + 4 folds) | 已有5次生成 | 7,500条回答 |
| One-shot repair | 3模型 × (Base + 4 folds) | 已有generation 0，必要时修正一次 | 去除重复Base后1,500个任务—条件记录 |
| 原生PackMonitor | DeepSeekCoder，Base/BOUND-A各有无约束两条件 | 每条件重新贪心生成一次 | 400条回答 |

Repair的12个逐折原始文件共保存2,400条记录，其中包含每折重复的Base；汇总只取每模型一份Base和四份BOUND。1,500个独立任务—条件记录不等于1,500次新生成，因为通过初始验证的回答无需repair。

### 名称验证的两个口径

Post-hoc filter采用历史model-cutoff标签，其冻结cutoff分别为DeepSeekCoder `2023-11-02`、Qwen3 `2025-04-29`、Llama-3.1 `2024-07-23`。历史查询中发现6个同模型/同cutoff标签冲突，使用`valid-wins`形成内部一致缓存：至少一次成功的存在性查询优先于其他失败记录。冲突保存在`registry_snapshot.json`；该策略是探索性假设，仍需E7复核首发日期与冲突敏感性。

Repair和PackMonitor采用官方冻结commit附带的706,618名称列表。名称先转小写并将连续`-_.`规范化为`-`，再检查列表成员关系。Repair另外允许识别出的标准库；安装命令分支要求只推荐第三方distribution，禁止标准库安装名称。

因此，此处的invalid是“未通过冻结名称列表验证”，不能直接解释为“截至2026-09-23现实中不存在”。列表缺少完整的逐包时间证据，也不等于按评估日期重新建立的全量PyPI快照。虽然可离线复算，repair/PackMonitor结果并未补齐与原model-cutoff完全一致的第二套标签；这仍是E7关联工作。

### 实际repair提示与终态

反馈提示包含原任务、原回答和被拒绝名称，要求返回完整替代列表，格式为`[ANSWER]包名列表[/ANSWER]`，允许真实PyPI分发名或标准库，要求不要重复被拒绝名称。调用原条件模型：Base关闭LoRA，BOUND启用对应fold。采用贪心解码，脚本默认最多128个新token。

修正后重新提取并验证全部候选，包括新引入名称；最终保留验证通过项和标准库。保存四种终态：

| 终态 | 含义 |
|---|---|
| `initial_verified` | 原回答非空且通过验证，未调用repair |
| `repair_verified` | 调用repair后，修正版非空且全部通过 |
| `final_filter` | 最多一次repair后仍有invalid，执行最终过滤 |
| `explicit_refusal_or_empty` | 没有残余invalid，但没有可保留候选 |

`final_filter`之后也可能为空，因此最终空回答率直接检查`final_filtered_packages`，不能只统计`explicit_refusal_or_empty`终态。抽取不到包的回答也可能是格式问题，Empty不应自动等同于明确拒答。这个流程没有安装、import或功能测试，不是真实coding-agent实验。

### 实际PackMonitor配置与公平性边界

冻结官方commit为`8808362e14891fe692b17b8192ed123dff4d64d2`，使用`llguidance==1.1.0`和`guidance-stitch==0.1.5`。原样grammar引用了未声明的`NATATURAL_LANG`，实验保存错误证据，并仅在包装器改为已声明的`NATURAL_LANG`。因此应报告为带最小兼容补丁的官方实现复现。

四个条件均将同一任务包装成“仅输出一个Markdown bash代码块，其中只有一条pip install命令”，要求名称之间用空格分隔，不使用版本、选项、注释、解释或标准库模块。全部使用greedy decoding、64-token最大生成预算；BOUND使用DeepSeekCoder fold A。PackMonitor真实执行生成中约束，未用后处理模拟。

原生对照统计的是正则可提取安装区域内的包名。记录中的`install_region_trigger_rate`实际上是出现可匹配安装区域的比例，不能解释成对所有输出token都验证过的约束覆盖率。未提取到候选的输出单列为空候选，不能算作任务成功。

### 实际指标及分母

| 指标 | 实际计算口径 |
|---|---|
| 初始invalid回答率 | 初始至少含一个invalid候选的记录数 / 全部记录数；也是repair调用比例 |
| 修正后残余invalid率 | 最终过滤前仍含invalid的记录数 / 全部记录数，不只以repair尝试为分母 |
| Repair成功率 | `repair_verified`记录数 / 实际尝试repair的记录数；要求非空且全部通过 |
| 最终空回答率 | 最终保留候选集合为空的记录数 / 全部记录数 |
| 最终平均包数 | 每条记录最终保留候选数的平均，包括通过规则的标准库 |
| 原生invalid回答率 | 提取到的安装候选中至少一个未列入冻结registry的回答数 / 全部回答数 |
| Post-hoc Package-HR | 全部回答中的invalid包数 / (valid包数 + invalid包数)，标准库不入分母 |

BOUND先逐折计算指标，再作四折等权平均；repair成功率也如此，不是将四折所有尝试合并后计算的pooled成功率。Base与BOUND的repair触发集合不同，因此条件性成功率不能单独归因于修正能力更强。

原生PackMonitor两组比较使用2,000次prompt级配对bootstrap、seed `20260923`，同时重采样同一prompt下有/无约束的回答。Repair四折表目前是描述性汇总，没有对应的完整配对效应区间。

## 原设计与尚待完成的评价要求

以下为实验设计要求；实际完成范围以上文和结果表为准，尤其双时间口径与推荐质量标注尚未全部完成。

### 对照问题 A：参数编辑 × 外部验证

在相同任务、生成协议、seed policy 和 frozen registry snapshot/cutoff 下比较：

1. Base；
2. BOUND；
3. Base + post-hoc verifier；
4. BOUND + post-hoc verifier；
5. Base + verifier-guided one-shot repair；
6. BOUND + verifier-guided one-shot repair。

Base 的 filter/repair 分支共享 Base 自己的初始回答，BOUND 分支共享 BOUND 自己的初始回答。Base 与 BOUND 不强行共享同一文本回答，只共享任务和生成协议。

## 对照问题 B：BOUND × PackMonitor

- 优先进行 PackMonitor 兼容性试运行，记录原始代码版本、支持模型、触发语法、约束区域、词表来源和失败信息。
- 至少在共同支持的 `pip install`/安装命令场景比较 Base、BOUND、PackMonitor；资源允许时加入 BOUND + PackMonitor。
- PackMonitor 必须重新进行生成中约束解码，不能对旧回答做 post-hoc 过滤来模拟。
- 如果原版只在安装命令的包名区域触发，则适配输出语法或限定到共同支持任务；不能让 monitor 未触发后据此评价无效。
- 若无法公平复现，只报告兼容性阻塞和适配尝试，不用非等价实现冒充原方法。

## One-shot repair 状态机

1. 对初始回答的全部候选做验证并保存状态。
2. 若存在 invalid candidate 且预算允许，提供 registry 反馈并最多重新生成一次。
3. 对修正版的全部最终候选重新验证，包括新引入的包。
4. 若仍不通过，按预注册策略记录为 `final_filter`、`explicit_refusal` 或 `pipeline_failure`；不得静默计为成功。
5. 保存初始回答、反馈、修正版、最终回答、全部 registry 响应和状态转换。

## Registry 与 cutoff

- 同时报告原论文 cutoff 口径和固定评估日期口径。
- registry response/cache 必须冻结；网络失败、元数据缺失和不存在分开处理。
- PackMonitor 可使用预编译或缓存权威包名列表，不能默认其每次推理必须联网。

## 指标

原设计的Primary：Recommendation Adequacy Rate、Relevant-Package Hit Rate、Task-Relevant Precision、verified valid packages retained per answer。当前仅完成保留候选数量等自动指标；前三项尚未对E2最终回答单独标注，不得使用E1原始回答标签代替。

Secondary：Sample-HR、原论文口径 Package-HR、过滤后 empty rate、repair success、新引入 invalid rate、最终 filter/refusal/failure rate、registry calls、重生成率、额外 tokens、p50/p95 latency，以及 warm/cold cache 成本。

PackMonitor 另报告约束覆盖率、未触发率、约束解码额外延迟与内存。BOUND 的一次性训练/定位成本与 verifier/monitor 的推理成本分开报告。

## 解释边界

- 过滤后 Package-HR 为 0 不等于任务成功；必须同时看 Adequacy 和过滤后剩余内容。
- 更准确的机制差异是：BOUND 推理时不依赖专用包名约束解码器，PackMonitor 推理时执行外部约束。是否形成部署优势必须由数据支持。
- one-shot repair 只称为工具增强验证管线，不称为真实 coding agent；实际 agent 还需要工具执行、环境反馈和多步控制。
- 若 verifier 或 PackMonitor 全面更好，应报告负结果并收窄 BOUND 定位，而不是自动改称“离线优势”。

## 输出

- `results/registry_snapshot.json`
- `results/packmonitor_compatibility.md`
- `results/packmonitor_runtime100_generations.jsonl`
- `results/packmonitor_bound_runtime100_generations.jsonl`
- `results/packmonitor_native100_summary.json`
- `results/all_models_four_folds_repair.json`
- `results/posthoc_filter_results.jsonl`
- `results/repair_generations.jsonl`
- `results/repair_state_transitions.csv`
- `results/latency_and_calls.csv`
- `results/summary.md`

## 实验结果

### 第一阶段：100-prompts post-hoc verifier

状态：计算已完成，但由于历史在线标签存在同-cutoff 冲突，本表是 `valid-wins` 固定快照假设下的探索性结果，暂不用于最终 rebuttal claim。固定 `seed=20260923`，对每个模型从原 held-out 高风险池稳定抽取 100 个 prompts；每个 prompt 使用已有 Base 和四个 BOUND folds 的 5 次回答，共 7,500 条。Base 在四折间完全一致，只计一份。

下表中 BOUND 是四折描述性均值。过滤后的 Sample-HR/Package-HR 按构造均为 0，因此重点同时报告空回答率与每回答保留的 registry-valid 包数。

| 模型 | 条件 | 初始 Sample-HR | 初始 Package-HR | 过滤后空回答率 | 每回答保留 valid 包 |
|---|---|---:|---:|---:|---:|
| DeepSeekCoder | Base | 0.836 | 0.343 | 0.162 | 1.818 |
| DeepSeekCoder | BOUND 四折均值 | 0.337 | 0.143 | 0.093 | 2.544 |
| Qwen3 | Base | 0.884 | 0.343 | 0.132 | 1.836 |
| Qwen3 | BOUND 四折均值 | 0.179 | 0.130 | 0.265 | 1.724 |
| Llama-3.1 | Base | 0.822 | 0.364 | 0.112 | 2.122 |
| Llama-3.1 | BOUND 四折均值 | 0.432 | 0.223 | 0.128 | 2.638 |

解释边界：DeepSeekCoder 上 BOUND+filter 的空回答率低于 Base+filter；Qwen3 上则明显更高且折间差异大，不能声称 verifier 自动解决 utility 问题。该阶段没有人工 Adequacy 标签，不能判断保留包是否足以完成任务。

历史在线 PyPI 标签中发现 6 个同模型/cutoff 冲突。本次探索性汇总先建立一致的离线快照并采用 `valid-wins`：至少一次成功查询是存在性的正证据，旧失败查询可能为瞬时错误；冲突完整保留在 `registry_snapshot.json`。这仍是 model-cutoff 口径，不是 deployment-date snapshot。最终确认性表必须在 E7 的带首发日期冻结快照上重算，并做冲突包敏感性分析。

### GPU 与 PackMonitor 状态

- GPU 2 已通过单 prompt DeepSeekCoder fold-A BOUND adapter 加载和生成 smoke；该输出不纳入指标。
- PackMonitor 官方 commit `8808362e14891fe692b17b8192ed123dff4d64d2` 已冻结并完成静态与动态兼容性审计。官方方法只约束 Markdown `bash` block 中的 `pip install`，因此公平对照统一使用这一共同支持的输出协议，而不把原 `[ANSWER]` 包名列表直接送入无触发区域。
- 官方 grammar 的 `start` 规则误写为未声明的 `NATATURAL_LANG`，原样 matcher 会失败。本实验仅在包装器中将其改为已声明的 `NATURAL_LANG`；官方工作树保持不变。`llguidance==1.1.0` 与 `guidance-stitch==0.1.5` 隔离安装于临时依赖目录，没有污染主环境。

### 第二阶段：100-prompts one-shot repair（探索性）

三个模型均在各自固定的 100-prompt manifest 上比较 Base 与 BOUND fold A；每 prompt 取已有 generation 0，使用 PackMonitor 官方 commit 随附的 706,618 个名称作为离线冻结名称列表，而非经逐包日期核验的deployment-date快照。存在 invalid 时贪心重生成最多一次，随后重新验证所有候选；残余 invalid 必须进入 `final_filter`。

| 模型 | 条件 | 初始 invalid 率 | repair 后仍有 invalid（过滤前） | 最终空回答率 | repair 成功率（尝试中） | repair p50/p95 秒 |
|---|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | Base | 0.740 | 0.430 | 0.250 | 0.243 | 2.969 / 3.467 |
| DeepSeekCoder | BOUND fold A | 0.190 | 0.080 | 0.180 | 0.526 | 3.047 / 3.374 |
| Qwen3 | Base | 0.710 | 0.290 | 0.040 | 0.592 | 0.709 / 1.757 |
| Qwen3 | BOUND fold A | 0.120 | 0.030 | 0.140 | 0.750 | 0.670 / 1.197 |
| Llama-3.1 | Base | 0.700 | 0.280 | 0.010 | 0.600 | 0.775 / 3.607 |
| Llama-3.1 | BOUND fold A | 0.310 | 0.120 | 0.200 | 0.613 | 0.911 / 3.629 |

这一fold-A阶段说明固定一次repair并不保证全部候选通过验证：repair后、最终过滤前仍有3%–43%的回答含invalid。BOUND fold A的残余invalid均低于Base，但Qwen3和Llama-3.1的最终空回答率更高。后续已经补齐A/B/C/D四折，完整结果见下节；每条件仍只取已有generation 0。

详细结果见 `results/posthoc_filter_summary.csv`、`results/repair_summary.md`、`results/repair_generations_qwen3.jsonl`、`results/repair_generations_llama31.jsonl`、`results/manifest.json`、`results/registry_snapshot.json` 与 `results/packmonitor_compatibility.md`。

### 三模型四折 repair sensitivity

在 fold-A 之后按预定 A→B→C→D 顺序补齐所有模型的四折；每折仍为固定100 prompts、每条件已有 generation 0。Base 只取一份，BOUND 指标先逐折计算再取四折均值。

| 模型 | 条件 | 初始 invalid | repair后残余 invalid | 最终空回答 | repair成功率 | 最终包数 |
|---|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | Base | 0.740 | 0.430 | 0.250 | 0.243 | 1.690 |
| DeepSeekCoder | BOUND四折均值 | 0.295 | 0.163 | 0.092 | 0.456 | 2.793 |
| Qwen3 | Base | 0.710 | 0.290 | 0.040 | 0.592 | 3.870 |
| Qwen3 | BOUND四折均值 | 0.155 | 0.055 | 0.260 | 0.658 | 1.720 |
| Llama-3.1 | Base | 0.700 | 0.280 | 0.010 | 0.600 | 3.770 |
| Llama-3.1 | BOUND四折均值 | 0.382 | 0.135 | 0.135 | 0.641 | 3.218 |

BOUND 四折均值在三个模型上均降低初始和 repair 后残余 invalid，但 utility guardrail 并不一致：DeepSeekCoder 最终空回答下降，而 Qwen3 和 Llama-3.1 分别从 0.040/0.010 上升至 0.260/0.135，且最终包数下降。尤其 Qwen3 fold-B 最终空回答率达 0.450。结果支持“在该冻结列表口径下，编辑减少一次修正后仍需最终过滤的回答”，但不支持“该组合无代价地提高推荐质量”；必须另对E2最终回答按E1 Adequacy协议标注，不能直接复用E1原始回答的标签。

#### 绝对变化与折间差异

下表均为BOUND四折均值减Base，比例差用百分点（pp）表示，不是相对降幅。

| 模型 | repair调用率变化 | 过滤前残余invalid变化 | 最终空回答率变化 | 最终平均包数变化 |
|---|---:|---:|---:|---:|
| DeepSeekCoder | −44.50 pp | −26.75 pp | −15.75 pp | +1.1025 |
| Qwen3 | −55.50 pp | −23.50 pp | +22.00 pp | −2.1500 |
| Llama-3.1 | −31.75 pp | −14.50 pp | +12.50 pp | −0.5525 |

减少repair调用意味着在当前触发规则下较少调用额外生成，但不直接等于同等比例的端到端时延节省：还需要验证、模型加载、生成长度和缓存成本。最终过滤后invalid为零是规则的构造结果，不是独立的质量证据。

| 模型 | fold A 残余invalid / 空回答 | fold B | fold C | fold D |
|---|---:|---:|---:|---:|
| DeepSeekCoder | 8% / 18% | 22% / 8% | 7% / 7% | 28% / 4% |
| Qwen3 | 3% / 14% | 3% / 45% | 3% / 28% | 13% / 17% |
| Llama-3.1 | 12% / 20% | 14% / 34% | 17% / 0% | 11% / 0% |

Qwen3各折均出现比Base（4%）更高的最终空回答；Llama的空回答副作用主要集中于A/B折，而C/D为0%。因此不能只报告四折平均，也不能选择最好的一折代替全体。空回答是风险信号，但非空、包数更多也不能自动证明充分性更高。上述差异尚无完整配对区间，不作非劣性或统计显著性声明。

可复算汇总见 `results/all_models_four_folds_repair.md/json`；逐折原始 JSONL 与独立汇总目录均保留。

### PackMonitor 原生约束解码：100-task 小规模对照

在 DeepSeekCoder 的冻结 E2 100-prompt manifest 上，使用共同的 Markdown `bash`/`pip install` 协议、706,618名称冻结 registry、greedy decoding 与64-token预算，重新生成而非后处理旧回答。Base/PackMonitor 共用基础模型和任务；BOUND/BOUND+PackMonitor 共用同一个 fold-A delta 和任务。每条件100条，共400条原生生成。

| 比较 | 条件 | invalid-answer rate | empty rate | 安装区域触发率 | 平均时延（秒） |
|---|---|---:|---:|---:|---:|
| 基础模型 | Base | 0.450 | 0.020 | 0.980 | 0.603 |
|  | PackMonitor | 0.040 | 0.010 | 0.990 | 0.744 |
| 编辑模型 | BOUND fold A | 0.290 | 0.000 | 1.000 | 0.549 |
|  | BOUND fold A + PackMonitor | 0.040 | 0.000 | 1.000 | 0.708 |

以prompt为cluster的2,000次配对bootstrap中，PackMonitor相对Base的invalid-answer绝对差为`-0.410`，95% CI `[-0.510,-0.310]`；BOUND+PackMonitor相对BOUND为`-0.250`，95% CI `[-0.350,-0.160]`。这支持外部生成中约束对Base和BOUND均降低冻结列表下的invalid回答率，并证明两种机制可以组合。反方向的问题则没有得到正向证据：Base+PackMonitor与BOUND+PackMonitor均为4%，未观察到编辑带来的额外invalid率下降；空候选仅相差一条，不能据此声称组合提高推荐质量。已有区间检验的是“增加PackMonitor”，不是“在PackMonitor上增加BOUND”。

64-token的Base+PackMonitor条件仍有4%的回答被判为invalid。对此条件4例的逐例审计显示，最大token预算截断了合法包名前缀，例如`slack-`或`google-p`；不能将这项审计无条件推广到BOUND+PackMonitor的每个失败案例。这些证据说明约束解码并不自动解决强制截断后的输出完整性，最终候选仍应重新验证。128-token事后敏感性中PackMonitor invalid为3%，剩余三例依然是重复生成后在预算边界截断。再对最初4例做256-token定向诊断时仍有2例失败，且PackMonitor平均时延升至8.95秒；该定向样本不能估计总体率，也不替换冻结的64-token主表。

| token预算 | 范围 | Base invalid | Base+PackMonitor invalid | 用途 |
|---|---|---:|---:|---|
| 64 | 冻结100任务 | 45/100 | 4/100 | 主结果 |
| 128 | 同100任务 | 47/100 | 3/100 | 事后预算敏感性 |
| 256 | 原64-token失败的4任务 | 4/4 | 2/4 | 定向诊断，不能估计总体率 |

主表中增加PackMonitor的平均时延差分别为Base约+0.141秒、BOUND约+0.159秒。这只是当前runner与缓存状态下的观测，包含约束构建/复用等实现因素，且各条件输出长度不同；没有完整warm/cold拆分，不应外推为普遍部署开销。全部四条件主生成记录均未报告generation error，但没有程序异常不代表输出满足任务要求。

以上对照只评估安装区域语法和冻结registry成员约束。它不验证任务相关性、安装/导入成功、版本与API兼容或端到端任务成功。E1结果可以提供风险背景，但不能代替这些新回答的充分性标签。机器可读结果及逐回答原文见`results/packmonitor_native100_summary.json`、`results/packmonitor_runtime100_generations.jsonl`与`results/packmonitor_bound_runtime100_generations.jsonl`。

## 复核与复现入口

| 内容 | 脚本 | 数据/汇总 |
|---|---|---|
| 抽样与post-hoc过滤 | `script/run_posthoc_verifier.py` | `results/manifest.json`、`results/posthoc_filter_results.jsonl`、`results/posthoc_filter_summary.csv` |
| 一次修正和最终过滤 | `script/run_one_shot_repair.py` | `results/repair_generations*.jsonl`、`results/repair_state_transitions.csv` |
| 四折汇总、Base去重 | `script/summarize_all_repair_folds.py` | `results/all_models_four_folds_repair.json`、同名`.md` |
| 原生约束生成 | `script/run_packmonitor_native_smoke.py`、`script/run_packmonitor_native_100_gpu2.sh` | 两个`runtime100_generations.jsonl`文件，完整文件名见上文 |
| 配对bootstrap | `script/summarize_packmonitor_native.py` | `results/packmonitor_native100_summary.json`、同名`.md` |
| 事后截断诊断 | 同一原生生成runner，不同token预算/任务子集 | `results/packmonitor_runtime100_maxtok128_generations.jsonl`、`results/packmonitor_truncation_diag256_generations.jsonl` |

此次文档更新未重新训练或生成，依据已落盘的结果与实现核对；四折变化表由未舍入的汇总值相减得到。阶段表保留三位小数，临界值的展示舍入不影响原始JSON中的数值。

## 当前可报告结论与未完成项

可报告的限定结论：在模型各自的100条高风险held-out任务上，BOUND降低冻结名称列表下的初始验证失败和一次修正后残余失败，但Qwen3和Llama-3.1存在最终空候选增加的代价。在DeepSeekCoder fold-A的100条安装命令任务上，PackMonitor对Base/BOUND均显著降低invalid回答率；加入BOUND未进一步降低已有PackMonitor的invalid率。生成中约束仍需处理预算截断与最终候选验证。

在补齐下列证据前，E2只能作为带明确限制的小规模名称验证对照，不能称为完整推荐质量实验或实际agent任务验证：

1. 按E1协议对E2过滤后、repair后及PackMonitor输出进行独立充分性/相关性审计；若使用agent模拟标注，明确披露，不能称为真实人工用户研究。
2. E7复核6个历史冲突，并提供model-cutoff与共享评估日期两套可追溯标签；当前列表成员关系不能替代完整时间证据。
3. 为三模型四折repair补充prompt级配对差异区间，保留折间异质性，不把固定adapter结果推广到所有训练seed。
4. 若要声称成本优势，补充输出长度、warm/cold缓存和端到端成本拆分；若要声称任务成功，另需隔离执行与功能测试。

## 对照审稿问题：当前E2能回答什么、还缺什么（2026-09-24）

### 核对范围与总体判断

问题来源：[icse rebuttal_question.md](../../icse%20rebuttal_question.md)，包含Response #677A的8项、#677B的14项、#677C的8项。本节逐项归类，但判断对象限于**当前E2已落盘的结果**；提到E1/E3/E4等表示需要衔接的证据，不表示这些实验已经完成对应要求。结果依据为本文件三阶段表、`all_models_four_folds_repair.json`和`packmonitor_native100_summary.json`。

整体评价：**可带限制地报告，不能宣称已完整解决审稿意见。**E2实质补上了外部验证与原生PackMonitor基线，最直接回应A-Q1和C-Q1；但“补上对照”不等于“证明BOUND优于对照”。当前结果反而要求收窄优势表述：PackMonitor在所测安装命令任务上的invalid率低于单独BOUND（4%对29%），已有PackMonitor时加入BOUND没有观察到进一步下降（4%对4%）。这不证明两者普遍等价或编辑永远无用，也不支持编辑必不可少。

下表中“部分回答”指问题中的一个子问题有数据，不能据此将整条意见标为解决；“未覆盖”指E2没有相关直接证据。

### Reviewer A（#677A）

| 问题 | E2覆盖程度及现有证据 | 不足与回应边界 |
|---|---|---|
| Q1：工具增强/agentic验证能否相当或更好；编辑的必要性与优势 | **直接相关、部分回答。**三模型有filter及一次repair；DeepSeekCoder有四条件原生PackMonitor。PackMonitor相对Base下降41 pp，配对95% CI为[−51,−31] pp；相对BOUND下降25 pp，[−35,−16] pp | 能回答外部约束在本测试中有效，不能证明BOUND整体更好或必要。未运行真实agent、在线PyPI工具交互；尚缺同质量约束下的完整成本比较与E2输出充分性 |
| Q2：是否用真实但无关包替换幻觉包 | **未直接回答语义核心，仅提供退化信号。**Qwen3/Llama的repair最终空回答增加，候选数下降 | 名称列表、空回答率、包数均无法识别“每题requests”。须另标E2最终回答的相关性、Adequacy及槽覆盖；不能借用E1旧回答标签 |
| Q3：定位中的多token、共享前缀和token碰撞 | **未覆盖。**PackMonitor截断诊断只涉及推理输出完整性 | 不能用该诊断回答定位风险分数如何处理首token代理；需E6检查实际tokenization、候选碰撞与梯度退化 |
| Other：有效性边界的表征/分数分离证据 | **未覆盖** | HR下降或验证器有效不证明稳定几何边界；需独立候选分数/表征分析与E5/E6消融 |
| Other：别名、重命名、namespace、import/distribution、cutoff后包 | **部分澄清流程，未完成边界审计。**记录了标准库处理、名称规范化、两类registry口径及6项冲突 | 规范化不能解决语义映射；冻结名称列表不能判定逐包发布时间。需E4/E7保留原名、证据、时间与未知状态 |
| Other：只测高风险提示 | **未解决。**E2仍是各模型自身high-risk held-out抽样 | 不能把100条称作自然分布或跨模型shared set；需E3未按风险筛选的独立证据 |
| Other：统计证据与稳定性 | **部分回答。**原生约束两组配对bootstrap，repair保留三模型四折及异质性 | repair尚无完整配对CI；PackMonitor仅一模型一折、一次greedy生成；不涵盖重新编辑/训练seed的不确定性 |
| Other：创新主要在应用建模与已有组件整合 | **仅能帮助定位贡献。**实证区分参数编辑、后处理与生成中约束 | 不证明新编辑原语，也不分离风险分数/定位/损失的独立贡献；需收窄表述并结合E5/E6 |

### Reviewer B（#677B）

| 问题 | E2覆盖程度及现有证据 | 不足与回应边界 |
|---|---|---|
| Q1：代码生成与包推荐提示的具体区别 | **仅补充E2自身协议。**说明了原列表、repair列表和安装命令包装 | 不能代替原论文三种任务的完整prompt模板及差异说明；应补原RQ2材料 |
| Q2：生成代码是否语法检查/编译/执行 | **未覆盖。**E2验证名称/安装区域，不检查Python程序 | pip命令能抽取或生成无异常不等于代码语法正确；需E4的AST/compile与E8功能验证 |
| Q3：来源包关联、适用性、召回、通用包退化 | **未解决核心要求。**保留valid包数量只是诊断 | 需明确来源关联保留/恢复比例及不能恢复原因，并在可靠子集报告Source-Package Hit/参考覆盖；E2没有这些质量结果，不能称为recall实验 |
| Other：真实项目或用户研究 | **未覆盖** | 合成任务上的工具增强管线不是实际项目；agent模拟标注也不是用户研究；需E8或真实用户研究 |
| Other：import-to-package映射可靠性 | **未覆盖原RQ2映射。**安装命令直接抽取distribution可避免本分支依赖该映射器 | 不能由本分支绕过映射推断原RQ2映射正确；需E4独立审计 |
| Other：HumanEval配置和证据价值 | **未覆盖** | 需单独说明原HumanEval设置、执行与验证；E2不能代替 |
| Other：合成提示、热门偏差、长尾与时间范围 | **只澄清限制，未补外部有效性证据** | 100条高风险合成提示不能说明长尾或真实请求；需E3/E7及真实任务证据，取消风险筛选也不自动消除合成/热门偏差 |
| Other：模型选择及规模 | **未覆盖规模问题。**repair仍为原三模型，PackMonitor仅DeepSeekCoder | 没有更大或更强的新近模型对照；不能以三模型四折替代跨规模证据 |
| Other：工程导向创新 | **仅帮助定位，不验证独立技术新颖性** | 可定位为特定失败模式的编辑与验证集成；是否有独立技术贡献需其他消融支持 |
| Other：开发流程位置与结论范围 | **可作有证据的定位说明，未验证下游。**展示“候选生成→名称验证→一次修正→重验/过滤” | BOUND处理候选生成环节；之后仍需任务适配、依赖解析、安装/import、API兼容、功能测试和开发者集成。不能称为完整可靠代码生成 |
| Other：Figure 1可读性与图文一致性 | **未覆盖** | 属于论文修订，不能由新增结果替代 |
| Other：ECMWF动机及具体包解释 | **未覆盖该例的事实与任务适用性核验** | 需单独核验名称、生态与用途；E2总表不验证图中例子 |
| Other：module等术语混用 | **仅本实验已区分distribution、标准库和编辑模块** | 仍需通篇统一术语及import/distribution区别 |
| Other：指标标准名称与解释 | **可澄清本实验指标，未完成全论文改名。**已写明invalid率、repair成功率、空候选率的分母 | `1−Sample-HR`只表示该口径下未发现名称错误，不是功能任务成功；`1−Package-HR`也不是任务相关性precision。Valid-Rate不应称为recall |

### Reviewer C（#677C）

| 问题 | E2覆盖程度及现有证据 | 不足与回应边界 |
|---|---|---|
| Q1：部署场景、强制验证/filter/PackMonitor、同预算、编辑增量 | **最直接回应，但仍部分完成。**有最终强制过滤、一次repair、原生PackMonitor以及组合；原生四条件在同一模型/100任务/greedy64-token协议下运行 | 相同token上限不等于相同延迟/计算预算；各分支registry/协议不同，不能跨表总排名。PackMonitor上加入BOUND的invalid增益未见，质量/成本增益未证实；真实agent与在线registry未测 |
| Q2：未经风险筛选的绝对收益、每千次事件、CI、拒答 | **不回答目标分布，只提供高风险集的局部CI/空候选统计** | 不可把45%→4%换算成每千次真实部署请求收益；E2没有未筛选样本，empty也不等于拒答。需E3在其冻结集合上回答，并保留合成基准限制 |
| Q3：普通/全模块LoRA、其他定位、独立风险贡献与稳定边界 | **未覆盖** | verifier/PackMonitor不是定位消融；需E5/E6同预算对照与独立机制证据 |
| Q4：安装/import/API/版本/语义/执行；原本正确提示的替换、拒答、新包排斥 | **仅部分副作用证据。**Qwen3/Llama repair最终空回答分别增加22.0/12.5 pp | 没有执行或E2语义标签；没有独立定义的“原本task-appropriate”子集，未区分明确拒答/解析失败，也未审计cutoff后合法包的系统性排斥。不能说保持依赖正确性 |
| Other：相对PackMonitor及相关编辑方法的创新 | **PackMonitor基线缺口已实质补充。**真实逐token约束、固定版本及最小grammar补丁，含组合结果 | 仅一模型一折100任务；不证明比PackMonitor更优，也不回答CREME/DINM/TruthX/RaLFiT相关机制的独立增量。不能用“离线”否定可缓存列表的PackMonitor |
| Other：共同提示集与跨模型风险集评估 | **未覆盖。**只保证每模型内部条件共享任务 | 三模型分别抽100条不构成跨模型共同集；需E3共享集及cross-risk矩阵 |
| Other：更强模型、真实agent、mandatory verifier/RAG/PackMonitor/组合 | **基线清单部分完成。**有post-hoc filter、最终强制过滤、一次反馈修正、PackMonitor与BOUND组合 | 没有RAG、更强模型或实际工具执行agent；强制保留列表内名称不等于完整智能体环境 |
| Other：可完整核验的artifact | **本地证据链明显补强。**manifest、registry冲突缓存、完整生成、四折汇总和统计脚本可追溯 | 本地存在不等于已更新公开Zenodo；仍需打包冻结名称列表/哈希、补丁/依赖、原始筛选与排除轨迹及命令，消除对临时目录的依赖，并另做公开artifact验证 |

### A-Q1/C-Q1的三个核心判断必须分开

1. **外部验证是否有效？有直接证据。**在当前安装命令任务中PackMonitor显著降低列表外名称；后处理最终零invalid是规则保证，不能与未经最终过滤的模型输出率混为一谈。
2. **编辑在一次repair前是否减少失败和调用？有描述性证据。**三个模型的调用率降低44.50/55.50/31.75 pp，过滤前残余invalid降低26.75/23.50/14.50 pp；但Qwen3/Llama空候选增加。过滤完成后双方都只保留列表通过项，不能再声称最终名称错误率更低。
3. **编辑在已有PackMonitor时是否有额外收益？尚未证明。**invalid率4%对4%，不能解释成等价检验通过；质量与完整成本未测。当前只证明技术上能够组合，而非组合有独立实用增益。

部署定位可以据此收窄为：研究开放权重模型的候选生成阶段，参数编辑不依赖专用推理时包名约束解码器，可与外部验证并用。**尚无证据证明离线、低延迟或成本优势**；PackMonitor可以缓存名称列表，而BOUND还有一次性定位/编辑成本。这里是机制差异与待验证场景，不是已证实的优势。

### 补证优先级与不应使用的结论

| 优先级 | 最小补证/修订项 | 主要对应问题 |
|---|---|---|
| P0：使用现有结果前 | 保留上述范围限制和负面结果；全文区分列表成员、时间有效性、任务适配与执行成功；公开描述最小兼容补丁 | A-Q1/Q2、B-Q3、C-Q1/Q4 |
| P0：若要声称质量优势/保持 | 对固定配对E2最终回答补相关性、Adequacy、槽覆盖及空输出原因；独立标签与未知处理、差异CI；不要挑选有利回答 | A-Q2、B-Q3、C-Q4 |
| P0：若要声称现实PyPI有效性 | E7校验两套时间标签、列表覆盖/未知及6个冲突；保留原输出名，不悄悄修正映射后计成功 | A有效性边界情况、C-Q4 |
| P1：量化编辑的额外价值 | 补BOUND+verifier相对Base+verifier的prompt配对CI，直接比较BOUND+PackMonitor与Base+PackMonitor；测同质量/合理预算下的完整成本 | A-Q1、A统计稳定性、C-Q1 |
| P1：外部有效性/完整场景 | 衔接E3未筛选共享集及跨风险集；E8小规模真实任务和执行；若要声称agent收益，加入真实工具反馈环境 | A高风险范围、B真实项目、C-Q2/Q4及agent要求 |
| P1：材料可复现 | 打包运行依赖、补丁、冻结词表及哈希、抽样/排除记录、全部输出与统计入口，并检查公开artifact可运行 | C完整核验材料 |

上述是证据缺口与建议，不是本次已经启动的新增实验。若时间不足，可保留小规模对照并主动收窄论文结论，而不是把所有缺口都包装成已解决。

不可使用的结论包括：“BOUND比PackMonitor更好”“强制验证后编辑仍显著提升质量”“过滤后零幻觉意味着任务成功”“empty上升证明过度拒答”“已验证真实agent”“已证明离线优势”“三模型四折足以说明跨规模/训练seed稳定”。这些表述均超出现有证据。

### 可用于rebuttal的中文事实性表述草稿

我们补充了固定高风险held-out任务上的后处理验证、一次验证引导修正，以及在共同安装命令协议下的原生PackMonitor对照。DeepSeekCoder的100任务中，Base、BOUND、Base+PackMonitor与BOUND+PackMonitor的冻结名称列表invalid率分别为45%、29%、4%和4%。PackMonitor对Base及BOUND均带来进一步下降；但当前未观察到在PackMonitor上加入编辑的额外invalid率收益。三模型四折repair中，编辑减少初始验证失败和修正后残余失败，但Qwen3与Llama-3.1出现最终空候选增加。我们据此不再将参数编辑描述为外部验证的替代或已证实更优的方案。现有E2证据限于名称有效性和管线行为，推荐充分性、安装/执行及真实agent收益仍需单独验证。
