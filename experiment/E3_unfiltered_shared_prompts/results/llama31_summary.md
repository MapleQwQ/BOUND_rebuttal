# E3 Llama-3.1 small100 初步结果

> 仅适用于 preliminary exact-exclusion manifest 和 model-cutoff labels；deployment snapshot 与完整 near-duplicate audit 尚未完成。

| 条件 | Sample-HR | Package-HR | Empty | Avg packages |
| --- | ---: | ---: | ---: | ---: |
| base | 0.088 | 0.049 | 0.032 | 2.634 |
| bound_A | 0.090 | 0.067 | 0.076 | 2.370 |
| bound_B | 0.156 | 0.113 | 0.228 | 2.800 |
| bound_C | 0.118 | 0.064 | 0.012 | 2.634 |
| bound_D | 0.088 | 0.044 | 0.022 | 2.924 |

四折 BOUND macro Sample-HR=0.113；Base=0.088；绝对差=0.025，prompt bootstrap 95% CI=[-0.010, 0.062]。
Common-seed schedule mismatch count=0。
