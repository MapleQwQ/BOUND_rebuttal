# E3 三模型 small100 初步综合结果

> 仅适用于 preliminary exact-exclusion manifest 和各模型 cutoff labels；完整近重复排除与共同 deployment snapshot 尚未完成。

| 模型 | Base Sample-HR | BOUND 四折 macro | 差值（BOUND−Base） | Base Empty | BOUND Empty macro |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 0.0300 | 0.0575 | +0.0275 | 0.0600 | 0.1270 |
| Qwen3 | 0.0220 | 0.0065 | -0.0155 | 0.2280 | 0.3390 |
| Llama-3.1 | 0.0880 | 0.1130 | +0.0250 | 0.0320 | 0.0845 |
| 三模型等权 macro | 0.0467 | 0.0590 | +0.0123 | 0.1067 | 0.1835 |

共享 prompt 配对 bootstrap（2,000 次）的三模型 macro Sample-HR 差值 95% CI 为 `[-0.0045, +0.0270]`。正值表示 BOUND 的幻觉回答比例更高。

Package-HR 的三模型等权 macro：Base=0.0263，BOUND=0.0351，差值=+0.0089。Empty rate 的对应差值为 +0.0768。

15 个条件合计 7,500 次生成；common-seed mismatch=0。

解释：两个模型的 Sample-HR 点估计上升，仅 Qwen3 下降；联合结果不能支持“BOUND 在未筛选共同提示集上降低幻觉”的主张。该结果仍是 small-100 preliminary evidence，不能代表真实开发者分布，也不能替代完成 leakage audit 后的确认性 E3。
