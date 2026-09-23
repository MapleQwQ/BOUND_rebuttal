# Dataset

BOUND uses package-recommendation prompts derived from the package hallucination benchmark introduced by Spracklen et al. in "We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs".
This directory contains the paper input splits needed to run BOUND.

For each model, data are stored under:

```text
data/package_hallucination/{model}/
```

Each model directory contains:

```text
high_risk_prompts.jsonl       # all high-risk prompts used by the paper split
unseen_prompts.jsonl          # non-edit high-risk unseen prompts
cross_task_test100.jsonl      # 100 base prompts for cross-task generalization
fold_A/edit_cases.jsonl       # 50 edit cases
fold_B/edit_cases.jsonl       # 50 edit cases
fold_C/edit_cases.jsonl       # 50 edit cases
fold_D/edit_cases.jsonl       # 50 edit cases
```

`high_risk_prompts.jsonl` is the union of the 200 edit prompts and the unseen high-risk prompts.
Rows keep the original five-generation package behavior in the `trials` field, which is used as the base-model reference during edited model evaluation.

The paper split sizes are:

| model | high-risk prompts | edit folds | unseen prompts | cross-task prompts |
| --- | ---: | ---: | ---: | ---: |
| deepseekcoder | 741 | 4 x 50 | 541 | 100 |
| qwen3 | 609 | 4 x 50 | 409 | 100 |
| llama3.1 | 1134 | 4 x 50 | 934 | 100 |

The cross-task generalization experiment evaluates each base cross-task prompt with five generated responses at runtime without expanding the input prompt file.
