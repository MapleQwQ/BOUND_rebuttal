# E3 确认性样本量冻结

- 冻结配置：200个共同 prompts × 3模型 ×（Base+4个BOUND folds）× 5次生成，共15,000次生成。
- 200是设计中在算力受限情况下预先允许的200–300区间下界；三模型、四折与五次生成均完整保留。
- preliminary small100 的效果方向已经被查看，因此不能声称本样本量由盲态功效分析选出；选择200只依据事先范围和可用GPU预算。
- 停止条件是每个条件恰好200 prompts且每prompt恰好5次生成。不得根据显著性、区间或模型方向继续扩样。
- 仅允许恢复同一 prompt/condition 的基础设施失败；不替换产生空回答、幻觉或不利结果的任务。
- common-random-number global seed 固定为 `20260926`，实际 generation seed 由脚本基于 `(global_seed,prompt_id,generation_id)` 稳定派生。
