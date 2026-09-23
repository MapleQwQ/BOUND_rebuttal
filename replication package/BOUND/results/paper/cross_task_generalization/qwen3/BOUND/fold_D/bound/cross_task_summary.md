# Cross-Task Code/Install Transfer Summary

- model: `qwen3`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3660 | 0.2178 | 0.6280 | 0.1920 | 1.8640 | 1.4580 | 0.4060 |
| install | 0.2880 | 0.2388 | 0.6240 | 0.2260 | 1.3900 | 1.0580 | 0.3320 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0980 | 0.0980 | 0.1909 |
