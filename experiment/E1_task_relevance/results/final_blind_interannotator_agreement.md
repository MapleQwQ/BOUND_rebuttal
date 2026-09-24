# E1 Final Blind Inter-Annotator Agreement

## Technical summary

Before adjudication, the two blind annotators agreed on **89.3%** of answer-level Adequacy labels (Cohen's κ = **0.834**). Registry status was highly reproducible (**98.4%**, κ = **0.955**), while task-role classification was the main judgment boundary (**71.8%**, κ = **0.569**). Both annotators marked all 300 answers judgeable.

## Agreement results

| Dimension | Unit / N | Exact agreement | Cohen's κ | Disagreements |
|---|---:|---:|---:|---:|
| Adequacy | answers / 300 | 89.33% | 0.834 | 32 |
| Registry status | candidates / 960 | 98.44% | 0.955 | 15 |
| Task role | candidates / 960 | 71.77% | 0.569 | 271 |
| Candidate covered-slot set | candidates / 960 | 92.40% | 0.849 | 73 |
| Answer covered-slot set | answers / 300 | 89.33% | 0.863 | 32 |
| Answer-slot binary coverage | answer-slot pairs / 525 | 93.33% | 0.867 | 35 |
| Candidate-slot binary coverage | candidate-slot pairs / 1995 | 96.14% | 0.865 | 77 |
| Cannot judge | answers / 300 | 100.00% | undefined (constant false) | 0 |

## Scope and definitions

Exact agreement compares the complete category or covered-slot set at the stated unit. Binary slot agreement expands each answer or candidate against every frozen slot for its anonymous task. Cohen's κ uses the two annotators' observed marginal label distributions; κ is undefined for `cannot_judge` because both series contain only `false`.

## Main disagreement pattern

There were 176 answers with at least one answer- or candidate-level disagreement. The dominant issue was the boundary between `optional_support` and `irrelevant`, followed by whether a general-purpose package directly covered a frozen atomic slot. Registry disagreements were narrow and mostly involved package-like strings that also denote external products (`aws-cdk`, `powerdns`, `openstack`, and `pugjs`).

## Methodology and robustness

Rows were aligned by blind answer ID and candidate index, with candidate-name equality asserted. Agreement was calculated before any adjudication. The analysis used only the six authorized anonymous inputs; the guideline was read only for label semantics. No model, method, fold, key, non-anonymous manifest, old annotation/adjudication, or evaluation-source file was loaded.

## Limitations

κ is sensitive to marginal prevalence, so exact agreement is reported alongside it. Slot-set exact agreement is intentionally strict; binary slot agreement is also shown to distinguish one-slot boundary errors from wholly different judgments.
