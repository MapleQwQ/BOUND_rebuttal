# E2 三模型四折 one-shot repair 汇总

每个模型、每折固定100 prompts；每个条件使用已有 generation 0。Base 指标取 fold-A 文件，BOUND macro 为 A/B/C/D 四折算术平均。

| 模型 | 条件 | 初始 invalid | repair后残余 invalid | 最终空回答 | repair成功率 | 最终包数 |
|---|---|---:|---:|---:|---:|---:|
| DeepSeekCoder | Base | 0.740 | 0.430 | 0.250 | 0.243 | 1.690 |
| DeepSeekCoder | BOUND四折均值 | 0.295 | 0.163 | 0.092 | 0.456 | 2.793 |
| Qwen3 | Base | 0.710 | 0.290 | 0.040 | 0.592 | 3.870 |
| Qwen3 | BOUND四折均值 | 0.155 | 0.055 | 0.260 | 0.658 | 1.720 |
| Llama-3.1 | Base | 0.700 | 0.280 | 0.010 | 0.600 | 3.770 |
| Llama-3.1 | BOUND四折均值 | 0.382 | 0.135 | 0.135 | 0.641 | 3.218 |

注意：最终过滤按构造移除残余 invalid，但不保证任务充分性。空回答和最终包数是必要 guardrails；该实验仍不是 PackMonitor 生成中约束解码，也不是真实 coding-agent 执行实验。
