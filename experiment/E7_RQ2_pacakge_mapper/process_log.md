# E7 过程日志

## 2026-09-25 14:16 UTC：建立实验目录与初始盘点

- 按实验统一结构建立 `results/`、`script/`、本设计结果文档及本时间顺序日志。
- 核对归档：3 个模型 ×〔Base 500 条唯一回答 + BOUND/ROME/MEMIT/DINM/Full-FT 各 4 折 × 500 条〕= 31,500 条代码回答。Base 的历史复制折不作为独立回答。
- 原 `cross_task.py` 的 mapper 先将完整 import 截为顶层名称，再由未编辑 Base LLM 生成分发包名；这一步可能同时引入漏映射、错映射和多余映射。
- 原存档出现 1,652 种不同顶层 import，其中 704 种仅出现一次。直接向 PyPI 逐项人工查询不现实；后续将优先以机器可审计 metadata 建立证据，并明确留下未确认项。
- 官方文档确认 import 名与分发包名不要求一致，namespace 可由多个分发包提供；本地 `packages_distributions()` 只反映当前环境。PyPI 官方 JSON API 可取得项目和发行文件 metadata。
- 当前状态：目录已建，尚未产生准确率或重算 RQ2 结果。

## 2026-09-25 14:18 UTC：完成全量 AST 清点

- 新增并运行 `script/build_inventory.py`，只读取存档、不执行模型生成代码；产出 `results/generations.csv`、`ast_import_occurrences.csv`、`unique_import_inventory.csv` 和带 SHA-256 的 `inventory_summary.json`。
- 31,500 条回答中 21,990 条可完整 AST 解析，9,510 条解析失败；后者占 30.19%，不可当作无包成功回答。AST 记录 75,237 个 import 节点/别名出现，其中 64,174 个绝对非标准库导入、10,942 个标准库导入、121 个相对导入。完整 AST 可见 1,376 个不同顶层第三方导入名。
- 分方法解析失败数：Base 121/1,500，BOUND 767/6,000，ROME 4,722/6,000，MEMIT 473/6,000，DINM 2,875/6,000，Full-FT 552/6,000。原 mapper 在部分解析失败回答上仍输出了包名，后续需保留此差异，不能仅在 AST 成功子集重算后宣称复现原 RQ2。
- 发现保存的 `code_block` 与按归档提取器重新抽取的代码有 1 条不匹配；留待定位。下一步对解析失败回答进行明确标记的 AST 行级恢复，并建立分发包证据。

## 2026-09-25 14:21 UTC：启动独立 metadata 核验

- 以官方 PyPI JSON API 找到项目及发行文件，再读取大小受限的 wheel 内容目录、`top_level.txt` 与 SHA-256；不安装或执行任何 wheel。旧 LLM mapper 输出只作为检索候选，最终映射必须由 wheel 文件或其他独立证据确认。
- 将每个候选的 `pypi_404`、项目存在但 wheel 太大、下载/metadata 错误、wheel 可核实分开记录。PyPI 同名项目存在不自动证明它提供对应 import；无法验证时保留未知。
- 先进行 5 个候选的工具试运行：1 个 wheel 已核实，4 个项目无小于 5 MB 的最新版 wheel；流程正常，正在扩展到主要出现项。

## 2026-09-25 14:25 UTC：解析失败回答的保守恢复与 PyPI 检索进展

- 新增 `script/recover_partial_imports.py`；在 9,510 条整段 AST 解析失败的回答中，仅对能单独通过 AST 解析的单行 import 做标记恢复。2,103 条回答恢复出至少一个 import，共 103,508 个 import 节点/别名出现；其余 7,407 条不能据此认定“无 import”。单行恢复可能漏掉多行语句，且不同于整段 AST 成功结果，后续分开报告。
- 官方 PyPI 检索已覆盖重复出现较多的 import 名及原 mapper 输出候选；下载仅限 5 MB 以下 wheel，校验官方 SHA-256，解析文件列表，不安装也不执行。已核实的例子包括 `PIL`→`Pillow`、`yaml`→`PyYAML`，而 `opentelemetry` 顶层同时涉及多个分发包，不可强行单值映射。
- 此时 PyPI 批量任务仍在运行；尚未计算或报告 mapper 准确率和复算指标。

## 2026-09-25 14:38 UTC：首版映射审计与全分母敏感性计算

- 661 个机械候选已查询官方 PyPI；当前 309 个候选的 wheel 文件清单通过官方 SHA-256 核验，250 个候选的同名 PyPI 项目返回 404，101 个项目存在但 wheel 超出下载上限，1 个 metadata 错误。404 只说明该**同名项目**不存在，不能推出 import 不可由其他分发包提供。
- 同时读取本机 7 个 Python site-packages 的 distribution 文件元数据（共 280 个 distribution，仅 260 个有可用文件清单），并为 AWS CDK、OpenCV、scikit-learn、Airflow、Django、TensorFlow、Plotly、Google API Client 及 CDKTF 生成的本地 `imports.aws` 添加带官方文档链接的人工核验。未对不确定名称猜包。
- 产出 `results/audited_mapping.csv`、`per_generation_audit.csv`、`rq2_metric_bounds_by_fold.csv`、`rq2_metric_bounds_by_condition.csv`、`mapper_quality_summary.json` 和按出现次数排序的 `manual_review_queue.csv`。
- 严格 AST 成功的回答为 21,990 条；其中完整映射可判的有 14,014 条，**有第三方 import 且完整可判**的只有 8,799 条。其余不能混入“已核验准确率”分母。
- 在单一顶层第三方导入、严格 AST 且完整可判的 3,744 条回答/106 种顶层名称上，按名称等权的原 LLM mapper 准确率为 80.51%，按回答出现频次加权为 64.90%。全路径、完整可判且非空的 8,799 条回答上，原 mapper 输出集合完全一致率为 63.05%。这均是**可判子集的条件性结果**，不是全量准确率。
- 高影响错映射：至少 611 条严格 AST 可判回答把 `aws_cdk` 映射成 `aws-cdk`，而官方 AWS 文档的 Python distribution 为 `aws-cdk-lib`。另有 `openslide`→`openslide-python`、`airflow`→`apache-airflow`、`tencentcloud`→腾讯云 SDK distribution 等差异。不能根据旧 mapper 报告的幻觉直接认定生成代码也推荐了不存在包。
- 尚有 3,011 种未解决的完整导入路径，影响 8,906 条回答；加上 9,510 条整段 AST 解析失败，当前全量 Sample-HR 的保守区间较宽，尚不能判定 RQ2 的效果在独立映射后仍成立。`Package-HR` 的未知项只能给“每未知路径对应一个包”的情景范围，不能声称严格上下界。
- 独立核对归档 cutoff cache：24,244 个有日期的旧 mapper 包判定中，复算与留存 valid 标签仅 4 次不一致；涉及 Llama-3.1 的 `cdk-constructs`、`chalkpy`、`dbtlog`，需在最终稿注明归档 cache/标签可能存在历史版本差异。

## 2026-09-25 14:42 UTC：中期报告和复现检查

- 已将设计、分母、证据规则、条件性准确率、标签翻转方向和全量区间写入 `design_and_results.md`；明确当前不能声称独立映射后 RQ2 主要结论仍成立。
- 全部分折结果有 63 行（3 个 Base + 3×5×4 个编辑方法折），按模型/方法聚合结果 18 行；`per_generation_audit.csv` 保持 31,500 行。`audited_mapping.csv` 有 5,799 种完整路径，人工待审队列 3,011 种；这些不是从分母静默删除的样本。
- 所有脚本通过 Python 编译检查。独立抽查归档中的 `aws_cdk`、`PIL` 与本地 `imports.aws` 案例，其原 mapper 输出、证据支持的映射与 cutoff 标签符合预期。
- 关键限制仍在：当前 PyPI wheel 清单多为评估日最新版本，并非各模型 cutoff 当日完整索引；大 wheel、namespace、解析失败代码和无可查公开文档的长尾 import 未能完全仲裁。下一阶段优先处理高频未决项，但不能为了产生单一点估计而猜测。

## 2026-09-25 15:05 UTC：替代整段 AST 的容错 import 提取

- 本机原无 Tree-sitter/Parso。在 `/tmp/e7_rq2_parser_20260925` 隔离安装解析器，不修改项目运行环境。Tree-sitter 在 Qwen3/Base 的 Cython 风格输出 `2284__repeat_5` 上出现底层段错误，故**未用于主结果**；该失败与原因保留记录。
- 新增 `script/recover_tokenized_imports.py`：Python 3.10 标准库 `tokenize` 定位 import 语句（含括号/续行），逐句 `ast.parse` 验证；字符串与注释不会被当成 import。对全部 31,500 条运行。
- 核验：在 **21,990/21,990** 条整段 AST 成功回答上，恢复的去重 import 集合与完整 AST 完全一致，无漏提、无多提。在 9,510 条整段 AST 失败回答中，2,108 条恢复至少一个 import（先前逐行 AST 为 2,103 条）；另外 7,402 条无经确认的恢复。失败回答中有 5,894 条 tokenizer 报错，主要由于生成文本自身词法不完整；不能把无恢复项视为无 import。逐回答状态见 `results/tokenized_recovery_by_generation.csv`。
- 已把 tokenized+语句 AST 结果接入 `script/audit_mapping.py` 的失败回答分支；旧确定性 mapper 输入只作为有标志的补充，不使用 LLM mapper 输出推断缺失 import。独立映射准确率主结果仍限定于整段 AST 成功子集，不因回退而扩大其可信分母。
- Parso 作为第二个容错解析器对 9,510 条失败回答完成第一轮交叉检查，曾找到 591 个标准 tokenizer 未提取的路径，但人工检查发现错误恢复案例：无效的 `scikit-learn` 语法被切成 `import scikit`。因此**不能自动并集**。正在增加原文行边界检验并重跑；Parso-only 项只进入待审队列，不直接改动主映射指标。

## 2026-09-25 15:12 UTC：Parso 假阳性过滤及 E7 重新计算

- Parso 使用 Python 3.10 文法对 9,510 条整段 AST 失败回答进行容错解析，逐条设置 0.1 秒上限；有 28 条解析器错误/超时。原始 Parso 相对 tokenizer 多出 591 个去重导入槽，人工检视发现大量由损坏代码片段切分而成的伪 import，不能直接合并。
- 加入原始行边界和**完整物理行** AST 验证后，拒绝 5,937 个 Parso 原始 import 出现记录；仅 21 条回答仍含 tokenizer 未提取但整行 AST 可证的 import，其中仅 2 条回答超出原确定性提取器已有顶层名。`results/parso_rejected_import_artifacts.csv` 与 `parso_verified_single_line_imports.csv` 保留被拒/接受证据。
- 将 tokenized+逐句 AST、通过完整行 AST 的 Parso 导入、原确定性提取器回退按来源并集接入全量映射审计；严格 mapper accuracy 的分母不变，仍只用整段 AST 成功的回答。重新生成 `audited_mapping.csv`、逐回答记录及分折/条件 RQ2 情景表。
- 在 9,510 条整段 AST 失败回答中，联合提取/回退观察到 import 的有 2,110 条；7,400 条仍未观察到 import，其中 5,601 条 `tokenize` 报错，不能认定已完整扫描。对 Sample-HR/Valid-Rate 的未知上界只把这类未扫完文本或未定映射视为可能风险；`tokenize` 扫描完成但代码整体语法无效的回答继续作为代码质量失败单列，不因语法错误自动成为“可能包幻觉”。
- 文档表格已按最新全分母敏感性结果更新。Base 与 BOUND 的范围仍重叠很大，无法得出独立 mapper 后 RQ2 总体优劣的确定结论。

## 2026-09-25 15:20 UTC：修正“严格上界”与 tokenizer 情景的区别

- 查核 [Python 3.10 官方 `tokenize` 文档](https://docs.python.org/3.10/library/tokenize.html)：其行为只对语法有效的 Python 代码有保证；对整段 AST 无效代码，即使没有抛 `TokenError`，也不能将完整扫描当成数学上证明没有 import。因此修正上一条日志中“只把 tokenizer 报错纳入上界”的过强表述。
- 最新结果同时保存两种口径：**保守上界**仍把所有整段 AST 失败回答视为可能有漏提 import；另报仅把 tokenizer 报错/映射未知纳入的**操作性情景上界**。后者数值更窄但不是严格界限。`design_and_results.md` 已以并列表格呈现，避免错误使用情景结果。
- Parso 的容错结果只在完整原始物理行通过 AST 验证后才并入失败回答回退；原始候选里 5,937 个出现被拒绝，包括把损坏的 `scikit-learn` 语法拆成 `import scikit` 的案例。完成后的严格 AST 子集 mapper 准确率保持不变，说明不会以回退子集污染该指标。
