# Cross-Task Code/Install Transfer Summary

- model: `llama3.1`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3100 | 0.1931 | 0.7240 | 0.1660 | 1.9260 | 1.5540 | 0.3720 |
| install | 0.3100 | 0.2663 | 0.6540 | 0.2640 | 2.3360 | 1.7140 | 0.6220 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0460 | 0.0460 | 0.0771 |
