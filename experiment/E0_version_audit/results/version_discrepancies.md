# E0 version freeze and result-consistency audit

Generated: `2026-09-23T14:05:08.013336+00:00`

## Decision summary

- **Paper evidence integrity:** 321 table cells were traced; 235 exact/display matches, 17 rounding-only differences, 56 material/semantic mismatches, and 13 explicit N/A cells.
- **Raw-result validation:** the repository validator completed with `bad=0, warn=2`; all 147 RQ1 rows, 72 RQ2 method-fold results, 60 RQ3 rows, cost arithmetic, and 15 selected HumanEval summaries passed.
- **RQ1 copy integrity:** 16/24 curated BOUND evaluation files are byte-identical and 24/24 have identical metric summaries to the historical result files.
- **LoRA artifacts:** all 12 main BOUND deltas load successfully; average size is `731.03 KiB`; module counts are DeepSeekCoder=[7], Qwen3=[9], Llama-3.1=[7].
- **Blocking issue:** cloned replication cutoff dates disagree with the result-producing configs for DeepSeekCoder and Llama-3.1. Do not claim the cloned package reproduces submitted numbers until these configs are reconciled.

## Cell-level audit

| Table | Match | Rounding only | Mismatch | N/A |
| --- | ---: | ---: | ---: | ---: |
| `tab:cost_bound` | 19 | 0 | 1 | 4 |
| `tab:editing_drop` | 14 | 4 | 0 | 0 |
| `tab:main_results_three_models` | 106 | 11 | 0 | 9 |
| `tab:rq2_cross_task` | 51 | 2 | 55 | 0 |
| `tab:rq3_ablation` | 45 | 0 | 0 | 0 |

### Mismatching paper cells

| Cell | Paper | Recomputed | Difference |
| --- | ---: | ---: | ---: |
| `tab:rq2_cross_task::deepseekcoder|Base|install|Sample-HR` | 0.434 | 0.444 | 0.01 |
| `tab:rq2_cross_task::deepseekcoder|Base|install|Package-HR` | 0.2986 | 0.3048 | 0.0062 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|code|Sample-HR` | 0.326 | 0.3285 | 0.0025 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|code|Package-HR` | 0.2542 | 0.25605 | 0.00185 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|code|Valid-Rate` | 0.6415 | 0.6405 | 0.001 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|install|Sample-HR` | 0.3375 | 0.3445 | 0.007 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|install|Package-HR` | 0.1987 | 0.202075 | 0.003375 |
| `tab:rq2_cross_task::deepseekcoder|BOUND|install|Valid-Rate` | 0.769 | 0.7635 | 0.0055 |
| `tab:rq2_cross_task::deepseekcoder|DINM|code|Sample-HR` | 0.3105 | 0.3545 | 0.044 |
| `tab:rq2_cross_task::deepseekcoder|DINM|code|Package-HR` | 0.2714 | 0.31645 | 0.04505 |
| `tab:rq2_cross_task::deepseekcoder|DINM|code|Valid-Rate` | 0.5655 | 0.5425 | 0.023 |
| `tab:rq2_cross_task::deepseekcoder|DINM|install|Sample-HR` | 0.207 | 0.2135 | 0.0065 |
| `tab:rq2_cross_task::deepseekcoder|DINM|install|Package-HR` | 0.2352 | 0.255075 | 0.019875 |
| `tab:rq2_cross_task::deepseekcoder|DINM|install|Valid-Rate` | 0.3985 | 0.396 | 0.0025 |
| `tab:rq2_cross_task::deepseekcoder|MEMIT|code|Sample-HR` | 0.355 | 0.3555 | 0.0005 |
| `tab:rq2_cross_task::deepseekcoder|MEMIT|code|Package-HR` | 0.2758 | 0.27615 | 0.00035 |
| `tab:rq2_cross_task::deepseekcoder|MEMIT|install|Sample-HR` | 0.415 | 0.4165 | 0.0015 |
| `tab:rq2_cross_task::deepseekcoder|MEMIT|install|Package-HR` | 0.3017 | 0.3026 | 0.0009 |
| `tab:rq2_cross_task::deepseekcoder|ROME|code|Sample-HR` | 0.085 | 0.21 | 0.125 |
| `tab:rq2_cross_task::deepseekcoder|ROME|code|Package-HR` | 0.0671 | 0.25 | 0.1829 |
| `tab:rq2_cross_task::deepseekcoder|ROME|code|Valid-Rate` | 0.151 | 0 | 0.151 |
| `tab:rq2_cross_task::deepseekcoder|ROME|install|Sample-HR` | 0.101 | 0.205 | 0.104 |
| `tab:rq2_cross_task::deepseekcoder|ROME|install|Package-HR` | 0.0669 | 0.25 | 0.1831 |
| `tab:rq2_cross_task::deepseekcoder|ROME|install|Valid-Rate` | 0.1515 | 0 | 0.1515 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|code|Sample-HR` | 0.354 | 0.6155 | 0.2615 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|code|Package-HR` | 0.2729 | 0.639325 | 0.366425 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|code|Valid-Rate` | 0.6385 | 0.322 | 0.3165 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|install|Sample-HR` | 0.3845 | 0.626 | 0.2415 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|install|Package-HR` | 0.2547 | 0.624275 | 0.369575 |
| `tab:rq2_cross_task::deepseekcoder|Full-FT|install|Valid-Rate` | 0.6275 | 0.283 | 0.3445 |
| `tab:rq2_cross_task::qwen3|BOUND|code|Sample-HR` | 0.3385 | 0.357 | 0.0185 |
| `tab:rq2_cross_task::qwen3|BOUND|code|Package-HR` | 0.2237 | 0.24645 | 0.02275 |
| `tab:rq2_cross_task::qwen3|BOUND|code|Valid-Rate` | 0.5815 | 0.579 | 0.0025 |
| `tab:rq2_cross_task::qwen3|BOUND|install|Sample-HR` | 0.24 | 0.2435 | 0.0035 |
| `tab:rq2_cross_task::qwen3|BOUND|install|Package-HR` | 0.2122 | 0.2202 | 0.008 |
| `tab:rq2_cross_task::qwen3|BOUND|install|Valid-Rate` | 0.603 | 0.6005 | 0.0025 |
| `tab:rq2_cross_task::qwen3|MEMIT|code|Sample-HR` | 0.364 | 0.3665 | 0.0025 |
| `tab:rq2_cross_task::qwen3|MEMIT|code|Package-HR` | 0.2829 | 0.28475 | 0.00185 |
| `tab:rq2_cross_task::qwen3|MEMIT|install|Sample-HR` | 0.491 | 0.4915 | 0.0005 |
| `tab:rq2_cross_task::qwen3|MEMIT|install|Package-HR` | 0.3608 | 0.361175 | 0.000375 |
| `tab:rq2_cross_task::qwen3|Full-FT|code|Sample-HR` | 0.093 | 0.0945 | 0.0015 |
| `tab:rq2_cross_task::qwen3|Full-FT|code|Package-HR` | 0.1094 | 0.110375 | 0.000975 |
| `tab:rq2_cross_task::qwen3|Full-FT|code|Valid-Rate` | 0.32 | 0.319 | 0.001 |
| `tab:rq2_cross_task::llama3.1|Base|code|Sample-HR` | 0.338 | 0.348 | 0.01 |
| `tab:rq2_cross_task::llama3.1|Base|code|Package-HR` | 0.2425 | 0.2485 | 0.006 |
| `tab:rq2_cross_task::llama3.1|Base|install|Sample-HR` | 0.576 | 0.578 | 0.002 |
| `tab:rq2_cross_task::llama3.1|Base|install|Package-HR` | 0.3452 | 0.3482 | 0.003 |
| `tab:rq2_cross_task::llama3.1|BOUND|install|Sample-HR` | 0.3825 | 0.387 | 0.0045 |
| `tab:rq2_cross_task::llama3.1|BOUND|install|Package-HR` | 0.2492 | 0.253725 | 0.004525 |
| `tab:rq2_cross_task::llama3.1|MEMIT|code|Sample-HR` | 0.3355 | 0.3385 | 0.003 |
| `tab:rq2_cross_task::llama3.1|MEMIT|code|Package-HR` | 0.2319 | 0.23725 | 0.00535 |
| `tab:rq2_cross_task::llama3.1|MEMIT|code|Valid-Rate` | 0.689 | 0.6885 | 0.0005 |
| `tab:rq2_cross_task::llama3.1|MEMIT|install|Sample-HR` | 0.565 | 0.575 | 0.01 |
| `tab:rq2_cross_task::llama3.1|MEMIT|install|Package-HR` | 0.3348 | 0.3441 | 0.0093 |
| `tab:rq2_cross_task::llama3.1|MEMIT|install|Valid-Rate` | 0.6785 | 0.6715 | 0.007 |
| `tab:cost_bound::all|MEMIT|mean|Loc. time (s)` |  | 0 |  |

Rounding-only differences are at most one unit in the displayed last decimal and arise when the manuscript averages already-rounded fold rows rather than full-precision JSON metrics. They are not counted as material mismatches, but the aggregation rule should be standardized.

Interpretation: most material mismatches are in RQ2 manuscript TeX versus the currently frozen method-fold results. The 72 stored RQ2 rows independently pass recomputation from `rq2_details.jsonl`; update the paper values or document and freeze the older aggregation source before rebuttal. The cost table also displays MEMIT localization time as N/A while its frozen numeric input is `0.00`; choose one semantic convention.

## Cutoff audit

| Model | Result-producing configs | Cloned replication package | Match |
| --- | --- | --- | --- |
| deepseekcoder | `2023-11-02` | `2023-10-29` | **NO** |
| qwen3 | `2025-04-29` | `2025-04-29` | yes |
| llama3.1 | `2024-07-23` | `2023-12-31` | **NO** |

The result-producing dates are consistent across folds and are authoritative for reproducing the submitted numbers. However, the paper does not state these exact dates, and the repository contains no citation establishing whether each date denotes a provider-declared knowledge cutoff, model release date, or the package-existence snapshot boundary. This semantic/source provenance remains unresolved and should be documented before artifact release.

## Llama-3.1 fold A run2 lineage

`paper_raw_data.md` explicitly states that the RQ1 table uses the Llama-3.1 fold-A BOUND run2 replacement. The run2 artifact sequence is internally coherent:

| File | Modified (UTC) | Bytes |
| --- | --- | ---: |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/blast_delta.pt` | 2026-06-13T17:21:41.957426+00:00 | 578889 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/train_log.jsonl` | 2026-06-13T17:21:41.969426+00:00 | 19601 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/localization_report.json` | 2026-06-13T17:21:41.993426+00:00 | 24043 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/eval_edit_prompts.json` | 2026-06-13T17:33:35.660668+00:00 | 364361 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/eval_unseen_prompts.json` | 2026-06-13T19:08:48.290596+00:00 | 6484999 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/blast_50.gpu4.rq1_run2.runtime.yaml` | 2026-06-13T17:22:13.489393+00:00 | 1255 |
| `knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50/blast_50.gpu5.rq1_run2.runtime.yaml` | 2026-06-13T17:25:08.925206+00:00 | 1255 |

The delta/train/localization artifacts were written first, followed by edit and unseen evaluation files. Both GPU4 and GPU5 runtime YAMLs contain the same experiment configuration; because no immutable run ID is embedded in the JSON outputs, the exact evaluator process cannot be distinguished after the fact. The final directory contents and their hashes are therefore the frozen authority.

## Base-reference discrepancy

RQ1 uses dedicated `base_heldout_highrisk_eval.json` files for the Base row. The `baseline_*` fields embedded in edited-model evaluation JSONs are not identical for all models/runs and must not be substituted for those dedicated Base files. This explains previously observed differences such as DeepSeekCoder heldout Sample-HR `0.8333` (paper Base source) versus `0.8288` (embedded baseline in a BOUND evaluation).

## Manifest scope and limitations

`artifact_manifest.json` hashes 395 evidence files (629785720 bytes): manuscript TeX, all files directly cited by the cell provenance table, the 12 BOUND deltas and their configs/logs/evaluations, and the cloned cutoff configs. Large Full-FT checkpoint shards and unused exploratory runs are intentionally excluded because they are not inputs to the submitted paper tables. Their existence was checked separately during the pre-E0 inventory.

Cost rows remain the weakest lineage: the preserved numeric inputs reproduce the table, but most entries do not point to per-run logs. HumanEval also uses an explicitly selected one-run-per-fold protocol rather than all stored repeats. Both should be disclosed or strengthened in the artifact documentation.

## Required remediation before rebuttal freeze

1. Correct or explicitly explain every `mismatch` row in `paper_cell_provenance.csv`, especially RQ2 Base cells.
2. Reconcile DeepSeekCoder and Llama-3.1 cutoff dates in the cloned replication package with the result-producing configs; add a source and definition for each cutoff.
3. Preserve the current Llama fold-A run2 hashes and identify it as the final authoritative run.
4. Add log-level provenance for cost inputs if available; otherwise state that the table is reproducible from frozen numeric inputs but not fully traceable to raw runtime logs.
