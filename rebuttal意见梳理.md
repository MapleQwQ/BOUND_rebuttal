# ICSE 2027 BOUND：审稿意见梳理与回应准备

本文基于本地三份完整审稿意见、投稿 PDF、LaTeX 正文、BOUND 的实现及保留数据整理。阅读日期：2026-09-23。未运行模型训练、生成或外部包安装；未独立查证审稿人提到的外部论文和上游数据集。下文明确区分审稿人判断、本地核实事实与建议开展的工作，不能把建议实验写成已经完成的结果。

## 1. 总体判断

目前是一位 Weak accept、两位 Weak reject。共同争议不是 BOUND 是否降低了论文定义的包名幻觉率，而是：指标能否支持推荐质量的结论、在外部注册表验证可用时有什么增量价值、定位和编辑的独立贡献是否充分证明，以及高风险小模型实验能否支撑更宽泛的部署论述。

| 维度 | A | B | C |
| --- | --- | --- | --- |
| Overall merit | 3 / Weak accept | 2 / Weak reject | 2 / Weak reject |
| Novelty | 3 / Substantial | 2 / Incremental | 2 / Incremental |
| Rigor | 3 / Good | 3 / Good | 2 / Fair |
| Relevance | 3 / High | 3 / High | 1 / Limited |
| Verifiability and Transparency | 3 / Good | 3 / Good | 3 / Good |
| Presentation | 3 / Good | 3 / Good | 3 / Good |

三人均肯定材料可访问、表达较清楚；A 和 B 尤其认可方法设计及消融。C 的 artifact assessment 为 Satisfactory，但明确说只核查了可访问性，没有执行代码。因此，“审稿人认可 artifact”不能等同于实验结果已经被独立复现。

优先级判断：B 明确说 Rigor 部分决定其推荐，其最核心问题是推荐适用性；C 对必要性、创新性、评测范围同时不满，需要证据与定位共同回应；A 已支持录用，但其三个明确问题也必须正面回答。不能据此预测任何一位一定改分。

## 2. 论文目前实际证明了什么

BOUND 首先根据幻觉包与有效包候选的 logit 对比构造风险信号，用 gradient-times-weight 识别敏感的 transformer 投影模块；然后通过 LoRA 和三个目标——Valid-NLL、Hall-UL、Locality-KL——进行局部编辑。

评测使用 DeepSeek-Coder-6.7B-Instruct、Qwen3-8B、Llama-3.1-8B-Instruct。每个模型独立筛选高风险 prompts：基模生成五次，至少三次含幻觉才保留。三组高风险集合分别有 741、609、1,134 个 prompts；各有四个独立的 50 条编辑集合，余下 541、409、934 条作为 unseen。跨任务和消融分别使用 unseen 中的 100 条 prompts。

论文报告编辑集 Package-HR 相对下降 79.9%，unseen 相对下降 65.4%，代码生成与 pip install 的 Package-HR 相对下降分别为 12.8% 和 34.0%。这些是相对降幅，不是百分点。四个编辑集合不是常规意义上轮换测试集的四折交叉验证；四个编辑模型使用同一个对应的 unseen 集。

这些证据最直接支持：在指定模型和高风险测试分布上，BOUND 降低 cutoff-aware PyPI 判定下的包名错误，并在部分任务格式中保持了这一趋势。它们还不足以单独证明语义正确的依赖推荐、端到端代码正确性、自然请求分布上的收益，或存在可直接观测的稳定内部“边界”。

## 3. Reviewer A：支持，但希望补齐效用和方法细节

认可点：问题重要且具有供应链风险；三种损失互补且动机合理；消融暴露了其他方法靠抑制输出降低幻觉的问题；方案轻量；整体评测和写作较好。

主要担忧：

1. package-validity boundary 更多是解释性设定，缺乏编辑前后表征或包分数分离的直接证据。
2. “包存在”不代表“包适合当前任务”。
3. 缺少查询 PyPI 的工具增强/agentic 基线，无法充分证明模型编辑的优势。
4. 高风险筛选限制结论范围；统计证据不足。
5. next-token 风险分数如何处理多 token 包名、共享前缀及 token 碰撞，正文不明确。
6. 重命名、别名、namespace、import 名与 distribution 名差异、cutoff 后合法包需要说明。

明确提出的三个问题：

| 编号 | 问题 | 所需回应 |
| --- | --- | --- |
| A-Q1 | PyPI 工具验证能否达到同样或更好的效果？为什么需要编辑？ | 明确使用场景，补相同条件下的验证基线，衡量编辑的额外收益与成本 |
| A-Q2 | 如何避免用真实但无关的包替换幻觉包？ | 提供语义适用性证据，不能仅重复 Valid-Rate |
| A-Q3 | 多 token 包名如何参与定位？ | 精确描述首 token 实现、重复 token 去重、跨集合碰撞及局限 |

回应重点：保留其对任务建模和轻量方案的认可，承认“boundary”在现稿中的证据层级，不把性能改善解释成内部机制已被证明。

## 4. Reviewer B：核心否定点是推荐质量没有被测量

B 很认可 introduction、技术描述和复现包；其 Weak reject 主要由评测有效性驱动，并非认为整套方法毫无价值。

最重要的反例：对所有任务都回答 requests，可以得到 Package-HR=0、Sample-HR=0、Valid-Rate=1，却没有任务效用。这个反例指出的是指标的识别能力不足，并不表示 B 已证明 BOUND 实际退化成这种行为。回应需要证明实际结果没有这一退化，而不是否认反例成立。

B 的六条主要弱点：

| 编号 | 内容 | 对当前结论的影响 |
| --- | --- | --- |
| W1 | 只测存在性，未测适用性，也无真实项目对照 | “可靠推荐”的含义超出证据 |
| W2 | 无 recall、无长尾分析 | 无法证明需要的包被保留，可能偏向热门通用包 |
| W3 | RQ2 依赖未经验证的基模进行 import→PyPI 映射，代码自身也未作为可运行成果验证 | 评测混合生成模型和映射器误差，不能推出代码质量改善 |
| W4 | 三种任务没有明确 prompt 模板 | 读者难以判断跨任务差异与可复现性 |
| W5 | 数据合成、热门包偏置、2023 时间范围；三个模型的选择无充分理由 | 外部有效性有限 |
| W6 | HumanEval 的设置和验证方法不清楚 | 表中的小幅变化不足以证明无能力损失 |

B 建议恢复 prompt 与源包的对应关系，或使用真实项目需求及依赖声明，或者做用户研究。其“top 5,000、Llama-2 70B、2023”等具体上游构造描述来自审稿意见，本次未独立验证，不应未经查证直接照写为作者确认事实。

对 recall 建议应认真采纳但精确定义：若每条 prompt 只有一个来源包，命中该包是 reference-package hit/recall，不能直接视为对全部合理依赖的完整 recall。其他包也可能是合理替代；项目 manifest 也可能包含开发依赖、可选依赖和与当前任务无关的依赖，需先界定任务所需集合。

明确提出的三个问题：

| 编号 | 问题 | 本地状态 |
| --- | --- | --- |
| B-Q1 | 代码生成 prompts 到底是什么，与包推荐有何不同？ | 代码中有完整 system 模板；共享 task 内容，分别要求包列表、Python 代码、pip 命令，可直接澄清并给例子 |
| B-Q2 | 是否检查语法？ | 实现用 ast.parse 辅助提取 imports，失败后回退文本扫描；没有语法通过率或执行结果，不能回答为已验证代码正确性 |
| B-Q3 | 是否保留 prompt 与源包链接？为什么不用它测适用性？ | 当前高风险数据字段中有 id/dataset/question，没有显式 originating package 字段；valid_reference 是基模已生成的有效包，不是源包 ground truth |

其他修改：放大 Figure 1；说明 ECMWF 背景；解释例子中的领域包、通用包及错误候选；区分 transformer module 与 Python import module；澄清 package/library/dependency；可考虑更直观的指标名称。B 关于 Figure 1 没有分离线的表述不完全符合当前投稿 PDF：图中可见灰色虚线及绿色/红色闭合区域。但图中文字明显小于正文，且“示意图还是实测表征图”仍应说明，不值得把回应重点放在反驳这条视觉描述上。

## 5. Reviewer C：质疑部署必要性、增量贡献和外推范围

C 承认幻觉会导致安装失败和供应链风险，也认可离线、无网络或没有强制 verifier 的开放权重场景可能有价值。主要问题是现稿没有把这些场景明确为研究对象，却讨论了更宽泛的现代 coding agents。

五条主线：

1. **部署必要性**：既然可以强制查注册表，为什么还要在模型内部学习存在性？需要对照 mandatory verification、post-hoc filtering、PackMonitor，以及 BOUND+verifier。
2. **创新性**：C 把 PackMonitor 视为直接竞争方案，把 CREME、DINM、TruthX、RaLFiT 视为邻近技术。需要解释具体差异和独立增益；这些外部方法的细节应另行阅读原文核实。
3. **选择偏差**：高风险集合是压力测试，不能代表自然请求分布；模型各自使用不同集合，跨模型直接比较也受限制。
4. **正确性范围**：存在性不能代表 install/import 成功、API/版本兼容、任务适用或安全；还应观察原本正确的任务被编辑破坏的情况。
5. **定位证据**：随机模块消融不足以区分风险分数、选层方法、参数预算和 LoRA 本身的贡献，更不能证明稳定的内部 boundary。

明确提出的四组问题：

| 编号 | 问题 | 优先证据 |
| --- | --- | --- |
| C-Q1 | 目标部署场景是什么？与强制 PyPI、过滤、PackMonitor 同预算比较如何？ | 一致的模型/prompts/注册表口径；有效输出质量、延迟、调用次数、重试次数；BOUND+verifier |
| C-Q2 | 未筛选的自然 prompt 分布上是否有收益？ | 基线率与绝对降幅、每千次生成事件、CI、拒答率；更强模型或 agent 作为范围扩展 |
| C-Q3 | 相对普通/全模块 LoRA、CREME/DINM 式定位和其他 saliency，独立贡献是什么？ | 控制损失和预算的定位对照；普通 LoRA 对照；分数分离/跨折稳定性分析 |
| C-Q4 | 更严格正确性下收益是否保留？是否破坏原来正确的推荐或排斥新合法包？ | 安装/import/语义/执行的分层验证；原本低风险或正确样本上的回归分析 |

回应重点：承认查注册表是强有力的存在性验证方式；把 BOUND 放在有明确约束的内部缓解与辅助验证位置。没有实验前不要声称一定更快、更准确或能够替代工具验证。

## 6. 跨审稿人的共性与处理顺序

| 优先级 | 主线 | 审稿人 | 当前可澄清部分 | 仍需证据部分 |
| --- | --- | --- | --- | --- |
| P0 | 存在性不等于任务适用性 | A/B/C | 限定 valid 的定义与贡献范围 | 推荐语义审核、源包命中、真实任务验证 |
| P0 | 外部验证可用时的额外价值 | A/C | 明确离线/受限部署与互补关系 | Base+verifier、BOUND+verifier 等公平对照 |
| P0 | RQ2 测量链是否可信 | B，兼及 A/C | 提供三类 prompt 和映射模板；解释解析逻辑 | 映射准确率、语法通过率、适当的执行验证 |
| P1 | 定位/LoRA 的独立贡献 | C，兼及 A/B | 承认已有 primitive，细化任务贡献 | 同损失、同预算的定位比较和普通 LoRA |
| P1 | 高风险筛选与泛化 | A/C，兼及 B | 明确 conditional stress test | 未筛选集合、共同集合、原本正确样本 |
| P1 | boundary 的机制证据 | A/C | 明确操作性定义，避免实测表征暗示 | 独立候选上的分数变化、定位稳定性等 |
| P1 | 统计和 HumanEval | A/B/C | 说明四个编辑集合与重复生成单位 | prompt 层面的区间、折间变化、完整 HumanEval 协议 |
| P2 | 多 token、别名、cutoff、术语与图示 | A/B/C | 大部分可通过实现说明解决 | 碰撞/错误标签审计及受影响比例 |

对于统计，五次生成嵌套于 prompt，四个编辑模型又共享 unseen 集，不能把所有记录当作独立样本。建议按 prompt 聚类，报告折间结果，并明确区间覆盖的是哪些随机性。若 Base 直接复用筛选时的五次生成，另需解释筛选与评测共用样本的影响，最好对固定测试集重新独立采样基模。

## 7. 本地实现与数据核实出的回应要点

### 7.1 定位是首 token 代理，训练中的负向目标使用完整包名

`bound/bound.py` 的 `localize_package_boundary` 对每个包执行 `tokenizer(" " + pkg, add_special_tokens=False).input_ids[:1]`，在 good/bad 各自集合内去重，未显式消除两个集合间的相同 token。多个包因此可能不可区分；两侧集合的 log-sum-exp 及 anchor 权重也意味着共享项不能笼统称为自动完全抵消。

相对地，`continuation_unlikelihood` 对完整 bad_text 的 token 计算平均 log probability 后取指数，属于长度归一化的序列分数。答复应分开描述 localization 和 editing；不能说风险定位已经逐 token 处理完整包名。定位取 assistant 开头的 next-token logits，未像负向训练那样追加 `[ANSWER]\n` 后再计分，这也值得核查代理信号的适切性。

### 7.2 ast.parse 不等于语法质量已经评估

`cross_task.py:extract_import_modules` 尝试 AST；异常后继续文本扫描。当前流程不输出专门的 syntax_valid 指标，也不因为语法失败拒绝计入包指标。可以如实说代码中存在解析步骤，同时承认论文没有建立语法/执行质量证据。

保留 cross-task 文件含 `code_generation_raw`、`code_block`、`import_modules` 和 mapper 输出，因此对 BOUND 的既有输出补做语法与映射审计是可行的。当前本地 retained results 主要是 BOUND，未见对应 Base 跨任务完整输出及所有 baseline 的原始文件；若要做前后比较，需要补齐它们。

B 提到的 `packages_distributions()` 不宜在未建立对应环境/元数据覆盖范围时当成全部未知 import 的完整 oracle；可采用元数据支持的映射加人工审核，对未知或多义映射单独记录。本次未实现或验证替代映射流程。

### 7.3 源包真值目前没有直接字段

遍历三模型 `high_risk_prompts.jsonl`，字段均为 `dataset / hallucinated / hallucination_prob / id / language / num_generations / question / trials / valid`。保留 ID 提供了追溯机会，但没有上游源包映射文件可直接使用。不能把 valid/valid_reference 当作独立 ground truth；它来自基模自身输出的存在性筛选。

### 7.4 本地材料支持补分析，但不支持声称所有基线已复现

BOUND 的 edit/unseen 结果汇总按四折平均与论文主表中的 BOUND 行一致。这里核对的是已保存 summary 的算术平均，没有运行模型，也未独立重做包抽取和注册表标注。`compute_result.py` 主要读取已有 summary 字段组织表格，本身不是从生成文本重新标注的完整验证。

## 8. 提交 rebuttal 前应内部核对的额外问题

以下不是审稿人的原话，也不能在未追溯实验版本前认定是论文结果错误。

**(1) top-5 与配置的关系。** 三份模型配置中设置 `localization_top_k: 5`，但同时采用 `localization_mode: window_family`、`localization_window: 1`。选择函数以 top-5 的层及投影类型为中心，扩展邻近层的同类模块，最终可能超过五个。论文写成只编辑 top-5，需要核对投稿实验对应配置、最终模块列表、实际参数量及 731 KB 的统计依据。

**(2) 保存的 Base 与论文数值存在小差异。** 例如 DeepSeekCoder unseen，论文 Sample-HR/Package-HR 为 0.8333/0.4414，保留 evaluation summary 为约 0.82884/0.43703。Qwen3、Llama-3.1 也有小差别。原因可能涉及评测版本、抽取规则、数据处理或独立采样，但目前未确定。应先确定权威实验记录，再使用精确相对降幅及 CI。

**(3) cutoff 的含义与错误分类。** 实现采用固定日期，函数注释写 release/cutoff date，正文写 knowledge cutoff，需核对每个日期的来源和语义。现行判断将截止日期后才有 release 的包也计为 hallucinated，必须与“评测时仍不存在”区分。代码还将查询失败、无可用 release 元数据和不满足日期条件汇入同一错误类别，需要审计这些类别是否影响结果。

**(4) 包名规范化边界。** `normalize` 对含点但不含连字符/下划线的名字先截到首段；它不等同于对所有 distribution 名只做连字符规范化。结合 namespace、import/distribution 差异，应以具体样本核查误标。未核实前不要承诺已经完备支持别名和 namespace。

**(5) “不牺牲有效包生成”应避免绝对化。** 论文主表中 Qwen3 unseen Valid-Rate 从 0.7990 降至 0.7434，下降 5.56 个百分点；某些折下降更明显。跨模型平均改善并不能证明每个模型都保持无损，也不能证明语义适用性无损。

## 9. 面向 rebuttal 的工作建议

1. 先固定投稿实验对应版本、Base 参考记录、定位模块列表和注册表日期定义，避免新补材料与原稿口径不一致。
2. 优先补推荐适用性证据：对原始/编辑输出做盲化的任务相关性审核；若恢复源包对应关系，再补源包命中，清楚允许合理替代。报告是否更集中推荐常见通用包、空输出及不必要依赖。
3. 补工具验证对照：至少比较 Base、BOUND、Base+verifier、BOUND+verifier，在同一任务与标注口径下报告有效完成情况及推理/查询成本。简单过滤达到低存在性错误并不自动等于完成任务，仍需看过滤后是否留下有用结果。
4. 利用已有跨任务输出补语法统计和映射抽查，提供 prompt 模板；补齐 Base 输出后再评估编辑前后变化。语法通过只回答最低层次问题，不能替代 API 与端到端运行验证。
5. 根据时间与算力补最关键的普通 LoRA/同损失定位对照、未筛选 prompt 集和统计区间。更多相近规模模型的优先级低于解决现有指标与基线缺口。
6. 最后处理表述：把 boundary 定位为操作性建模概念，精确说明创新落点；完善 HumanEval 协议；修改图示、术语及生态范围。真实项目研究、更强模型和完整 agent 实验的范围应由 rebuttal 时间预算决定，不能靠未来工作承诺代替最核心证据。

不建议的回应方式：仅说适用性 out of scope；仅凭没有联网就宣称全面胜过 verifier；仅引用四折平均就声称统计显著；将 DINM 整体基线视为已隔离验证定位策略；将 unseen 提升或随机模块消融视为内部边界存在的证明；将当前代码包含 AST 解析说成论文已验证代码正确性。

## 10. 本地来源索引

- `reviewer意见/reviewer意见.md`：三份完整意见及 10 个明确提问。
- `paper/Package_Hallucination_icse (2).pdf`：12 页投稿版，Figure 1 位于第 2 页。
- `paper/Package_Hallucination_icse/catalogue/approach.tex`：风险评分、定位与三种损失。
- `paper/Package_Hallucination_icse/catalogue/experimentalsetup.tex`：数据筛选、指标、基线、生成和编辑设置。
- `paper/Package_Hallucination_icse/catalogue/results.tex`：RQ1–RQ3 与主表。
- `paper/Package_Hallucination_icse/catalogue/discussion.tex`：成本、HumanEval、有效性威胁。
- `replication package/BOUND/bound/bound.py`：包抽取/标注、定位、LoRA、损失与评测。
- `replication package/BOUND/bound/cross_task.py`：三任务中的跨任务模板、AST/文本抽取、基模映射。
- `replication package/BOUND/bound/hparams/*.yaml`：本地当前运行配置。
- `replication package/BOUND/data/package_hallucination/`：高风险、编辑、unseen 与跨任务输入。
- `replication package/BOUND/results/paper/`：保留的 BOUND 结果及生成记录。
- `replication package/BOUND/results/compute_result.py`：保存的 summary 到表格的汇总脚本。
