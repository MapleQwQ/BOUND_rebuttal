# Cross-Task Code/Install Transfer Summary

- model: `deepseekcoder`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3220 | 0.2518 | 0.6160 | 0.1520 | 1.3820 | 1.0340 | 0.3480 |
| install | 0.3900 | 0.2081 | 0.7720 | 0.0280 | 2.0760 | 1.6440 | 0.4320 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0920 | 0.0920 | 0.1588 |
