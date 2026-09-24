# E1 共同 Requirement Slots 下的正式双标一致性

> 本报告是在方法条件仍盲化、正式仲裁尚未进行时生成。两名标注者均按共同冻结的 60 个任务、105 个 requirement slots 映射回答；原始独立 slots 一致率保留为敏感性分析。

## 对齐检查

- 两侧回答：300 / 300；共同回答：300。
- 共同候选：960；候选集合不一致的回答：0。
- 未读取方法盲化映射，未修改两份原始标签。

## 主一致率

| 层级/标签 | N | exact agreement | Cohen's κ |
|---|---:|---:|---:|
| 回答 Adequacy | 300 | 85.00% | 0.7671 |
| 候选 registry_status | 960 | 99.79% | 0.9939 |
| 候选 task_role | 960 | 64.90% | 0.5227 |
| 候选 covered/not-covered | 960 | 88.85% | 0.7386 |
| 候选 covered slot 集合 | 960 | 86.67% | 0.7428 |
| 回答 covered slot 集合 | 300 | 81.67% | 0.7618 |

回答级数值 slot coverage 在 295 条可比回答上的精确一致率为 81.36%，平均绝对差为 0.1359。

## 分歧规模

- Adequacy 分歧回答：45/300。
- Coverage 分歧回答：60/300。
- 任一报告字段存在分歧的回答：170/300。
- 详细分歧共 420 条记录，保存于 `formal_common_slot_disagreements.jsonl`。

## 未知标签

- 回答级 `cannot_judge`：A1=0/300，A2=0/300。
- 候选级 `task_role=cannot_judge`：A1=76/960，A2=173/960。

## 解释边界

- 这里报告的是仲裁前独立判断的一致性，不是仲裁后结果。
- `formal_interannotator_agreement.json/.md` 使用各自独立拆分的 slots，应作为 slot 粒度敏感性结果保留，不覆盖本报告。
- 本报告没有实验条件字段，不能据此比较 Base 与 BOUND。
