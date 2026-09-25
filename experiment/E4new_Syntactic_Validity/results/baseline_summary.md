# E4new：全部 RQ2 方法的代码语法有效性

本补充将 ROME、MEMIT、DINM、Full-FT 的三模型×四折逐条输出纳入与 Base/BOUND **相同的代码提取、`no_code`、`ast.parse`、`compile` 和完整分母规则**。**BOUND 的唯一统计输入始终是 `BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization/` 下的12份原始输出；没有用历史 RQ2 的 BOUND 文件替换它。**其他四种 baseline 从 `knowledgeEdit/results/rq2_cross_task_20260611/` 读取，Base 也来自该历史目录，因为投稿 replication package 未保留 Base 逐条生成。新增 48 个条件，每条件 100 prompts×5 generations，共 24,000 条；连同此前 Base 1,500 条和 BOUND 6,000 条，共审计 31,500 条纳入统计的生成记录。每个 baseline 条件的 500 个 ID 和题目文本均与该模型 Base 对齐。Python 版本为 3.10.20。Base按当前每模型四折最低Syntax-Valid Rate选取A/C/A；这是事后最差折敏感性口径，Qwen3 C折文件在两次审计间发生变化，来源风险见[Base重审报告](base_reaudit.md)。

## Syntax-Valid Rate：全部 generation 分母

| 方法 | DeepSeekCoder | Qwen3 | Llama-3.1 | 三模型等权 |
| --- | ---: | ---: | ---: | ---: |
| Base（当前最差折：A/C/A） | 91.00% | 84.20% | 91.40% | 88.87% |
| BOUND | 93.70% | 78.90% | 91.75% | 88.12% |
| ROME | 23.10% | 21.55% | 0.00% | 14.88% |
| MEMIT | 90.25% | 85.80% | 91.60% | 89.22% |
| DINM | 85.75% | 74.35% | 1.40% | 53.83% |
| Full-FT | 95.65% | 27.95% | 0.00% | 41.20% |

Base 每模型 500 条只计一次；其他方法为四折等权平均，每折 500 条。Syntax-Valid 包含 AST 通过但 `compile` 失败的极少数记录，故不等于 Compile-Valid。全部方法采用相同的原始 RQ2 unseen prompt 与五次生成设置；此表不是功能正确率。

### 四折明细

| 模型 | 方法 | A | B | C | D |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | ROME | 0.00% | 0.00% | 0.00% | 92.40% |
| DeepSeekCoder | MEMIT | 91.20% | 89.80% | 89.20% | 90.80% |
| DeepSeekCoder | DINM | 83.80% | 88.40% | 87.20% | 83.60% |
| DeepSeekCoder | Full-FT | 96.80% | 94.60% | 94.80% | 96.40% |
| Qwen3 | ROME | 0.00% | 86.20% | 0.00% | 0.00% |
| Qwen3 | MEMIT | 86.20% | 85.20% | 85.80% | 86.00% |
| Qwen3 | DINM | 80.20% | 55.20% | 81.00% | 81.00% |
| Qwen3 | Full-FT | 34.20% | 12.00% | 26.40% | 39.20% |
| Llama-3.1 | ROME | 0.00% | 0.00% | 0.00% | 0.00% |
| Llama-3.1 | MEMIT | 92.20% | 91.60% | 91.20% | 91.40% |
| Llama-3.1 | DINM | 2.40% | 0.80% | 2.20% | 0.20% |
| Llama-3.1 | Full-FT | 0.00% | 0.00% | 0.00% | 0.00% |

## No-Code 与其他诊断

| 模型 | 方法 | No-Code | Parse-Failure | Compile-Failure | AST-valid 且有非标准库 import 候选 |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | ROME | 75.10% | 1.80% | 0.10% | 21.20% |
| DeepSeekCoder | MEMIT | 2.00% | 7.75% | 0.20% | 84.60% |
| DeepSeekCoder | DINM | 10.15% | 4.10% | 0.20% | 80.35% |
| DeepSeekCoder | Full-FT | 0.35% | 4.00% | 0.25% | 90.75% |
| Qwen3 | ROME | 77.25% | 1.20% | 0.00% | 20.70% |
| Qwen3 | MEMIT | 10.40% | 3.80% | 0.00% | 82.55% |
| Qwen3 | DINM | 19.85% | 5.80% | 0.05% | 72.40% |
| Qwen3 | Full-FT | 60.35% | 11.70% | 0.05% | 27.55% |
| Llama-3.1 | ROME | 68.60% | 31.40% | 0.00% | 0.00% |
| Llama-3.1 | MEMIT | 0.00% | 8.40% | 0.15% | 82.75% |
| Llama-3.1 | DINM | 79.85% | 18.75% | 0.00% | 0.45% |
| Llama-3.1 | Full-FT | 99.85% | 0.15% | 0.00% | 0.00% |

这些比例都以**全部生成**为分母。对退化成乱码的输出，`no_code` 与 `parse_failure` 的细分受“是否出现类似 Python 代码行”的启发式规则影响，尤其是 Llama-3.1 的 ROME/DINM；无论落在哪个失败子类，这些输出均不进入 Syntax-Valid 分子。Qwen3 Full-FT 的 `no_code` 很多是 `None`；Llama-3.1 Full-FT 几乎所有输出都没有可识别的 Python 程序。抽样查看的 Llama-3.1 DINM 少数语法通过输出仍是重复/无意义文本；**语法通过不是代码有用或可运行的证据**。

## 与 Base 的配对区间

每模型按 prompt 成组重采样 Base 五次生成和该方法四折各五次生成，10,000 次、seed `20260924`。三模型等权 Syntax-Valid 差值的 95% 区间如下（百分点）：

| 方法 | 方法−Base 差值 | 95% prompt-bootstrap CI |
| --- | ---: | ---: |
| BOUND | −0.75 | [−2.57, +1.12] |
| ROME | −73.98 | [−76.25, −71.58] |
| MEMIT | +0.35 | [−1.15, +1.83] |
| DINM | −35.03 | [−37.20, −32.73] |
| Full-FT | −47.67 | [−50.32, −44.85] |

区间只反映固定模型与输出下的 prompt 组成，不覆盖模型编辑/训练 seed、不同 folds 的重新训练或新生成。方法之间也不应只凭语法率排序：Full-FT 在 DeepSeekCoder 的 Syntax-Valid 为 95.65%，但这不能说明依赖正确或任务成功；部分方法的低值则反映大量无代码/乱码输出。

新增逐条记录为 `baseline_per_generation.csv`；输入 SHA-256 与 Python 版本为 `baseline_input_manifest.json`；全部逐折值、其他指标和 CI 为 `baseline_syntax_summary.json`。原 Base/BOUND 的数据和方法见 [主报告](summary.md)。从仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/shuhanliu/miniconda3/envs/EasyEdit/bin/python BOUND_rebuttal/experiment/E4new_Syntactic_Validity/script/run_baseline_syntax_audit.py
```

投稿 RQ2 TeX 与某些后续归档的汇总值存在 E0 记录的版本差异；本次语法审计使用保留的逐条生成文本，并已确认 BOUND 逐条文本在投稿快照与历史 RQ2 归档之间一致。
