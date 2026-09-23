# Cross-Task Code/Install Transfer Summary

- model: `deepseekcoder`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3340 | 0.2580 | 0.6420 | 0.1360 | 1.4340 | 1.0640 | 0.3700 |
| install | 0.2720 | 0.1778 | 0.7040 | 0.2040 | 1.8000 | 1.4800 | 0.3200 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0400 | 0.0400 | 0.0762 |
