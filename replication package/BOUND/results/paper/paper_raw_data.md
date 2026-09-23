# BOUND Replication Raw Results

This file intentionally retains only BOUND result rows and the raw paths needed to inspect or recompute the BOUND replication artifacts. Non-BOUND outputs are not included in this replication package.

## Package Recommendation Editing

| model | fold | method | scope | prompts | Sample-HR | Package-HR | Valid-Rate | result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseekcoder | A | BOUND | edit50 | 50 | 0.0920 | 0.0508 | 0.8720 | `results/paper/package_recommendation/deepseekcoder/fold_A/BOUND/eval_edit_prompts.json` |
| deepseekcoder | A | BOUND | unseen | 541 | 0.2248 | 0.1227 | 0.8152 | `results/paper/package_recommendation/deepseekcoder/fold_A/BOUND/eval_unseen_prompts.json` |
| deepseekcoder | B | BOUND | edit50 | 50 | 0.2120 | 0.0790 | 0.9400 | `results/paper/package_recommendation/deepseekcoder/fold_B/BOUND/eval_edit_prompts.json` |
| deepseekcoder | B | BOUND | unseen | 541 | 0.4078 | 0.2062 | 0.8876 | `results/paper/package_recommendation/deepseekcoder/fold_B/BOUND/eval_unseen_prompts.json` |
| deepseekcoder | C | BOUND | edit50 | 50 | 0.2480 | 0.0781 | 0.9840 | `results/paper/package_recommendation/deepseekcoder/fold_C/BOUND/eval_edit_prompts.json` |
| deepseekcoder | C | BOUND | unseen | 541 | 0.3726 | 0.1481 | 0.9168 | `results/paper/package_recommendation/deepseekcoder/fold_C/BOUND/eval_unseen_prompts.json` |
| deepseekcoder | D | BOUND | edit50 | 50 | 0.2400 | 0.0901 | 0.9960 | `results/paper/package_recommendation/deepseekcoder/fold_D/BOUND/eval_edit_prompts.json` |
| deepseekcoder | D | BOUND | unseen | 541 | 0.4795 | 0.2056 | 0.9442 | `results/paper/package_recommendation/deepseekcoder/fold_D/BOUND/eval_unseen_prompts.json` |
| llama3.1 | A | BOUND | edit50 | 50 | 0.2880 | 0.1227 | 0.8800 | `results/paper/package_recommendation/llama3.1/fold_A/BOUND/eval_edit_prompts.json` |
| llama3.1 | A | BOUND | unseen | 934 | 0.3405 | 0.1693 | 0.7923 | `results/paper/package_recommendation/llama3.1/fold_A/BOUND/eval_unseen_prompts.json` |
| llama3.1 | B | BOUND | edit50 | 50 | 0.2000 | 0.1095 | 0.6760 | `results/paper/package_recommendation/llama3.1/fold_B/BOUND/eval_edit_prompts.json` |
| llama3.1 | B | BOUND | unseen | 934 | 0.3779 | 0.2230 | 0.6610 | `results/paper/package_recommendation/llama3.1/fold_B/BOUND/eval_unseen_prompts.json` |
| llama3.1 | C | BOUND | edit50 | 50 | 0.4400 | 0.1928 | 0.9680 | `results/paper/package_recommendation/llama3.1/fold_C/BOUND/eval_edit_prompts.json` |
| llama3.1 | C | BOUND | unseen | 934 | 0.5069 | 0.2307 | 0.9460 | `results/paper/package_recommendation/llama3.1/fold_C/BOUND/eval_unseen_prompts.json` |
| llama3.1 | D | BOUND | edit50 | 50 | 0.3440 | 0.1426 | 0.9520 | `results/paper/package_recommendation/llama3.1/fold_D/BOUND/eval_edit_prompts.json` |
| llama3.1 | D | BOUND | unseen | 934 | 0.3878 | 0.1588 | 0.9420 | `results/paper/package_recommendation/llama3.1/fold_D/BOUND/eval_unseen_prompts.json` |
| qwen3 | A | BOUND | edit50 | 50 | 0.0800 | 0.0445 | 0.8520 | `results/paper/package_recommendation/qwen3/fold_A/BOUND/eval_edit_prompts.json` |
| qwen3 | A | BOUND | unseen | 409 | 0.1193 | 0.0745 | 0.8650 | `results/paper/package_recommendation/qwen3/fold_A/BOUND/eval_unseen_prompts.json` |
| qwen3 | B | BOUND | edit50 | 50 | 0.0480 | 0.0502 | 0.5160 | `results/paper/package_recommendation/qwen3/fold_B/BOUND/eval_edit_prompts.json` |
| qwen3 | B | BOUND | unseen | 409 | 0.1022 | 0.0799 | 0.5570 | `results/paper/package_recommendation/qwen3/fold_B/BOUND/eval_unseen_prompts.json` |
| qwen3 | C | BOUND | edit50 | 50 | 0.1360 | 0.0515 | 0.7400 | `results/paper/package_recommendation/qwen3/fold_C/BOUND/eval_edit_prompts.json` |
| qwen3 | C | BOUND | unseen | 409 | 0.2181 | 0.1206 | 0.7232 | `results/paper/package_recommendation/qwen3/fold_C/BOUND/eval_unseen_prompts.json` |
| qwen3 | D | BOUND | edit50 | 50 | 0.1320 | 0.0643 | 0.8560 | `results/paper/package_recommendation/qwen3/fold_D/BOUND/eval_edit_prompts.json` |
| qwen3 | D | BOUND | unseen | 409 | 0.1985 | 0.0960 | 0.8284 | `results/paper/package_recommendation/qwen3/fold_D/BOUND/eval_unseen_prompts.json` |

## Cross-Task Generalization

| model | fold | method | code Sample-HR | code Package-HR | code Valid-Rate | install Sample-HR | install Package-HR | install Valid-Rate | raw result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseekcoder | A | BOUND | 0.3340 | 0.2580 | 0.6420 | 0.2720 | 0.1778 | 0.7040 | results/paper/cross_task_generalization/deepseekcoder/BOUND/fold_A/bound/cross_task_summary.md |
| deepseekcoder | B | BOUND | 0.3220 | 0.2518 | 0.6160 | 0.3900 | 0.2081 | 0.7720 | results/paper/cross_task_generalization/deepseekcoder/BOUND/fold_B/bound/cross_task_summary.md |
| deepseekcoder | C | BOUND | 0.3380 | 0.2547 | 0.6560 | 0.3120 | 0.1660 | 0.8020 | results/paper/cross_task_generalization/deepseekcoder/BOUND/fold_C/bound/cross_task_summary.md |
| deepseekcoder | D | BOUND | 0.3100 | 0.2525 | 0.6520 | 0.3760 | 0.2429 | 0.7980 | results/paper/cross_task_generalization/deepseekcoder/BOUND/fold_D/bound/cross_task_summary.md |
| qwen3 | A | BOUND | 0.3220 | 0.2098 | 0.5880 | 0.3020 | 0.2157 | 0.7520 | results/paper/cross_task_generalization/qwen3/BOUND/fold_A/bound/cross_task_summary.md |
| qwen3 | B | BOUND | 0.3000 | 0.2328 | 0.5160 | 0.1240 | 0.1683 | 0.4440 | results/paper/cross_task_generalization/qwen3/BOUND/fold_B/bound/cross_task_summary.md |
| qwen3 | C | BOUND | 0.3660 | 0.2344 | 0.5940 | 0.2460 | 0.2260 | 0.5920 | results/paper/cross_task_generalization/qwen3/BOUND/fold_C/bound/cross_task_summary.md |
| qwen3 | D | BOUND | 0.3660 | 0.2178 | 0.6280 | 0.2880 | 0.2388 | 0.6240 | results/paper/cross_task_generalization/qwen3/BOUND/fold_D/bound/cross_task_summary.md |
| llama3.1 | A | BOUND | 0.2780 | 0.1955 | 0.7080 | 0.3540 | 0.2042 | 0.8440 | results/paper/cross_task_generalization/llama3.1/BOUND/fold_A/bound/cross_task_summary.md |
| llama3.1 | B | BOUND | 0.3100 | 0.1931 | 0.7240 | 0.3100 | 0.2663 | 0.6540 | results/paper/cross_task_generalization/llama3.1/BOUND/fold_B/bound/cross_task_summary.md |
| llama3.1 | C | BOUND | 0.3580 | 0.2443 | 0.7000 | 0.4900 | 0.2968 | 0.7240 | results/paper/cross_task_generalization/llama3.1/BOUND/fold_C/bound/cross_task_summary.md |
| llama3.1 | D | BOUND | 0.2880 | 0.1953 | 0.7340 | 0.3760 | 0.2295 | 0.8480 | results/paper/cross_task_generalization/llama3.1/BOUND/fold_D/bound/cross_task_summary.md |