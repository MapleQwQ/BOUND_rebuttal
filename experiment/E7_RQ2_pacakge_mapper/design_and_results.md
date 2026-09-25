# E7：RQ2 Import→Distribution 映射审计

## 目标与范围

独立审计 RQ2 原 LLM mapper，并用经核验的映射重算 Base、BOUND、ROME、MEMIT、DINM、Full-FT 的代码任务 Sample-HR、Package-HR、Valid-Rate。分析对象为归档的全部 31,500 条**唯一**代码生成回答；Base 的 B/C/D 为历史复制或变体，不重复计入主分母。各模型的 BOUND 和其他编辑基线保留四折。

## 方法（执行前冻结）

1. 从保存的代码回答提取代码块，以 Python 3.10 `ast` 提取完整 import 路径及顶层名称；记录无代码、解析失败、相对导入、标准库与可明确判定的本地模块，不把不可解析回答静默从回答分母删除。原论文 mapper 只看顶层名称，故同时保留原始 mapper 输入以进行公平比较。
2. 第三方 import 以本地 distribution metadata、PyPI 项目/文件 metadata、官方安装和导入文档交叉核对。`packages_distributions()` 仅代表当前可发现安装环境，查询不到不能判定不存在；namespace、同名多 provider、缺乏可靠证据者保留歧义/未知，并留下证据 URL 与核验记录。不能仅凭 import 与项目名称相同、或原 LLM 的输出，认定映射正确。
3. 对原 mapper 报告按不同 import 键计算的 unique-mapping accuracy、按实际回答中出现次数加权的 occurrence-weighted accuracy，以及最终 valid/hallucinated 标签一致率。映射准确率的已核验分母、未知率、保守/宽松界限同时报告，不能只报告成功映射子集。
4. 使用与原实验相同的模型 cutoff 和包存在性规则复算三项 RQ2 指标；每个回答内分发包去重，Sample-HR 和 Valid-Rate 的分母为全部回答，并额外报告未知包/无代码/解析失败回答。四折先分别算指标，再取四折均值；Base 只计一次。若歧义无法消解，Sample-HR/Valid-Rate 给出范围；Package-HR 的未知分发包数也不确定，只能报告明确假设下的情景，不能把情景叫严格界限。
5. 主比较仅针对当前留存归档，不将其称为与已投稿表格逐项完全一致；E0 已记录投稿表格与归档之间的差异。

## 当前结果与边界（2026-09-25）

**已经确认原 LLM mapper 能制造错误幻觉标签，但目前不能证明“移除 mapper 后 RQ2 结论仍成立”。**严格 AST 成功、独立映射可判的子集中，原 mapper 对单一顶层第三方 import 的 unique-mapping accuracy 为 **80.51%**（106 种名称），occurrence-weighted accuracy 为 **64.90%**（3,744 条回答）。这不是全量准确率：总共 31,500 条回答；虽然 9,510 条不能整段 AST 解析，现已对其使用容错提取，但仍有 3,062 种未解决导入路径影响 8,906 条回答。后续仍需人工核验高频待决项并重新冻结全量点估计；当前表格是中期敏感性结果。

### 数据完整性与证据

输入为 3 模型 ×〔Base 500 条唯一回答 + BOUND、ROME、MEMIT、DINM、Full-FT 各 4 折 × 500 条〕，共 31,500 条。Base 的历史 B/C/D 为复制或变体，不重复入主分母。输入 SHA-256、AST 结果和逐回答记录分别见 [`results/inventory_summary.json`](results/inventory_summary.json)、[`results/ast_import_occurrences.csv`](results/ast_import_occurrences.csv)、[`results/generations.csv`](results/generations.csv)。当前留存归档与已投稿 RQ2 表存在 E0 所记录的差异，不能称为已逐项复现投稿表。

Python 3.10 整段 AST 成功 21,990 条，失败 9,510 条（30.19%）；其中 ROME 失败 4,722/6,000。对失败代码改用**标准库 `tokenize` 定位完整 import 语句，再逐句 `ast.parse`**，能处理多行导入并跳过字符串/注释中的伪 import。在 21,990 条整段 AST 成功回答上，此法的去重 import 集合与整段 AST **21,990/21,990 完全一致，零漏提、零多提**；对整段失败回答从 2,108 条恢复至少一条 import。另以 [Parso 容错解析器](https://parso.readthedocs.io/en/latest/docs/usage.html)交叉检查失败回答；Parso 独有结果必须通过**原始整行**的 AST 验证，最终仅在 21 条回答发现额外可信候选，其中 2 条是旧确定性提取器也未覆盖的回答。原实验确定性提取结果只作显式标记的回退。仍有 7,400 条整段失败回答未观察到 import，其中 5,601 条因词法错误或截断而不能确定确无 import；因此不把它们默认为“无依赖成功”，并保留无代码/解析失败 guardrail。详见 [`results/tokenized_recovery_summary.json`](results/tokenized_recovery_summary.json)、[`results/parso_physical_line_validation_summary.json`](results/parso_physical_line_validation_summary.json) 与逐回答文件。`code_block` 与按归档规则从原回答重新提取的文本有 1 条差异（DeepSeekCoder/Base/A，`3063__repeat_1`），已留标志供复核。

PyPI 证据路线为：官方 [JSON API](https://docs.pypi.org/api/json/) → 发行 wheel URL → 官方 SHA-256 校验 → wheel 文件清单/`top_level.txt`；只读取文件，不执行 wheel。原 mapper 输出仅用于提出检索候选，映射裁决必须有独立证据。本机多个环境的 distribution 文件 metadata 作为补充，人工核验与来源链接在 [`script/manual_adjudications.csv`](script/manual_adjudications.csv)。661 个候选的 PyPI 查询中，309 个 wheel 可核验，250 个**同名项目**返回 404，101 个项目存在但 wheel 超限，1 个 metadata 错误；同名项目 404 不能推出 import 无分发包。[Python 文档](https://docs.python.org/3.12/library/importlib.metadata.html)及 [PyPA 文档](https://packaging.python.org/en/latest/discussions/distribution-package-vs-import-package/)明确 import/distribution 不必一一对应、namespace 可有多个提供者。

完整路径清单中，单值核实 1,439 种、仅顶层可核实 1,203 种、namespace/多提供者歧义 376 种、未知 2,831 种、本地 2 种。**仅顶层可核实不等于具体子模块/API 可导入。**CDKTF 官方示例中的 [`imports.aws`](https://developer.hashicorp.com/terraform/cdktf/release/upgrade-guide-v0-18) 属生成的本地 provider 路径；此处排除而非判幻觉。逐条来源和状态在 [`results/audited_mapping.csv`](results/audited_mapping.csv)，未解决项按频次排序在 [`results/manual_review_queue.csv`](results/manual_review_queue.csv)。

### Mapper 准确率、错误方向与标签一致率

“unique”主口径只在**严格 AST、完整可判、原 mapper 输入只有一个顶层第三方 import**的回答中计算：先对每种 import 算回答正确比例，再对 106 种等权平均；按回答中该 import 的实际出现频次汇总即 3,744 次。多 import 的逗号列表无法可靠归因给某一个输入，因此另外对完整回答的映射集合做核验。

| 指标（均为可判子集的条件性结果） | 分母 | 结果 |
| --- | ---: | ---: |
| Unique-mapping accuracy，按不同 import 等权 | 106 种 | 80.51% |
| Occurrence-weighted accuracy，单 import 回答 | 3,744 条 | 64.90% |
| 完整映射集合完全一致率，非空回答 | 8,799 条 | 63.05% |
| 原 valid/hallucinated **包集合**完全一致率，非空回答 | 8,545 条 | 62.98% |
| 回答级“有 valid / 有 hallucinated”两个二元标签均一致 | 同上 | 76.22% |

21,990 条可完整 AST 解析回答中，仅 14,014 条映射完整可判，其中 5,215 条无第三方 import。不能将上表条件性百分比冒充全量。原 mapper 错误并非单一方向：至少 **611** 条严格 AST 可判回答将 `aws_cdk` 映为 `aws-cdk`，而 [AWS 官方文档](https://docs.aws.amazon.com/cdk/v2/guide/work-with.html)给出的 Python 分发包是 `aws-cdk-lib`；这会把真实代码依赖误标为不存在。另可见漏映射 `pytest`/`PyYAML`、把 `openslide` 当作同名 distribution、以及附加没有 import 对应的包。生成代码有真实依赖，并不等于旧 mapper 报告的幻觉就是生成代码本身的幻觉。

在上述 8,545 条非空且标签可判的回答里，**1,476 条**由原“含 hallucinated 包”改为审计后“不含已核实的 hallucinated 包”，反方向 **9 条**。这是可判子集的标签翻转，不可外推为全量 Sample-HR 的变化；它表明原 mapper 主要可能**抬高**这部分回答的假阳性，而不保证这种偏差在各方法间相同。

### 全分母 RQ2 重算：尚无法给出可信最终点估计

采用原实验截止日：DeepSeekCoder `2023-10-29`、Qwen3 `2025-04-29`、Llama-3.1 `2023-12-31`，沿用原归档 PyPI 首发日期缓存；此处只复算包级 cutoff 存在性，不证明代码功能正确。对 24,244 个缓存有日期的原 mapper 输出独立核查，只有 4 次截止日标签与留存 valid 标签不一致，涉及 Llama-3.1 的 `cdk-constructs`、`chalkpy`、`dbtlog`，保留为归档版本差异待核验。

Sample-HR 下界仅计已核实的 cutoff-invalid distribution；**保守上界**把尚不确定映射或任何整段 AST 失败回答计为可能含幻觉。另报告较窄的 **tokenizer 情景上界**：仅把未定映射或 `tokenize` 自身报错、无法扫完整段文本的回答视为可能含幻觉。后一口径依赖“无 TokenError 的词法扫描足以找出 import”的操作假设，**不是严格上界**；[Python 官方文档](https://docs.python.org/3.10/library/tokenize.html)说明 `tokenize` 对语法无效代码的行为并不保证。Valid-Rate 对应保留保守上界和 tokenizer 情景上界，均以全部回答为分母。整段 AST 失败但无 import 的回答，代码不可用问题仍单列。Package-HR 的未知路径可能对应零/一/多个分发包；文件中 `one_slot_min/max` 仅是假设每未知路径贡献一个包的情景，**不是严格界限**。所有折先分别算比率再四折平均，Base 只计算一次。

| 模型 | 方法 | 归档 Sample-HR | 审计下界–保守上界 | tokenizer 情景上界 | 每折未知映射回答（平均） |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | Base | 34.2% | 1.2%–51.4% | 45.0% | 220/500 |
| DeepSeekCoder | BOUND | 32.6% | 0.5%–48.0% | 43.4% | 214/500 |
| Qwen3 | Base | 37.0% | 0.2%–51.6% | 48.0% | 237/500 |
| Qwen3 | BOUND | 33.9% | 0.0%–54.0% | 45.3% | 211/500 |
| Llama-3.1 | Base | 33.8% | 1.4%–50.4% | 44.2% | 210/500 |
| Llama-3.1 | BOUND | 30.8% | 0.7%–46.9% | 40.4% | 194/500 |

其余基线及所有方法的 Package-HR 情景和 Valid-Rate 范围见 [`results/rq2_metric_bounds_by_condition.csv`](results/rq2_metric_bounds_by_condition.csv)、逐折结果见 [`results/rq2_metric_bounds_by_fold.csv`](results/rq2_metric_bounds_by_fold.csv)。归档 ROME 的较低/零幻觉率常与大量解析失败或无有效代码同时出现；E4new 的语法审计需并列报告。

**当前判断：**原 LLM mapper 是 RQ2 的实质混杂因素；独立证据确认了具体错映射与标签翻转，但未定项过多，Base 与 BOUND/其他基线的范围广泛重叠。不能以“已核实子集”取代全量结论，更不能说移除 mapper 后主要结论已获验证。若 rebuttal 截止前无法完成高频项与 namespace 的人工裁决，应如实报告部分审计及限制，不提交偏乐观的全量点估计。

### 复现顺序

在仓库根目录运行 `script/` 下的 `build_inventory.py`、`recover_tokenized_imports.py`（两者使用 `/usr/bin/python3.10`）；Parso 从 `parser_requirements.txt` 安装在隔离目录后，运行 `parso_crosscheck.py --all-failed --timeout-seconds 0.1` 和 `filter_parso_candidates.py`；之后运行 `build_local_metadata.py`、`fetch_pypi_evidence.py --min-occurrences 5 --workers 6`（需联网）、`audit_mapping.py`、`summarize_audit.py`、`make_review_queue.py`。只对生成代码做静态文本处理；下载 wheel 受大小上限限制且不运行其内容。先前的 `recover_partial_imports.py` 及其输出保留为历史对照，不再进入主复算。
