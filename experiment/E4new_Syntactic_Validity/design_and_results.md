# E4new：RQ2 Code-Generation 语法有效性审计

## 目标与范围

回答 Reviewer B 的语法检查问题。主比较为三个模型的 Base 与 BOUND 四折，在原 RQ2 的同一批 100 条 unseen prompts 上各检查 5 次生成。主指标 Syntax-Valid Rate 的分母固定为全部 generation；无代码、解析失败、编译失败均留在分母中。`ast.parse` 和 `compile(..., "exec")` 不执行生成代码，也不能证明运行或任务功能正确。

本文件记录数据可用性、实验规则及完整结果表格。逐条记录与机器可读汇总保存在 `results/`。

## 2026-09-24 数据可用性审计

RQ2之所以按四折存放Base，是因为结果目录和汇总表按四个编辑fold组织。Base没有fold-specific编辑；`scripts/materialize_rq2_base_folds.py`从Base fold A复制B/C/D以对齐目录，`case.json`也记录了`base_reused_from`。因此四个Base目录不代表四次独立Base生成。当前副本的少量内容差异及其对语法率的影响见[Base重审报告](results/base_reaudit.md)。

**结论：完整仓库中的现有原始输出足以完成 Base–BOUND 语法实验，无须重新生成。仅使用 `BOUND_rebuttal/replication package/BOUND` 则不够，因为投稿快照只保留 BOUND 的逐条 RQ2 输出，没有 Base 的逐条生成。**

| 来源 | 每模型条件 | 文件形态 | 已核对规模 |
| --- | --- | --- | --- |
| `BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization/{model}/BOUND/fold_{A,B,C,D}/bound/cross_task_case_grouped.jsonl` | BOUND 四折 | 每文件 100 个 case，每 case 的 `repeats` 含 5 条 | 12 文件 × 500 条 = 6,000 条 |
| `knowledgeEdit/results/rq2_cross_task_20260611/{model}/Base/fold_{A,B,C,D}/test100_case_repeat5/rq2_details.jsonl` | Base 四折归档 | 每文件 500 条逐 generation 记录 | 12 文件 × 500 条；四折并非全部逐字节相同。应用户要求，本次最差折敏感性口径按每模型最低Syntax-Valid Rate选一折，即3 × 500 = 1,500条Base记录 |

路径中的模型名映射：投稿快照 `deepseekcoder/qwen3/llama3.1` 对应历史目录 `deepseekcoder/qwen3-release/llama3.1-release`。两种来源的每条记录均有 `id`、`original_id`、`question`、`tasks.code.code_generation_raw`、`tasks.code.code_block` 和 `tasks.code.import_modules`。审计了 12 组 Base–BOUND 配对：每组 500 个唯一 generation ID，均覆盖 100 个 case × 5 次；ID 集完全一致，题目文本逐 ID 一致；原始回答和代码块字段没有缺失或空字符串。**字段非空不代表一定包含可解析的 Python 代码**，例如文字回答、`None`、只有格式标记仍须在正式审计中判为 `no_code`。

另外，投稿快照 12 个 BOUND 文件中的逐 ID `code_generation_raw` 与根目录 `replication_package/BOUND/results/paper/cross_task_generalization/.../cross_task_details.jsonl` 的 12 个对应文件全部相同（每文件 500/500）。因此使用投稿快照作为 BOUND 权威输入，从历史结果的Base归档选取最差折。不能把同prompt的四份Base归档当成2,000次独立生成。Base四折的细微差异与重审结果见[Base重审报告](results/base_reaudit.md)。

## 现有代码实际做了什么

投稿快照的 `bound/cross_task.py` 在抽取 import 时尝试 `ast.parse(scan_text)`；若抛出 `SyntaxError` 等异常，则回退到逐行文本扫描。它没有保存语法检查通过/失败状态，也没有因解析失败排除或标记该生成；未见 `compile` 或执行代码的质量指标。因此 reviewer 所说“完全没有在任何阶段调用语法解析”与实现细节不完全一致，但其核心批评成立：**论文 RQ2 没有评估生成代码的语法有效性**。

## 正式实验的冻结原则

1. 对所有 7,500 条独立原始生成统一提取 Python code，不直接把历史 `code_block` 当作无争议的真值。保留 `code_generation_raw`、历史 `code_block` 和新提取结果，审计两者不一致的样本；提前固定 fenced code、多代码块、无 fence、`[ANSWER]`、纯文本/`None`、截断回答的处理规则。
2. 将无可识别代码的 generation 标为 `no_code`；它保留在完整分母中。对识别出的代码依次运行 `ast.parse` 和 `compile(source, filename, "exec")`，不执行代码。记录 Python 解释器版本、异常类型与消息。
3. 主指标为 `# AST-valid 且非 no_code / # 全部 generations`。另报 No-Code Rate、Parse-Failure Rate、Compile-Failure Rate、Syntax-valid 且包含 third-party imports 的比例；明确各类别互斥或可重叠的定义，使其总数可核对。
4. 每模型分别报告 Base 与 BOUND A/B/C/D，再对四折等权平均。按 prompt 成组重采样 Base 和四折的全部 5 次 generation，计算 Base–BOUND 差值的 paired bootstrap CI；Base 在每个 prompt 中只出现一次，不复制四倍。
5. `third-party imports` 不能仅以“有 import”代替；先区分 Python 标准库、相对导入和第三方候选。语法有效性不蕴含包存在、可安装、可运行或任务正确。
6. 投稿 RQ2 表格与当前归档存在 55 个实质 cell 差异（见 E0 版本审计）。本实验可以作为**对当前冻结原始输出的补充审计**；在解释其与投稿表格的关系前，应先解决或披露版本来源，不能声称它直接验证了表中全部原始 RQ2 数值。

## 当前状态

`[x]` 数据充足性、统一提取、语法与编译检查、逐折汇总和 paired bootstrap 已完成。

## 实验结果

本实验在 Python 3.10.20 上审计了 **31,500 条纳入统计的生成记录**：Base 三模型各500条、BOUND 和 ROME/MEMIT/DINM/Full-FT 各三模型×四折×500条。**BOUND 只从 `BOUND_rebuttal/replication package/BOUND` 读取**；Base 和其他四种 baseline 从 `knowledgeEdit/results/rq2_cross_task_20260611` 读取。各方法使用同一模型对应的100条RQ2 unseen prompts及五次生成；每个编辑方法先对四折等权平均，再对三模型等权平均。`no_code` 等所有失败生成均留在分母中。

**Base最差折敏感性口径（事后选择）**：逐模型按四折归档的原始回答重新提取代码，选Syntax-Valid Rate最低的一折；并列时按A→D顺序选最早一折。DeepSeekCoder四折均91.00%，选A；Qwen3当前A/B/C/D依次为86.40%/85.60%/84.20%/86.40%，选C；Llama-3.1四折均91.40%，选A。四折原本由A复制生成，当前差异属于归档漂移，不能解释为四次独立实验。**这不是预先指定的主分析，而是用户指定的事后保守敏感性比较**；应与先前固定A折口径一并披露。固定A折Base三模型等权为89.60%，BOUND−Base为−1.48个百分点、95% CI [−3.28,+0.35]；本次按当前文件选折的Base为88.87%。

**来源一致性风险**：Qwen3 Base C折文件在本次重审前发生变化：先前审计的SHA-256为`fcb56d5d36cae512a0256384fd7737b74ea457ae2967ded74737e2ed581c74ca`，当前为`e5445819e719c21156b7257b0a0b9bbd8d5f0d647892bf07a200a41987e7ebcf`，文件修改时间为2026-09-24 13:49:39 UTC。相对A折，当前C折12条`code_generation_raw`不同，而这些条目的历史`code_block`仍相同；11条从AST通过变为解析失败。当前C折的84.20%及后续差值反映**现存文件**，但不能把这12处不一致解释为新的独立Base生成或未经核实的模型质量下降。用于rebuttal时，应同时给出固定A折口径，并先核实C折原始文件来源。

| Base模型 | A折 | B折 | C折 | D折 | 当前选用 |
| --- | ---: | ---: | ---: | ---: | --- |
| DeepSeekCoder | 91.00% | 91.00% | 91.00% | 91.00% | A |
| Qwen3 | 86.40% | 85.60% | 84.20% | 86.40% | C |
| Llama-3.1 | 91.40% | 91.40% | 91.40% | 91.40% | A |

上表每格均为该折AST通过数/全部500条。所选折逐条诊断见表3，四折的完整状态和SHA-256见[Base重审报告](results/base_reaudit.md)及`results/base_reaudit_summary.json`。

### 表1：全部方法的 Syntax-Valid Rate

| 方法 | DeepSeekCoder | Qwen3 | Llama-3.1 | 三模型等权 |
| --- | ---: | ---: | ---: | ---: |
| Base（当前最差折：A/C/A） | 91.00% | 84.20% | 91.40% | 88.87% |
| BOUND | 93.70% | 78.90% | 91.75% | 88.12% |
| ROME | 23.10% | 21.55% | 0.00% | 14.88% |
| MEMIT | 90.25% | 85.80% | 91.60% | 89.22% |
| DINM | 85.75% | 74.35% | 1.40% | 53.83% |
| Full-FT | 95.65% | 27.95% | 0.00% | 41.20% |

所选Base三模型分别为DeepSeekCoder 455/500（91.00%）、Qwen3 421/500（84.20%）、Llama-3.1 457/500（91.40%）；No-Code分别6、44、0条，Parse-Failure分别39、35、43条。保存的历史`code_block`直接校验则分别为90.00%、85.80%、91.00%；主口径从原始回答重新提取。详情见[Base重审报告](results/base_reaudit.md)。

Syntax-Valid Rate 定义为“有可识别代码且 `ast.parse` 成功的生成数 / 全部生成数”。AST通过但`compile`失败的少量记录仍进入 Syntax-Valid 分子，另在表3报告 Compile-Failure。语法有效不代表代码可运行、依赖正确或任务完成。

### 表2：各编辑方法四折的 Syntax-Valid Rate

| 模型 | 方法 | A | B | C | D |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | BOUND | 94.40% | 93.80% | 95.20% | 91.40% |
| DeepSeekCoder | ROME | 0.00% | 0.00% | 0.00% | 92.40% |
| DeepSeekCoder | MEMIT | 91.20% | 89.80% | 89.20% | 90.80% |
| DeepSeekCoder | DINM | 83.80% | 88.40% | 87.20% | 83.60% |
| DeepSeekCoder | Full-FT | 96.80% | 94.60% | 94.80% | 96.40% |
| Qwen3 | BOUND | 75.40% | 76.00% | 84.80% | 79.40% |
| Qwen3 | ROME | 0.00% | 86.20% | 0.00% | 0.00% |
| Qwen3 | MEMIT | 86.20% | 85.20% | 85.80% | 86.00% |
| Qwen3 | DINM | 80.20% | 55.20% | 81.00% | 81.00% |
| Qwen3 | Full-FT | 34.20% | 12.00% | 26.40% | 39.20% |
| Llama-3.1 | BOUND | 90.80% | 91.20% | 93.20% | 91.80% |
| Llama-3.1 | ROME | 0.00% | 0.00% | 0.00% | 0.00% |
| Llama-3.1 | MEMIT | 92.20% | 91.60% | 91.20% | 91.40% |
| Llama-3.1 | DINM | 2.40% | 0.80% | 2.20% | 0.20% |
| Llama-3.1 | Full-FT | 0.00% | 0.00% | 0.00% | 0.00% |

### 表3：完整分母上的失败类型与 import 候选

| 模型 | 方法 | No-Code | Parse-Failure | Compile-Failure | AST-valid 且有非标准库 import 候选 |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | Base | 1.20% | 7.80% | 0.20% | 85.60% |
| DeepSeekCoder | BOUND | 1.40% | 4.90% | 0.20% | 87.90% |
| DeepSeekCoder | ROME | 75.10% | 1.80% | 0.10% | 21.20% |
| DeepSeekCoder | MEMIT | 2.00% | 7.75% | 0.20% | 84.60% |
| DeepSeekCoder | DINM | 10.15% | 4.10% | 0.20% | 80.35% |
| DeepSeekCoder | Full-FT | 0.35% | 4.00% | 0.25% | 90.75% |
| Qwen3 | Base | 8.80% | 7.00% | 0.00% | 81.80% |
| Qwen3 | BOUND | 8.20% | 12.90% | 0.15% | 76.90% |
| Qwen3 | ROME | 77.25% | 1.20% | 0.00% | 20.70% |
| Qwen3 | MEMIT | 10.40% | 3.80% | 0.00% | 82.55% |
| Qwen3 | DINM | 19.85% | 5.80% | 0.05% | 72.40% |
| Qwen3 | Full-FT | 60.35% | 11.70% | 0.05% | 27.55% |
| Llama-3.1 | Base | 0.00% | 8.60% | 0.00% | 83.40% |
| Llama-3.1 | BOUND | 0.00% | 8.25% | 0.15% | 80.65% |
| Llama-3.1 | ROME | 68.60% | 31.40% | 0.00% | 0.00% |
| Llama-3.1 | MEMIT | 0.00% | 8.40% | 0.15% | 82.75% |
| Llama-3.1 | DINM | 79.85% | 18.75% | 0.00% | 0.45% |
| Llama-3.1 | Full-FT | 99.85% | 0.15% | 0.00% | 0.00% |

表3所有比例均以全部生成数为分母。`Compile-Failure` 是AST通过、但`compile(..., "exec")`失败的额外类别；逐条状态 `no_code`、`parse_failure`、`compile_failure`、`syntax_valid` 互斥。这里的“非标准库 import”只是 Python 3.10 标准库名单之外的顶层 import **候选**，未经distribution映射验证。乱码输出被分到 `no_code` 或 `parse_failure` 取决于是否出现类似Python代码的行，尤其影响Llama-3.1的ROME/DINM诊断子类，但均不计为语法通过。少数AST通过的乱码也可能没有任何任务价值。

### 表4：与 Base 的配对差异

按 prompt 成组重采样该 prompt 下全部五次 Base 与各方法四折生成，10,000次 bootstrap、seed `20260924`。表中为三模型等权 Syntax-Valid 差值；区间只涵盖固定输出下的 prompt 组成，**条件于上述事后选定的Base折**，不包含择折本身的不确定性。

| 方法 | 方法−Base，百分点 | 95% prompt-bootstrap CI，百分点 |
| --- | ---: | ---: |
| BOUND | −0.75 | [−2.57, +1.12] |
| ROME | −73.98 | [−76.25, −71.58] |
| MEMIT | +0.35 | [−1.15, +1.83] |
| DINM | −35.03 | [−37.20, −32.73] |
| Full-FT | −47.67 | [−50.32, −44.85] |

BOUND 的逐模型差异及95% CI分别为 DeepSeekCoder **+2.70** [+0.05,+5.60]、Qwen3 **−5.30** [−9.60,−0.90]、Llama-3.1 **+0.35** [−1.80,+2.50] 个百分点。三模型总体区间跨0，不能据此声称语法质量保持；Qwen3下降及Base C折来源风险需要在rebuttal中正面披露。

### 提取规则敏感性与复算文件

投稿提取器只识别闭合的 Markdown Python 围栏；本实验对所有方法一致恢复未闭合围栏中的代码。若直接校验当前保存的旧 `code_block`，Base→BOUND语法通过率分别为 DeepSeekCoder 90.00%→92.70%、Qwen3 85.80%→70.85%、Llama-3.1 91.00%→89.90%；恢复后的主口径见表1。DeepSeekCoder当前fold A的一个`code_block`与原始回答不一致，亦计入该敏感性差异。恢复围栏不修复代码本身，截断在完整语句边界的代码仍可能通过语法检查但不完整。

输入SHA-256、逐条状态、逐折指标与完整CI分别保存在 `results/input_manifest.json`、`results/per_generation.csv`、`results/syntax_summary.json`（Base/BOUND）和 `results/baseline_input_manifest.json`、`results/baseline_per_generation.csv`、`results/baseline_syntax_summary.json`（其他baseline）。可复算脚本为 `script/run_syntax_audit.py` 和 `script/run_baseline_syntax_audit.py`。详细解释另见 [Base/BOUND报告](results/summary.md)与[baseline报告](results/baseline_summary.md)。

现存RQ2汇总与投稿TeX表格有E0记录的版本差异；此处结果来自当前逐条生成文本，且Base C折原始文件已发生变化，不能据此默认原稿所有包名指标已复现。
