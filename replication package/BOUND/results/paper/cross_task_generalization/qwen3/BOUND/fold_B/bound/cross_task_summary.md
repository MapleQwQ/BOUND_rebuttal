# Cross-Task Code/Install Transfer Summary

- model: `qwen3`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3000 | 0.2328 | 0.5160 | 0.3000 | 1.3060 | 1.0020 | 0.3040 |
| install | 0.1240 | 0.1683 | 0.4440 | 0.4980 | 0.8320 | 0.6920 | 0.1400 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0160 | 0.0160 | 0.0406 |
