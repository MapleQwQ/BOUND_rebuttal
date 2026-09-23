# Recomputed BOUND Result Tables

This file is generated from raw files under `results/paper/`.

## Package Recommendation Editing
| model | fold | scope | prompts | Sample-HR | Package-HR | Valid-Rate |
| --- | --- | --- | --- | --- | --- | --- |
| deepseekcoder | A | edit50 | 50 | 0.0920 | 0.0508 | 0.8720 |
| deepseekcoder | A | unseen | 541 | 0.2248 | 0.1227 | 0.8152 |
| deepseekcoder | B | edit50 | 50 | 0.2120 | 0.0790 | 0.9400 |
| deepseekcoder | B | unseen | 541 | 0.4078 | 0.2062 | 0.8876 |
| deepseekcoder | C | edit50 | 50 | 0.2480 | 0.0781 | 0.9840 |
| deepseekcoder | C | unseen | 541 | 0.3726 | 0.1481 | 0.9168 |
| deepseekcoder | D | edit50 | 50 | 0.2400 | 0.0901 | 0.9960 |
| deepseekcoder | D | unseen | 541 | 0.4795 | 0.2056 | 0.9442 |
| qwen3 | A | edit50 | 50 | 0.0800 | 0.0445 | 0.8520 |
| qwen3 | A | unseen | 409 | 0.1193 | 0.0745 | 0.8650 |
| qwen3 | B | edit50 | 50 | 0.0480 | 0.0502 | 0.5160 |
| qwen3 | B | unseen | 409 | 0.1022 | 0.0799 | 0.5570 |
| qwen3 | C | edit50 | 50 | 0.1360 | 0.0515 | 0.7400 |
| qwen3 | C | unseen | 409 | 0.2181 | 0.1206 | 0.7232 |
| qwen3 | D | edit50 | 50 | 0.1320 | 0.0643 | 0.8560 |
| qwen3 | D | unseen | 409 | 0.1985 | 0.0960 | 0.8284 |
| llama3.1 | A | edit50 | 50 | 0.2880 | 0.1227 | 0.8800 |
| llama3.1 | A | unseen | 934 | 0.3405 | 0.1693 | 0.7923 |
| llama3.1 | B | edit50 | 50 | 0.2000 | 0.1095 | 0.6760 |
| llama3.1 | B | unseen | 934 | 0.3779 | 0.2230 | 0.6610 |
| llama3.1 | C | edit50 | 50 | 0.4400 | 0.1928 | 0.9680 |
| llama3.1 | C | unseen | 934 | 0.5069 | 0.2307 | 0.9460 |
| llama3.1 | D | edit50 | 50 | 0.3440 | 0.1426 | 0.9520 |
| llama3.1 | D | unseen | 934 | 0.3878 | 0.1588 | 0.9420 |

## Cross-Task Generalization
| model | fold | code Sample-HR | code Package-HR | code Valid-Rate | install Sample-HR | install Package-HR | install Valid-Rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deepseekcoder | A | 0.3340 | 0.2580 | 0.6420 | 0.2720 | 0.1778 | 0.7040 |
| deepseekcoder | B | 0.3220 | 0.2518 | 0.6160 | 0.3900 | 0.2081 | 0.7720 |
| deepseekcoder | C | 0.3380 | 0.2547 | 0.6560 | 0.3120 | 0.1660 | 0.8020 |
| deepseekcoder | D | 0.3100 | 0.2525 | 0.6520 | 0.3760 | 0.2429 | 0.7980 |
| qwen3 | A | 0.3220 | 0.2098 | 0.5880 | 0.3020 | 0.2157 | 0.7520 |
| qwen3 | B | 0.3000 | 0.2328 | 0.5160 | 0.1240 | 0.1683 | 0.4440 |
| qwen3 | C | 0.3660 | 0.2344 | 0.5940 | 0.2460 | 0.2260 | 0.5920 |
| qwen3 | D | 0.3660 | 0.2178 | 0.6280 | 0.2880 | 0.2388 | 0.6240 |
| llama3.1 | A | 0.2780 | 0.1955 | 0.7080 | 0.3540 | 0.2042 | 0.8440 |
| llama3.1 | B | 0.3100 | 0.1931 | 0.7240 | 0.3100 | 0.2663 | 0.6540 |
| llama3.1 | C | 0.3580 | 0.2443 | 0.7000 | 0.4900 | 0.2968 | 0.7240 |
| llama3.1 | D | 0.2880 | 0.1953 | 0.7340 | 0.3760 | 0.2295 | 0.8480 |
