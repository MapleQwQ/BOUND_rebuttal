# E1 数据源包名 Ground Truth 审计

## 审计问题

Spracklen 等人的 `LLM_LY` 数据是否提供了可用于 E1 的逐 prompt 包名 ground truth 或完整参考依赖？本项目的 `valid_reference` 是否等价于该 ground truth？

## 结论

截至 2026-09-23，公开数据和 artifact **未提供可直接使用的逐 prompt 包名或完整参考依赖 ground truth**。当前项目中的 `valid_reference` 明确来自被测模型生成结果，不能作为任务级标准答案，也不能用于计算 Reference Dependency Recall。

## 证据

### 1. 官方公开数据的字段结构

官方 GitHub 中的 `Data/Python/LLM_LY.json` 采用逐行 JSON 字符串形式，每行只有一个自然语言 coding prompt。文件中没有结构化的 prompt ID、源包名、参考依赖或 ground-truth 字段。

部分 prompt 会在自然语言中明文提到包或 import 名称，但存在三项限制：

1. 明文名称可能是 import 名而非 distribution 名；
2. prompt 中可能同时出现真实包、错误名称、别名、标准库和自然语言产品名；
3. 明文提到一个包不代表它构成完成任务所需的全部依赖。

因此，从 prompt 文本抽取的名称只能标为 `prompt_explicit_anchor`，不能自动视为完整 ground truth。

### 2. 官方说明与脚本

官方 README 将 `LLM_LY.json` 描述为基于过去一年最热门包生成的 prompts，并说明语言目录含有用于 hallucination detection 的有效包名全集。该有效包名全集只回答“名称是否存在”，不提供 prompt→正确推荐包的映射。

官方 `generate_package_names.py` 读取 prompt 文本并让模型生成推荐包列表；它没有读取源包标签，也没有把任何 prompt 级标签传到输出。

官方 `generate_code.py` 的注释提到生成 prompt 时输入可为 `package_prompts_master`。这表明生成流程中可能曾有带包信息的上游文件，但该文件没有出现在公开 GitHub 数据目录或 Zenodo artifact 文件清单中。因此不能假定 `LLM_LY` 的行号仍与某个未发布列表稳定对应。

### 3. Zenodo artifact 文件清单

官方 Zenodo 记录 `10.5281/zenodo.14676377` 仅发布一个约 9.9 GB 的 `Artifacts_Submission.zip`。本次通过 ZIP 中央目录审计确认，其中与 Python 数据相关的公开文件为：

- `Data/Python/LLM_AT.json`
- `Data/Python/LLM_LY.json`
- `Data/Python/SO_AT.json`
- `Data/Python/SO_LY.json`
- `Data/Python/pypi_package_names.csv`
- `Data/Python/false_positive_packages.csv`

文件清单中没有 prompt→源包映射、参考依赖表或 `package_prompts_master`。PyPI 包名全集仍只是 registry existence 资源。

### 4. 本项目 `valid_reference` 的派生链路

本地代码链路如下：

1. `getHallucinationPackage/extract_high_risk_prompts.py` 对每个 prompt 生成多条模型回答；
2. 从每条回答抽取包名，用 PyPI/cutoff 分类成 `valid` 与 `hallucinated`；
3. 将多次回答的 `valid` 包取并集形成 `valid_union`；
4. `getHallucinationPackage/build_edit_examples.py` 把传入的 `valid` 写为 `valid_reference`；
5. `scripts/robust_highrisk_experiment.py` 同样直接用 high-risk 记录的 `valid` 构造 `target_new` 和 `valid_reference`。

因此，`valid_reference` 的正确语义是：

> model-generated registry-valid package union

它只说明某个模型曾推荐这些名称且存在性检查通过，不说明这些包与任务相关、必要、充分或由数据集作者指定。不同模型还可能为同一 prompt 得到不同的 `valid_reference`，这进一步排除了其作为共同 ground truth 的可能性。

## 对 E1 的直接影响

- 不使用 `valid_reference` 计算 Reference Dependency Recall、Recommendation Adequacy 或“正确包召回率”。
- `valid_reference` 只可用于 Base-valid retention、输出变化和 Jaccard 等描述性分析，并在表头明确标为 model-generated。
- 对 prompt 明文包名只报告 Prompt-Explicit Anchor Hit；该指标不代表完整推荐质量。
- Reference Dependency Recall 仅在双人需求分解、可信文档核验且允许等价替代的参考依赖子集上报告。
- 如果作者提供上游映射，先验证行号/ID 对齐、版本、生成过程和“源包”语义；源包若只是 prompt 生成种子，仍只报告 Source-Package Hit，不把它升级为完整 dependency recall。

## 后续获取与验收条件

拟向原作者申请 `package_prompts_master` 或逐 prompt 源包映射。只有同时满足以下条件才标为 `official_prompt_mapping`：

1. 能与公开 `LLM_LY.json` 每条记录无歧义对齐；
2. 明确数据版本和生成时使用的包列表日期；
3. 明确字段代表“生成种子包”还是“完成任务所需依赖”；
4. 抽样人工核查不存在明显顺序错位；
5. 保存原始文件哈希和可复算对齐脚本。

若只能依据行序猜测、字符串相似度或 prompt 内包名反推，则分别标为 `unavailable` 或 `prompt_explicit_anchor`，不得写成 ground truth。

## 外部来源

- 官方仓库：https://github.com/Spracks/PackageHallucination
- 官方 `LLM_LY` 数据：https://github.com/Spracks/PackageHallucination/blob/main/Data/Python/LLM_LY.json
- 官方 Zenodo artifact：https://doi.org/10.5281/zenodo.14676377

