# E5——实验过程记录

本文件按时间顺序追加，记录已有运行重分析、预算核对、新训练配置、seed、失败和结果版本。

## 2026-09-23

- 将 E5/E6 合并为统一优先级规划，但保留独立目录便于产物管理。
- 将“同模块数”改为核对实际 LoRA 参数预算、projection 类型和矩阵形状。
- 将 `w/o Valid Anchor` 提升为风险分数独立贡献的首要对照。
- 明确 ordinary LoRA/SFT 同时改变损失，不能单独归因定位。
- 为 boundary 分析新增固定候选集合、长度归一化、seen/unseen hallucinated 分层和 valid score retention。
- 明确训练目标下降或表示图分离都不足以单独证明稳定几何边界。

## 下一步

- 从已有 delta/config 生成参数预算表。
- 重汇总多随机 seed 和 hard-random 结果，检查是否真正预算匹配。
- 查找或恢复 w/o Valid Anchor 运行；不存在时生成最小新增配置。
- 冻结 held-out candidate manifest 后再计算 score separation。

