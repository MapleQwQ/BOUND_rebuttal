# E3 DeepSeekCoder small100 初步结果

> 仅适用于 preliminary exact-exclusion manifest 和 model-cutoff labels；deployment snapshot 与完整 near-duplicate audit 尚未完成。

| 条件 | Sample-HR | Package-HR | Empty | Avg packages |
| --- | ---: | ---: | ---: | ---: |
| base | 0.030 | 0.016 | 0.060 | 2.502 |
| bound_A | 0.034 | 0.024 | 0.272 | 1.896 |
| bound_B | 0.060 | 0.029 | 0.102 | 2.326 |
| bound_C | 0.030 | 0.014 | 0.084 | 2.656 |
| bound_D | 0.106 | 0.049 | 0.050 | 2.734 |

四折 BOUND macro Sample-HR=0.057；Base=0.030；绝对差=0.027，prompt bootstrap 95% CI=[0.001, 0.053]。
Common-seed schedule mismatch count=0。
