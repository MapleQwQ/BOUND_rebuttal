# Cross-Task Code/Install Transfer Summary

- model: `llama3.1`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.3580 | 0.2443 | 0.7000 | 0.1440 | 1.7440 | 1.3180 | 0.4260 |
| install | 0.4900 | 0.2968 | 0.7240 | 0.0420 | 2.2440 | 1.5780 | 0.6660 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.1460 | 0.1460 | 0.2073 |
