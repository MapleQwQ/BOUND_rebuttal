# E3 confirmatory200 综合结果

该集合从纠正后的未按风险筛选 eligible pool 简单随机抽取；完整排除审计见 `exclusion_audit_confirmatory200.json`。

| 模型 | Base Sample-HR | BOUND四折 | 差值 | Base Empty | BOUND Empty | historical clean prompts |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeekCoder | 0.1070 | 0.1035 | -0.0035 | 0.0560 | 0.1167 | 149 |
| Qwen3 | 0.0540 | 0.0355 | -0.0185 | 0.2300 | 0.3417 | 177 |
| Llama-3.1 | 0.1540 | 0.1685 | +0.0145 | 0.0540 | 0.0900 | 122 |
| 三模型等权macro | 0.1050 | 0.1025 | -0.0025 | 0.1133 | 0.1828 | — |

共享prompt bootstrap 95% CI：`[-0.0202, +0.0148]`；common-seed mismatch=0。
Package-HR：Base=0.0607，BOUND=0.0630。
共同snapshot未列名回答率：Base=0.0920，BOUND=0.0920；未列名不自动等于现实中从未存在。

历史clean回归的逐模型/逐折 induced hallucination、clean→hallucinated transition 和empty guardrail保存在JSON中；risk strata逐prompt表见 `metrics_by_historical_risk.csv`。
