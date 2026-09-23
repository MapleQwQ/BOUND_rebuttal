# Cross-Task Code/Install Transfer Summary

- model: `llama3.1`
- method: `BOUND`
- mode: `generation`
- tasks: `code,install`
- prompts: `500`

## Task Metrics

| task | Sample-HR | Package-HR | Valid-Rate | Empty-Rate | Avg Packages | Avg Valid | Avg Hallucinated |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| code | 0.2780 | 0.1955 | 0.7080 | 0.1780 | 1.7700 | 1.4240 | 0.3460 |
| install | 0.3540 | 0.2042 | 0.8440 | 0.0200 | 2.2820 | 1.8160 | 0.4660 |

## Cross-task Metrics

| Any overlap | All-task overlap | Code Install Jaccard |
| ---: | ---: | ---: |
| 0.0780 | 0.0780 | 0.1327 |
