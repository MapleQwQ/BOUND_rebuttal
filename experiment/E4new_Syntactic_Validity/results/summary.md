# E4new：RQ2 代码语法有效性结果

## 结论

原 RQ2 实现曾为提取 import 调用 `ast.parse`，但解析失败会回退到文本扫描，没有记录或报告代码语法有效率。本次使用保留的原始回答，按统一规则重新提取代码并在 Python 3.10.20 上运行 `ast.parse` 和不执行代码的 `compile(..., "exec")`。

在三个模型各 100 个原 RQ2 unseen prompts、每 prompt 5 次生成、BOUND 四折的**全部生成**中，按Base四折归档中语法通过率最低的一折选取Base后，三模型等权 Syntax-Valid Rate 为 Base **88.87%**、BOUND **88.12%**，BOUND−Base 为 **−0.75 个百分点**，95% prompt-cluster paired bootstrap CI **[−2.57, +1.12] 个百分点**。该区间不能证明总体语法质量保持不变，也不能证明三模型平均有确定的下降。逐模型差异明显：DeepSeekCoder 上升，Qwen3 下降，Llama-3.1 接近不变。Qwen3 的下降和Base C折来源风险需要在 rebuttal 中正面披露。

## 数据与定义

- Base：每模型 500 条，来自根目录 `knowledgeEdit/results/rq2_cross_task_20260611/{model}/Base/fold_{A,B,C,D}/test100_case_repeat5/rq2_details.jsonl`。按当前四折中最低Syntax-Valid Rate选取，依次为DeepSeekCoder A、Qwen3 C、Llama-3.1 A；并列时取字母最早者。此为**事后最差折敏感性口径**，固定A折的原口径为89.60%。Qwen3 C折文件在两次审计间发生变化，见[Base重审报告](base_reaudit.md)；分母仍每模型只计500条一次。
- BOUND：投稿快照 `replication package/BOUND/results/paper/cross_task_generalization/{model}/BOUND/fold_{A,B,C,D}/bound/cross_task_case_grouped.jsonl`，每折 500 条，共 6,000 条。总独立记录 7,500 条。
- 主指标 `Syntax-Valid Rate = AST parse succeeds and not no_code / all generations`。`compile` 是额外检查，不执行生成代码。所有比率均用完整 generation 分母；BOUND 先逐折计算再等权平均，三模型亦等权平均。
- 代码提取：取 `[ANSWER]` 内容；优先拼接 Python 或无语言标记的 fenced blocks。最后一个 Python fence 未闭合时，取开头标记之后至回答末尾的代码。没有 Python fence 时检查回答文本；空值、`None`、纯注释/单个裸值、没有 Python 代码行的普通说明文字标为 `no_code`。此规则对 Base 与 BOUND 一致。原稿提取器的 `code_block` 保留为敏感性对照。
- “含第三方 import”在本次是**非 Python 3.10 标准库的顶层 import 候选**；本实验没有验证它们是否真的来自已安装 distribution，也没有执行 import。
- CI 用固定 seed `20260924` 的 10,000 次 prompt 成组重采样；同一 prompt 的 Base 五次与 BOUND 四折各五次一起重采样。区间只涵盖固定输出下的 prompt 组成，条件于事后选定的Base折，不涵盖择折、重新编辑模型或不同生成 seed。

## 主结果

Qwen3 Base C折原始文件在上次审计后变更，当前12条原始回答与A折不同，但对应保存的`code_block`未变；其中11条由AST通过变为失败。下表的C折Base结果只描述当前文件状态，来源核实前不宜单独作为投稿时Base生成质量的证据。文件哈希和逐条差异见[Base重审报告](base_reaudit.md)。

| 模型 | Base Syntax-Valid | BOUND A | B | C | D | BOUND 四折均值 | 差值，百分点 | 95% CI，百分点 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 91.00% | 94.40% | 93.80% | 95.20% | 91.40% | 93.70% | +2.70 | [+0.05, +5.60] |
| Qwen3 | 84.20% | 75.40% | 76.00% | 84.80% | 79.40% | 78.90% | −5.30 | [−9.60, −0.90] |
| Llama-3.1 | 91.40% | 90.80% | 91.20% | 93.20% | 91.80% | 91.75% | +0.35 | [−1.80, +2.50] |
| 三模型等权 | 88.87% | — | — | — | — | 88.12% | −0.75 | [−2.57, +1.12] |

## 完整分母上的其他指标

| 模型 | 方法 | No-Code | Parse-Failure | Compile-Failure | AST-valid 且有非标准库 import 候选 |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | Base | 1.20% | 7.80% | 0.20% | 85.60% |
| DeepSeekCoder | BOUND 四折均值 | 1.40% | 4.90% | 0.20% | 87.90% |
| Qwen3 | Base | 8.80% | 7.00% | 0.00% | 81.80% |
| Qwen3 | BOUND 四折均值 | 8.20% | 12.90% | 0.15% | 76.90% |
| Llama-3.1 | Base | 0.00% | 8.60% | 0.00% | 83.40% |
| Llama-3.1 | BOUND 四折均值 | 0.00% | 8.25% | 0.15% | 80.65% |
| 三模型等权 | Base | 3.33% | 7.80% | 0.07% | 83.60% |
| 三模型等权 | BOUND 四折均值 | 3.20% | 8.68% | 0.17% | 81.82% |

`Compile-Failure` 是已通过 AST 解析、但在 `compile` 阶段失败的额外类别。逐条共有 11 例，例如函数外的 `await`、重复关键字参数和重复形参。因此 Compile-Valid Rate 比 Syntax-Valid Rate 略低。`no_code`、`parse_failure`、`syntax_valid`、`compile_failure` 四种逐条状态互斥，合计覆盖全部 7,500 条；主 Syntax-Valid 包含 `compile_failure`。

## 提取方式敏感性

投稿时的代码块提取器只识别**闭合**的 Markdown fence。对未闭合的 ` ```python `，它会将围栏或 `[ANSWER]` 一起交给解析器。本次对 Base 和 BOUND 一律恢复 fence 后代码；与旧 `code_block` 不同的有 DeepSeekCoder 30/2,500 条、Qwen3 439/2,500 条、Llama-3.1 94/2,500 条。除未闭合围栏外，当前Qwen3 Base C折原始回答与保存字段不一致也计入其中。

若直接校验当前保存的旧 `code_block`，Base→BOUND 的 Syntax-Valid Rate 分别为 DeepSeekCoder 90.00%→92.70%、Qwen3 85.80%→70.85%、Llama-3.1 91.00%→89.90%。DeepSeekCoder fold A现有一条`code_block`与原始回答不一致，也包含在此敏感性差异中。因此提取规则尤其影响 Qwen3 的绝对数值和效应大小；两种口径都显示 Qwen3 下降。恢复围栏**不修复生成代码本身**：恢复后若代码确实截断在语句中，`ast.parse` 仍会失败；若恰好截断在完整语句边界，语法检查可能通过，但不代表程序完整。

## 回应边界

本实验直接补上 reviewer 要求的同任务代码语法检查，但不能据此声称代码可运行、API 正确、依赖可安装或满足用户任务。Qwen3 语法通过率的下降说明原 RQ2 的包名指标不能单独代表生成代码质量。现存 RQ2 输出与投稿 TeX 表格有 E0 记录的版本差异；此处为保留原始输出的补充审计，正式 rebuttal 应明确该来源。

可复算脚本：`../script/run_syntax_audit.py`。逐条结果：`per_generation.csv`。输入 SHA-256、Python 版本和 bootstrap 设置：`input_manifest.json`。完整机器汇总及所有指标 CI：`syntax_summary.json`。

从仓库根目录复算：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E4new_Syntactic_Validity/script/run_syntax_audit.py
```
