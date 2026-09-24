# E3 Qwen3 small100 初步结果

> 仅适用于 preliminary exact-exclusion manifest 和 model-cutoff labels；deployment snapshot 与完整 near-duplicate audit 尚未完成。

| 条件 | Sample-HR | Package-HR | Empty | Avg packages |
| --- | ---: | ---: | ---: | ---: |
| base | 0.022 | 0.014 | 0.228 | 1.918 |
| bound_A | 0.002 | 0.001 | 0.166 | 1.696 |
| bound_B | 0.002 | 0.002 | 0.538 | 1.034 |
| bound_C | 0.012 | 0.010 | 0.370 | 1.828 |
| bound_D | 0.010 | 0.006 | 0.282 | 2.094 |

四折 BOUND macro Sample-HR=0.007；Base=0.022；绝对差=-0.015，prompt bootstrap 95% CI=[-0.039, 0.002]。
Common-seed schedule mismatch count=0。
