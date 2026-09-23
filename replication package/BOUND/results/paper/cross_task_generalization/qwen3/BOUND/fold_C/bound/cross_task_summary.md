# Cross-Task Code/Install Transfer Summary

- model: `qwen3`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3660 | 0.2344 | 0.5940 | 0.2140 | 1.6040 | 1.2280 | 0.3760 |
| install | 0.2460 | 0.2260 | 0.5920 | 0.2740 | 1.1860 | 0.9180 | 0.2680 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0680 | 0.0680 | 0.1333 |
