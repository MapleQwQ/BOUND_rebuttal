# E2 one-shot repair 小规模结果

范围：Llama-3.1-fold-C，固定 100 prompts；Base 与一个指定 BOUND fold 各使用已有 generation 0 作为初始回答。
registry 为 PackMonitor 官方 commit 随附的 PyPI 名称文件；采用贪心修正、最多一次，之后重新验证全部候选。

| 条件 | 初始 invalid 率 | repair 后仍有 invalid（过滤前） | 最终空回答率 | repair 成功率（尝试中） | p50/p95 repair 延迟（秒） |
|---|---:|---:|---:|---:|---:|
| base | 0.700 | 0.280 | 0.010 | 0.600 | 0.740/3.371 |
| bound_fold_C | 0.460 | 0.170 | 0.000 | 0.630 | 0.627/1.210 |

`repair_verified` 要求修正后没有 invalid 且最终列表非空；仍有 invalid 的回答执行 `final_filter`。
该结果只使用一个模型、一个 BOUND fold、每 prompt 一条初始回答，是小规模探索，不代替四折/三模型正式比较。
