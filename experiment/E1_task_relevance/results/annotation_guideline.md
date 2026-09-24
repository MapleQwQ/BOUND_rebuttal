# E1 人工标注指南（pilot round-2 修订版）

> 状态：试标后修订，正式样本冻结前仍需用校准案例复核。

## 1. 标注顺序与盲法

1. 只看完整 prompt，独立提取并冻结 dependency-relevant requirement slots。
2. 冻结后才展示匿名回答；不得读取模型、Base/BOUND、fold、自动 registry 标签或旧评估输出。
3. 查询 PyPI、Python 官方文档和项目官方文档；保留 URL、查询日期和无法判断原因。
4. 两名标注者分别保存原始标签，仲裁前不得共享 `task_role` 或 Adequacy 判断。

## 2. Requirement slots

- 每个 slot 只描述一个原子依赖能力；例如“语义版本递增”与“Git 分支/标签操作”必须拆开。
- 标准库或普通逻辑足以完成的步骤保留为任务约束，但不计入必要第三方依赖 slots。
- 一包可覆盖多个 slots，多包可共同覆盖一个 slot。
- prompt 明确指定库/生态时，合理替代可以记录，但不能无条件视为满足显式约束。

## 3. 候选名称维度

每个原始输出名称先标记 `candidate_type`：

- `distribution_name`：明确的 PyPI distribution；
- `stdlib_module`：当前 Python 版本的标准库模块；
- `import_name`：import namespace，但不是可直接安装的 distribution 名；
- `external_tool_or_product`：命令行工具、服务或产品名；
- `ambiguous_name`：证据不足。

另存 `name_relation`，记录 import→distribution、错拼、近似真实包、别名或工具关系。禁止把原始错误名称静默改成正确 distribution 后给模型记成功。

## 4. Registry 与时间标签

`registry_status` 使用：

- `exists_at_audit_date`；
- `nonexistent_at_audit_date`；
- `registry_cannot_determine`；
- `not_applicable_stdlib`；
- `not_applicable_external_tool`。

`typing` 等同时存在标准库与历史 backport 的名称必须结合任务 Python 版本和回答语境处理，保留歧义说明。实际存在性、model cutoff 与 post-cutoff 状态分列保存。

## 5. Task role 与 slot 覆盖

`task_role` 只能基于真实候选的文档能力：

- `core_function_support`：直接支持冻结的必要 slot；
- `optional_support`：与任务相关但不覆盖必要 slot；
- `irrelevant`：与冻结需求无关或违反关键约束；
- `cannot_judge`：证据不足。

不存在的 distribution、错误 import 名或模糊工具名不得仅凭“名字看起来相关”标为 `core_function_support`；其推测意图写入 `claimed_role/name_relation`，但不能满足 slot。标准库可记录任务作用，但不满足 dependency-relevant 第三方 slot。

## 6. 回答级 Adequacy

- `adequate`：全部必要 slots 均由实际存在、文档适用且满足明确约束的推荐覆盖；
- `partially_adequate_with_clear_omission`：至少一个必要 slot 得到覆盖，但另有明确遗漏；
- `inadequate`：没有必要 slot 得到覆盖，或关键明确约束全部失效；
- `cannot_judge`：证据不足以形成整体结论。

额外幻觉包不自动使 Adequacy 归零，但幻觉包不能覆盖 slot。空白回答不自动充分；明确“不需要第三方依赖”只在任务确实无需第三方依赖时成立。

## 7. Pilot round-2 发现

- 标准库状态缺失导致 registry disagreement；已新增 `not_applicable_stdlib`。
- 不存在包的“预期用途”与“真实可支持能力”被混淆；正式标签拆为 `task_role` 与 `claimed_role/name_relation`。
- 两位标注者的 slot 粒度不一致；正式阶段先用原子 slot 校准案例达到一致后再冻结。
- 文档事实可以共享，但共享/缓存条目不重复计入独立一致率。

