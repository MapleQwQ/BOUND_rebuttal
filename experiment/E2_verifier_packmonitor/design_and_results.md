# E2——Verifier、PackMonitor 与 BOUND 公平对照

## 实验目标

直接回答外部 authoritative verifier 已存在时 BOUND 是否仍有增益，并在共同支持的安装命令场景与 PackMonitor 比较。不能把简单过滤器当作 PackMonitor，也不能只以“离线”场景名称回避负结果。

## 对照问题 A：参数编辑 × 外部验证

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

Primary：Recommendation Adequacy Rate、Relevant-Package Hit Rate、Task-Relevant Precision、verified valid packages retained per answer。

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
- `results/packmonitor_generations.jsonl`
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

三个模型均在各自固定的 100-prompt manifest 上比较 Base 与 BOUND fold A；每 prompt 取已有 generation 0，使用 PackMonitor 官方 commit 随附的 706,618 个 PyPI 名称作为无网络 deployment registry。存在 invalid 时贪心重生成最多一次，随后重新验证所有候选；残余 invalid 必须进入 `final_filter`。

| 模型 | 条件 | 初始 invalid 率 | repair 后仍有 invalid（过滤前） | 最终空回答率 | repair 成功率（尝试中） | repair p50/p95 秒 |
|---|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | Base | 0.740 | 0.430 | 0.250 | 0.243 | 2.969 / 3.467 |
| DeepSeekCoder | BOUND fold A | 0.190 | 0.080 | 0.180 | 0.526 | 3.047 / 3.374 |
| Qwen3 | Base | 0.710 | 0.290 | 0.040 | 0.592 | 0.709 / 1.757 |
| Qwen3 | BOUND fold A | 0.120 | 0.030 | 0.140 | 0.750 | 0.670 / 1.197 |
| Llama-3.1 | Base | 0.700 | 0.280 | 0.010 | 0.600 | 0.775 / 3.607 |
| Llama-3.1 | BOUND fold A | 0.310 | 0.120 | 0.200 | 0.613 | 0.911 / 3.629 |

结果一致说明固定一次 repair 并不保证最终有效：三个模型在 repair 后仍有 3%–43% 的回答含 invalid，必须执行最终过滤；因此论文不能把“一次反馈重生成”写成强制 verifier 保证。BOUND fold A 的残余 invalid 均低于 Base，但 Qwen3 和 Llama-3.1 的最终空回答率反而更高。目前仍只有一个 BOUND fold、每 prompt 一条回答，不能作总体结论；fold-B sensitivity 已启动。

详细结果见 `results/summary.md`、`results/posthoc_filter_summary.csv`、`results/repair_summary.md`、`results/qwen3_repair/`、`results/llama31_repair/`、`results/manifest.json`、`results/registry_snapshot.json` 与 `results/packmonitor_compatibility.md`。

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

BOUND 四折均值在三个模型上均降低初始和 repair 后残余 invalid，但 utility guardrail 并不一致：DeepSeekCoder 最终空回答下降，而 Qwen3 和 Llama-3.1 分别从 0.040/0.010 上升至 0.260/0.135，且最终包数下降。尤其 Qwen3 fold-B 最终空回答率达 0.450。因而结果支持“编辑与 verifier 可互补地降低不存在名称”，但不支持“该组合无代价地提高推荐质量”；是否充分仍必须由 E1 Adequacy 审计判断。

可复算汇总见 `results/all_models_four_folds_repair.md/json`；逐折原始 JSONL 与独立汇总目录均保留。

### PackMonitor 原生约束解码：100-task 小规模对照

在 DeepSeekCoder 的冻结 E2 100-prompt manifest 上，使用共同的 Markdown `bash`/`pip install` 协议、706,618名称冻结 registry、greedy decoding 与64-token预算，重新生成而非后处理旧回答。Base/PackMonitor 共用基础模型和任务；BOUND/BOUND+PackMonitor 共用同一个 fold-A delta 和任务。每条件100条，共400条原生生成。

| 比较 | 条件 | invalid-answer rate | empty rate | 安装区域触发率 | 平均时延（秒） |
|---|---|---:|---:|---:|---:|
| 基础模型 | Base | 0.450 | 0.020 | 0.980 | 0.603 |
|  | PackMonitor | 0.040 | 0.010 | 0.990 | 0.744 |
| 编辑模型 | BOUND fold A | 0.290 | 0.000 | 1.000 | 0.549 |
|  | BOUND fold A + PackMonitor | 0.040 | 0.000 | 1.000 | 0.708 |

以prompt为cluster的2,000次配对bootstrap中，PackMonitor相对Base的invalid-answer绝对差为`-0.410`，95% CI `[-0.510,-0.310]`；BOUND+PackMonitor相对BOUND为`-0.250`，95% CI `[-0.350,-0.160]`。这说明外部生成中约束对Base和BOUND均有额外存在性收益，并且两种机制在实现上可以组合。相应地，不能把“已有外部约束后编辑必然没有价值”或“编辑能替代外部验证”作为未经限定的结论。

64-token约束条件仍有4%的回答被判为invalid。逐例审计确认它们均在最大token预算处截断了合法包名前缀，例如`slack-`或`google-p`；这不是grammar允许了一个完整的registry外名称，却说明约束解码并不自动解决强制截断后的输出完整性，最终候选仍应重新验证。128-token事后敏感性中PackMonitor invalid为3%，剩余三例依然是重复生成后在预算边界截断。再对最初4例做256-token定向诊断时仍有2例失败，且PackMonitor平均时延升至8.95秒；该定向样本不能估计总体率，但进一步表明不能把简单增加预算解释为完整性保证。敏感性不替换冻结的64-token主表。

以上对照只证明安装区域语法和冻结registry成员约束。它不验证任务相关性、安装/导入成功、版本与API兼容或端到端任务成功；任务充分性应与E1的负面Adequacy结果联合解释。机器可读结果及逐回答原文见`results/packmonitor_native100_summary.json`、`results/packmonitor_runtime100_generations.jsonl`与`results/packmonitor_bound_runtime100_generations.jsonl`。
