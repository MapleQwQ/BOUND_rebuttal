# E9——实验过程记录

本文件按时间顺序追加，记录 harness、环境、run 选择、统计脚本和结果版本。

## 2026-09-23

- E0 确认论文 HumanEval 表使用 3 个 Base rows 和每模型四折各一个选定 BOUND run，共 15 个 summary。
- 发现保存目录还包含更多 repeats，论文选择规则需要单独说明并做敏感性分析。
- 明确不能用“变化在 ±2%”直接证明等价，需预注册 practical-equivalence margin。

## 下一步

- 恢复并冻结完整 harness/config/environment。
- 汇总所有 repeats 与论文选定 runs。
- 确定区间和 equivalence 判断规则后复算。

