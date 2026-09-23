# Cross-Task Code/Install Transfer Summary

- model: `qwen3`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3220 | 0.2098 | 0.5880 | 0.2460 | 1.6400 | 1.2960 | 0.3440 |
| install | 0.3020 | 0.2157 | 0.7520 | 0.0560 | 1.4740 | 1.1560 | 0.3180 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0960 | 0.0960 | 0.1934 |
