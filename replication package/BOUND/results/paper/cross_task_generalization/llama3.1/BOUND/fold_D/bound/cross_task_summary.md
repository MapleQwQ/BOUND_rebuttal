# Cross-Task Code/Install Transfer Summary

- model: `llama3.1`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.2880 | 0.1953 | 0.7340 | 0.1540 | 1.7000 | 1.3680 | 0.3320 |
| install | 0.3760 | 0.2295 | 0.8480 | 0.0260 | 2.7620 | 2.1280 | 0.6340 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0600 | 0.0600 | 0.0946 |
