# Cross-Task Code/Install Transfer Summary

- model: `deepseekcoder`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3100 | 0.2525 | 0.6520 | 0.1560 | 1.4260 | 1.0660 | 0.3600 |
| install | 0.3760 | 0.2429 | 0.7980 | 0.0360 | 1.9600 | 1.4840 | 0.4760 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0800 | 0.0800 | 0.1361 |
