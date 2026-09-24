# E1 Final Blind Adjudication Summary

## Technical summary

All **300 anonymous answers** and **960 raw candidate names** were adjudicated without unblinding. Final Adequacy is: **83 adequate**, **71 partially adequate with a clear omission**, and **146 inadequate**; no item remains `cannot_judge`. Of the 300 answers, 124 required no change and 176 contained at least one pre-adjudication disagreement.

## Decision principles applied

- Exact raw names were evaluated as written. A nonexistent or wrong import/distribution name was never silently replaced with the likely intended package.
- `core_function_support` requires documented capability tied to at least one frozen slot. Related infrastructure, generic clients, exporters, or frameworks remain `optional_support` when they do not satisfy the atomic requirement or explicit ecosystem constraint.
- External products were separated from PyPI distributions when the raw string clearly denoted a real tool/product. Their existence was not misreported as a PyPI hit.
- Adequacy was derived from the union of adjudicated candidate slot coverage. Extra hallucinated packages did not erase valid coverage, but hallucinated packages never supplied coverage.
- Consensus fields were preserved unless a dependent coverage/role consistency correction was required by an expressly adjudicated disagreement.

## Evidence-sensitive boundary decisions

- `pyusps` was not credited for rate or label slots: its project README says only the Address Information API is supported.
- `semantic-release` was not silently corrected to `python-semantic-release`; the exact PyPI distribution has no documented release-automation capability.
- `jaeger-client` was treated as OpenTracing support, not an OpenTelemetry Jaeger exporter.
- `opentelemetry-exporter-prometheus` exports metrics but does not itself collect Kafka producer/consumer/topic metrics.
- `transformers` was credited for Whisper transcription but not for the required CTranslate2 backend.
- Keras was credited for both image data loading/preprocessing and neural-network training/evaluation.
- Django plus Graphene was credited for the Django GraphQL integration and GraphQL schema/mutation capabilities; generic AWS CDK ECS/IAM/Logs/CloudWatch libraries were not credited as the requested ECS service-extension abstraction.
- Pillow/OpenCV were credited for JPEG 2000 conversion/metadata support, but not as the explicitly requested OpenJPEG Python binding.

## Final label distributions

| Dimension | Counts |
|---|---|
| Adequacy | {'adequate': 83, 'partially_adequate_with_clear_omission': 71, 'inadequate': 146} |
| Task role | {'core_function_support': 266, 'optional_support': 419, 'irrelevant': 275} |
| Registry status | {'exists_at_audit_date': 758, 'nonexistent_at_audit_date': 152, 'not_applicable_stdlib': 24, 'not_applicable_external_tool': 26} |
| Cannot judge | `false`: 300 |

## Adjudication balance

Across disputed fields, the evidence-supported outcome matched annotator A 197 times, matched annotator B 197 times, and used an independent third resolution 5 times. This tally is descriptive only; no majority or default-conservative rule was used.

## QA and robustness

- 300 unique blind answer IDs: passed.
- 960 candidate annotations: passed.
- 60 anonymous tasks × 5 answers each: passed.
- Every candidate and answer slot reference belongs to the task's frozen slot set: passed.
- Every answer-level covered-slot set equals the union of its candidate covered-slot sets: passed.
- `core_function_support` and non-empty candidate slot coverage are mutually consistent: passed.
- Adequacy is consistent with complete, partial, or zero frozen-slot coverage, including the no-third-party task: passed.
- Blinding guardrail: only the authorized anonymous inputs were read; no keys, mappings, non-anonymous manifests, old labels/adjudications/agreements, evaluation sources, model identities, methods, or folds were consulted.

## Output inventory

- `final_blind_adjudicated_labels.jsonl`: complete 300-row adjudicated label set.
- `final_blind_interannotator_disagreements.jsonl`: every answer with at least one raw disagreement, including both labels, final resolution, rationale, and evidence URLs.
- `final_blind_interannotator_agreement.json` and `.md`: pre-adjudication agreement statistics.

## Remaining limitation

The adjudication assesses package existence and documented capability at the audit date. It does not execute each package, and it does not infer success from an unverified likely-intended replacement package. This is deliberately conservative only at the raw-name identity boundary, not as a blanket policy for role or Adequacy decisions.
