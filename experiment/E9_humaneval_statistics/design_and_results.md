# E9——HumanEval 协议与统计复核

## 实验目标

核实论文 HumanEval 数字来自一致、可追溯的协议，并用正确的不确定性与 practical-equivalence 口径描述编辑前后的能力变化。

## 设计

- 冻结 benchmark 版本、evaluation harness、Python/runtime、decoding、samples/task、pass@k estimator、timeout 和 sandbox。
- Base 与四折 BOUND 分开报告 run-level 值、选取规则、均值和区间。
- 对论文采用“一模型一个 Base run、每 fold 一个选定 BOUND run”的规则进行敏感性分析，并与全部保存 repeats 的结果对比。
- 在查看差异前冻结 practical-equivalence margin；`p>0.05` 或变化在 ±2% 内不能自动解释为等价。
- 区间应区分 generation/run 随机性与固定 adapter 条件；不能外推到重新训练 seed 稳定性。

## 输出

- `results/protocol.md`
- `results/run_level_results.csv`
- `results/selection_sensitivity.csv`
- `results/confidence_intervals.json`
- `results/summary.md`

## 实验结果

状态：多次 Base/BOUND summary 已保留；E0 已追溯论文选定的 15 个 summary，但协议说明、全部 repeats 敏感性和 equivalence margin 尚未完成。

