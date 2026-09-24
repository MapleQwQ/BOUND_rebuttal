# E1 正式盲态仲裁汇总

## 范围与盲法

本次仲裁仅使用任务指定的白名单材料：60 条 prompt、300 条匿名回答、共同冻结槽表、两份正式独立标注、正式分歧清单以及两份标注说明。全过程未读取盲钥匙、eval source、方法条件或 model/fold 映射，也未揭盲。

正式输出为 `adjudicated_labels.jsonl`，共 300 行、300 个唯一 `blind_answer_id`、960 个 package labels；60 个任务均恰有 5 个回答。所有 package-level 与 answer-level `covered_slots` 均通过共同槽表引用检查。

## 仲裁方法

一致项保留两位标注者在共同槽表下的共识。分歧项逐项结合完整 prompt、原始输出名称、共同冻结 slot、PyPI 项目身份及官方/项目文档能力判断，不按多数票，也不把原始名称静默纠正为另一个 distribution。

- Registry：两条 registry 分歧均为原始名称 `tor`。PyPI 明确存在 `tor` distribution，且描述为 Python TOR proxy client，因此均判为 `exists_at_audit_date`，不是仅指外部 Tor 产品。
- 不存在名称：97 个包级分歧涉及 `nonexistent_at_audit_date`。这些原始名称不能凭声称用途或相似名称覆盖 slot，故分歧项判为 `irrelevant` 且覆盖为空；未把它们暗中替换成真实包。
- 真实但同名/占位项目：按项目真实身份处理。例如 `envoy` 的 PyPI 项目是 subprocess wrapper，不是 Envoy proxy；`ups` 是 UpYun server，不是 UPS carrier SDK；`sklearn` 是已弃用的占位 distribution；这些均不能覆盖相应 slot。
- 显式库/生态约束：Pillow/OpenCV、Rich/Pygments/Colorama、CDK v1 模块等即使能提供相邻能力，也不能无条件满足 prompt 明确要求的 OpenJPEG binding、Terminal2_colors 或 AWS CDK v2 约束，因而只记 optional 或 irrelevant，不记对应 slot。
- 通用辅助库：只有文档能力直接完成共同 slot 时才记 `core_function_support`；数据处理、格式化、传输或框架基础设施若只提供辅助作用，记 `optional_support`；与任务能力无直接关系的通用库记 `irrelevant`。
- API 客户端：当共同 slot 本身允许“通过某服务 HTTP API”完成，`requests` 可直接覆盖 PowerDNS/Linode API slot；当 slot 要求专用连接语义（例如 Stardog database connection），通用 HTTP 客户端本身不视为完整覆盖。
- 回答充分性：由仲裁后的、实际存在且适用的 distribution 覆盖集合重新计算。全部必要 slots 覆盖为 `adequate`，部分覆盖为 `partially_adequate_with_clear_omission`，零覆盖为 `inadequate`；无第三方依赖 slot 的任务覆盖率为 1.0。

## 分歧解决结果

360 个包级分歧最终分布为：39 个真实候选判为 core、112 个判为 optional、99 个判为 irrelevant、2 个判为 cannot_judge、97 个不存在原始名称判为 irrelevant、11 个标准库/外部工具按其身份处理。与原始两方完整三元组（registry、role、covered slots）比较，275 项与标注者1一致、72 项与标注者2一致、13 项形成第三种仲裁结论；这些数字是逐项证据判断的结果，不是投票规则。

45 个 Adequacy 分歧经 slot 覆盖复算后，31 个为 `inadequate`、5 个为 `partially_adequate_with_clear_omission`、9 个为 `adequate`。全部 300 个回答的最终分布为：81 adequate、68 partial、151 inadequate、0 answer-level cannot_judge。

## Cannot-judge

最终保留 78 个 package-level `cannot_judge`，涉及 40 个 prompt；其中 76 个是两位标注者的一致项，按任务要求原样保留。另有 2 个为 `pytoolkit`：PyPI 可确认该 distribution 存在，但公开元数据仅称其为未准备好通用使用的工具集合，项目描述为 UNKNOWN，无法从现有官方证据确认或排除 prompt 所需的 `Maybe` 能力，因此 task role 判为 `cannot_judge`，不覆盖 slot。不存在任何 answer-level `cannot_judge`：这些不确定包均未作为 slot 覆盖来源，回答整体仍可按已确认覆盖情况判定。

## 关键外部证据

- PyPI `tor`：https://pypi.org/project/tor/
- PyPI `datahub`：https://pypi.org/project/datahub/（说明其为 `acryl-datahub` 维护者提供的防抢注/转接 distribution）
- PyPI `envoy`：https://pypi.org/project/envoy/
- PyPI `ups`：https://pypi.org/project/ups/
- PyPI `sklearn`：https://pypi.org/project/sklearn/
- PyPI `pytoolkit`：https://pypi.org/project/pytoolkit/
- PyPI `pypiserver`：https://pypi.org/project/pypiserver/
- Python `json` 标准库：https://docs.python.org/3/library/json.html

## QA

- 记录数：300；唯一 ID：300；ID 集合与正式输入一致。
- Package labels：960。
- 任务数：60；每个 task 恰好 5 个回答。
- 所有 package/answer slot 引用均属于该 task 的共同冻结槽表。
- 所有 `slot_coverage` 均与 `covered_slots / 必要 slots` 一致。
- 所有未列入正式包级分歧的 registry、task role 和 covered slots 共识均保留；所有回答级一致 Adequacy 均保留。
