# E4——RQ2 代码质量与 Import→Distribution 映射审计

## 实验目标

验证 RQ2 的 Package-HR 结论不是 mapper 错误或失败样本被移出分母造成的，并补充最低限度的代码结构质量。`ast.parse` 和 `compile` 通过都不等于功能正确。

## 完整分母与输出状态

对 Base、BOUND 和主要 baselines 的每条 generation 保留以下互斥主状态及可并存细节：

- `no_code`：空字符串、只有格式标记或没有代码；
- `trivial_code`：纯注释、`pass`、`None` 等无实质实现；
- `truncated`：明显截断；
- `ast_failure`；
- `compile_failure`；
- `code_no_import`；
- `code_with_imports`。

无代码、截断、语法失败、无 imports、映射未知都保留在完整分母中，不能因为提取不到包而变成“零幻觉成功”。固定 Python 版本，先运行 `ast.parse`，再运行不执行代码的 `compile(source, ..., "exec")`。

## 映射证据模型

`importlib.metadata.packages_distributions()` 只读取当前环境可发现的 distribution metadata，不是全 PyPI 映射表。一个 import 可对应多个 distributions，editable install metadata 也可能不完整。因此本地查不到不能直接判为不存在。

每条映射记录保存：

- 完整 import path 和 top-level import；
- 候选 distribution 列表；
- evidence source：本地 metadata、项目 metadata、官方文档、维护映射表、PyPI metadata、人工核对；
- mapping status：`exact`、`ambiguous`、`namespace`、`unknown`、`not_applicable_stdlib`；
- 证据版本、URL/文件和审核者。

未知/歧义映射不默认记为 hallucinated，也不从分母静默删除；分别做保守、宽松和可判断样本敏感性分析。保留完整 dotted import path 处理 namespace。

## Mapper 审计抽样

- 同时按 unique mapping item 和实际出现频次加权抽样。
- 覆盖高频、长尾、歧义、namespace、本地 metadata 缺失和原 mapper 判 hallucinated 的项。
- 分别报告 unique-macro accuracy 与 frequency-weighted accuracy，避免只审高频或只按唯一名称平均。

## 指标

代码层：完整分母上的 AST-valid、compile-valid、有实质代码、有 imports、third-party imports、各失败状态比例。

映射层：exact accuracy、top-level coverage、ambiguous/unknown/namespace rate、原 mapper 与 hybrid mapper agreement，以及 unique-macro/frequency-weighted accuracy。

结果层：在相同完整分母下，用原 mapper 和 hybrid mapper 重算 Sample-HR/Package-HR；展示 unknown 的上下界和方法排序敏感性。

## Prompt 透明度

在结果中完整提供 package recommendation、code generation、`pip install` 和 import mapping 四个 prompt template，并标出 mapper 由哪个模型、哪个 decoding 配置执行。

## 输出

- `results/output_status_by_generation.csv`
- `results/syntax_compile_audit_by_method.csv`
- `results/mapper_annotation_sample.csv`
- `results/hybrid_import_distribution_map.json`
- `results/recomputed_rq2_metrics.json`
- `results/prompt_templates.md`
- `results/summary.md`

## 实验结果

状态：完整原始输出已确认存在；BOUND-only 初步 syntax audit 已有，但 Base 配对、compile 检查、完整分母和 mapper 双加权审计尚未完成。E0 另发现投稿 RQ2 TeX 与当前归档存在 55 个实质 cell 差异，必须先冻结采用版本。

