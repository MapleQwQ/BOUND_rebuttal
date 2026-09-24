# PackMonitor 原生约束解码 100-task 汇总

范围：DeepSeekCoder、冻结 E2 100-task manifest、greedy decoding；PackMonitor 仅应用官方 grammar 拼写的最小兼容修正。

| 比较 | 条件 | invalid answer | empty | 触发率 | 平均时延（秒） |
|---|---|---:|---:|---:|---:|
| base_vs_packmonitor | base | 0.450 | 0.020 | 0.980 | 0.603 |
|  | packmonitor | 0.040 | 0.010 | 0.990 | 0.744 |
| 配对差（约束−无约束） | invalid | -0.410 (95% CI [-0.510, -0.310]) | — | — | — |
| bound_vs_bound_packmonitor | bound | 0.290 | 0.000 | 1.000 | 0.549 |
|  | bound_packmonitor | 0.040 | 0.000 | 1.000 | 0.708 |
| 配对差（约束−无约束） | invalid | -0.250 (95% CI [-0.350, -0.160]) | — | — | — |

该表只验证安装区域语法和冻结 registry 成员约束；不把 registry-valid 解释为任务相关、可安装、API兼容或端到端成功。
