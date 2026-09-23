# Cross-Task Code/Install Transfer Summary

- model: `deepseekcoder`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3380 | 0.2547 | 0.6560 | 0.1100 | 1.4840 | 1.1060 | 0.3780 |
| install | 0.3120 | 0.1660 | 0.8020 | 0.0780 | 2.0240 | 1.6880 | 0.3360 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0580 | 0.0580 | 0.0964 |
