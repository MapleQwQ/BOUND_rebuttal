

# reviewer意见

## [Review #677A](https://icse2027.hotcrp.com/review/677A)

------

### Overall merit

**3.** Weak accept

### Novelty

**3.** Substantial - presents a clearly new idea, method, result, artifact, dataset, use case, workflow, or perspective

### Rigor

**3.** Good - appropriate methods and evidence adequately support the claims

### Relevance

**3.** High - addresses an important SE problem and is likely to influence research or practice under clear assumptions

### Verifiability and Transparency

**3.** Good - Sufficient information is provided to understand the work and support verification of the main claims

### Presentation

**3.** Good - clear, well organized, and easy to follow

### Paper summary

LLM hallucination can introduce security risks in the software supply chain. This paper proposed BOUND which mitigates package hallucination by model editing. The work frames the problem as editing a “package-validity boundary,” localizes transformer modules using a gradient-based risk score contrasting hallucinated and valid packages, and injects LoRA adapters into the top-ranked modules. BOUND reduces package-level hallucination rate by 79.9% on edit prompts and by 65.4% on unseen prompts.

### Strengths

- Package hallucination is an important and concrete software engineering security problem.
- The use of Valid-NLL, hallucinated-package unlikelihood, and locality KL is well motivated, and the experiments expose an important failure mode of competing methods
- The evaluation is comprehensive and justified that the model editing does not negatively affect general coding ability.
- The proposed method is lightweight and operationally applicable.

### Weaknesses

- The concept of “package-validity boundary” is more asserted than empirically demonstrated.
- The validity metric does not measure whether a package is actually appropriate for the requested task.
- The evaluation is restricted to prompts already selected as high-risk for each model.
- The statistical evidence is weaker than the breadth of experiments suggests.

### Detailed comments for authors

# Novelty

- The strongest novelty of this work is the application-specific formulation and integration rather than a fundamentally new editing primitive. Gradient-based module localization, LoRA, NLL supervision, unlikelihood training, and KL locality constraints are individually established techniques; the contribution is in combining and adapting them specifically to package hallucination.
- The distinction from conventional factual model editing is convincing. Package recommendation does not correspond naturally to rewriting one subject-object fact, because multiple valid and invalid package names can coexist and the desired output is not a single fixed target.
- However, the paper should provide stronger evidence for the proposed “package-validity boundary” interpretation. For example, an analysis of representations or package-score separation before and after editing could demonstrate that BOUND actually sharpens a validity boundary rather than simply learning a task-specific suppression objective.

# Rigor

- A key missing baseline is an agentic/tool-augmented LLM that verifies candidate packages against PyPI before producing the final response. Since BOUND is motivated partly by avoiding external retrieval and additional inference-time complexity, directly comparing its accuracy and efficiency with such a practical validation pipeline would substantially strengthen the claim that model editing is advantageous.
- The ablation study is informative and supports the importance of the major components. In particular, removing Valid-NLL causes a collapse in valid-package generation, while removing hallucination unlikelihood or locality KL substantially increases hallucination rates, demonstrating that the objectives play complementary roles.
- BOUND evaluates a next-token logit vector at the beginning of the answer and maps complete package strings into token-level candidate sets, but the manuscript does not make sufficiently clear how multi-token names, shared prefixes, or tokenizer collisions are handled in the risk score.

# Relevance

- The work is highly relevant to software engineering and especially to secure LLM-assisted development. Dependency recommendations are actionable outputs that can directly enter package managers or agent workflows, so improving their reliability has clear practical significance.

# Verifiability and Transparency

- The paper provides substantial implementation details and released the dataset and code in the replication package.
- The package-validity procedure is reproducible but has important edge cases that deserve clarification. The paper should explain how it handles renamed packages, aliases, namespace packages, packages whose import name differs from their PyPI distribution name, and packages released after the model-specific knowledge cutoff.

# Presentation

- Overall, the paper is clear, well organized, and easy to follow. The motivating example and system overview communicate the intuition effectively, while the tables clearly expose the trade-off between reducing hallucinations and simply suppressing package generation.

### Questions for authors’ response

1. Could a tool-augmented or agentic LLM that verifies package names against PyPI achieve comparable or better hallucination mitigation? Please justify the need for model editing and explain what advantages BOUND offers over such a validation-based approach.
2. How does BOUND ensure that reductions in Package-HR correspond to better package recommendations rather than merely replacing nonexistent packages with real but task-irrelevant packages?
3. How are multi-token package names handled in the localization risk score?

## [Review #677B](https://icse2027.hotcrp.com/review/677B)

------

### Overall merit

**2.** Weak reject

### Novelty

**2.** Incremental - modest extension, adaptation, combination, or improvement

### Rigor

**3.** Good - appropriate methods and evidence adequately support the claims

### Relevance

**3.** High - addresses an important SE problem and is likely to influence research or practice under clear assumptions

### Verifiability and Transparency

**3.** Good - Sufficient information is provided to understand the work and support verification of the main claims

### Presentation

**3.** Good - clear, well organized, and easy to follow

### Paper summary

The paper targets package hallucination, the tendency of LLMs to recommend package names that do not exist. Instead of treating this as factual rewriting, the paper frames it as an error in the model's package-validity boundary, its ability to separate packages that exist in the ecosystem from plausible non-existent names under a given task context.

BOUND proceeds in two stages. It first ranks all projection matrices, attention and MLP alike, by the sensitivity of a risk score contrasting hallucinated against valid candidate logits, and keeps the top five. It then injects LoRA adapters into those modules only, optimising a likelihood term on valid packages, an unlikelihood term on hallucinated ones, and a KL locality term against the original model.

The evaluation uses three open-source LLMs of comparable size and prompts from an existing dataset, restricted to those on which the base model hallucinates in more than half of five generations. Against five baselines, BOUND reduces Package-HR by 79.9 per cent on edit prompts and 65.4 per cent on unseen prompts, transfers to code generation and pip install recommendation, and needs 731 KB of adapters. An ablation, a cost analysis and a HumanEval check complete the evaluation.

### Strengths

S1. The introduction is very well written. It sets up the problem, separates external mitigation from internal adaptation, explains why model editing is a natural third option, and argues clearly why methods built for subject-object factual updates do not fit a setting with no explicit subject, no fixed target output, and valid and hallucinated names coexisting in the same response. A reader reaches Section III knowing exactly what is being solved and why.

S2. Section III is technically substantial and well described. The boundary framing is carried through consistently into the design: the risk score contrasts the two candidate sets instead of targeting a string, the localisation space deliberately includes attention projections rather than MLP blocks alone, and the three loss terms correspond one to one to what the edit must achieve. The ablation in Section V-C supports this design rather than merely accompanying it.

S3. The replication package is well structured and easy to understand.

### Weaknesses

W1. The evaluation only ever asks whether a recommended package exists. It says nothing about the quality or the appropriateness of the recommendation, and it never compares the recommendations against real projects. This is the central limitation of the paper.

W2. Recall is never measured, and it could be. Prompts derived from real projects would allow the authors to check whether the packages those projects actually declare are in fact recommended. A study of the long tail is also needed: recommending pandas or numpy is not the same problem as recommending a less well known library, and only the second case carries real risk.

W3. RQ2, which supports the cross-task generalisation claim, rests on two unverified steps: a mapping from imports to package names delegated to an unedited model that is itself prone to package hallucination, and generated code that is never compiled or checked.

W4. It is not clear in what sense the code generation task differs from the package recommendation task, and no prompt template is given for any of the three tasks.

W5. The prompt dataset is synthetic, restricted to the head of the popularity distribution, and anchored to 2023. The choice of the three evaluated models is not motivated.

W6. The HumanEval material in the discussion does not provide any evidences.

### Detailed comments for authors

## Novelty

Framing package hallucination as a boundary problem rather than a factual rewriting problem is a useful and well-motivated perspective. At the same time, I would characterise the main novelty of the work as primarily engineering-oriented rather than conceptual. As the authors themselves show, the proposed method builds on and improves over existing model-editing techniques, adapting them effectively to the specific dependency recommendation. The paper never positions its contribution within the larger production chain it belongs to. Preventing a non-existent dependency from being suggested is one link in a longer sequence that ends with code that a developer accepts, integrates and maintains. Making that placement explicit in the introduction would help the reader calibrate the contribution, and would cost a paragraph.

## Rigor

This is where my recommendation is decided.

A package counts as valid if it is on PyPI with at least one release before the model's knowledge cutoff. The authors are candid about this, i.e.,"does not imply that the package is semantically correct for the given task", but the consequences are not drawn. No notion of how good, how appropriate, how maintained or how commonly used the recommended dependency is enters the evaluation at any point. The paper therefore demonstrates that BOUND suppresses names that do not exist, which is a narrower claim than the one the framing invites, namely that it improves the reliability of package-related outputs.

**The three metrics can be satisfied by a degenerate answer.** Package-HR is the share of hallucinated names among those extracted, Sample-HR flags answers containing at least one hallucinated name, and Valid-Rate flags answers containing at least one existing package. A model that answered `requests` to every prompt would score Package-HR 0, Sample-HR 0 and Valid-Rate 1, a perfect result on all three while being useless. Valid-Rate was introduced, correctly, to catch methods that reduce hallucination by suppressing package output, and it does catch the extreme cases visible in Tables II and III. It does not separate suppression from generic answering.

**There is a precision but no recall.** Package-HR is exactly the complement of precision. Valid-Rate is a hit rate, not a recall, because recall would require the set of packages the task actually called for, and that set does not exist anywhere in the evaluation. This is not a missing metric but a consequence of the missing notion of task-appropriate package. What makes this correctable, and what leads me to weak reject rather than reject, is that the ground truth is already there. In the dataset each prompt of the LLM-generated subset is produced by asking a model to write a coding prompt from the PyPI description of one specific package, so every prompt has an originating package attached. Retaining that link would give a reference point against which recommendations could be scored, and a recall alongside the precision.

**validation** Two further routes would strengthen the paper considerably, and I would encourage the author to consider at least one of them. The first is a user study supporting the usefulness of the recommendations. The second, which I think is the stronger option, is an experiment on real client projects: take existing projects, derive prompts from their specifications or requirements, and check whether the recommended packages match the dependencies those projects actually declare. The dependency manifest supplies the missing ground truth, and this would allow the quality and the pertinence of the recommended dependencies to be measured rather than assumed.

**The RQ2 pipeline contains two unverified steps.** In Section V-B the edited model generates Python code, the import statements are extracted, and the imported module names are mapped to PyPI package names using "the corresponding unedited base model". Metrics are then computed on the mapper's output. The mapper is precisely the model that was selected into the high-risk pool because it hallucinates package names in more than half of its generations. If it invents a name, the hallucination is charged to the edited model; if it normalises towards popular names, the bias runs the other way. Either way the RQ2 numbers include a component that is never validated, and neither the mapping prompt nor any accuracy figure for the mapping is reported. This is avoidable: the Python standard library exposes the module to distribution mapping through `importlib.metadata.packages_distributions()`, and tooling that derives a project's dependencies from its imports is widely available. There is no technical reason to place a language model in this position, and the paper gives none.

The second step is that the generated code is never compiled, executed or syntax checked. Only the imports are extracted from it. As a result, if editing degraded the ability to produce working code while leaving plausible import statements in place, the RQ2 metrics would still improve. What Section V-B calls code generation is, operationally, the presence of import statements. A syntax check with `ast.parse` would cost nothing and would close this. HumanEval in Section VI-B does not cover it, since it runs on different prompts and serves a different purpose.

**The HumanEval material adds noise.** HumanEval appears in the discussion without being introduced: what the benchmark measures, how it was run, and how the reported figures were validated are never explained. As it stands it reads as an aside rather than as evidence, and the reader cannot tell what the numbers establish. Either present it properly or drop it.

**The prompt dataset carries three properties that the paper does not discuss.** The subset used is the LLM-generated one from [12], built by taking the five thousand most downloaded Python packages, scraping their PyPI descriptions and asking Llama-2 70B to generate a coding prompt from each; the "recent" split consists of the packages most downloaded in 2023. The prompts are therefore synthetic rather than drawn from real projects or real developer questions; the prompt space sits entirely at the head of the popularity distribution, so the long tail, where plausible non-existent names are hardest to tell apart and where the risk is concentrated, is excluded by construction; and 2023 material is used to edit models released in 2024 and 2025 under a validity criterion tied to each model's own cutoff. This does not invalidate the results, but it bounds them, and the bound belongs in the paper. Look at

**The choice of models is not motivated.** Section IV-D lists the three models without saying why these three, and Section VI-C only explains the preference for open-source over commercial models, which is a different question. All three sit in the same 6.7 to 8 billion parameter range, so the evaluation says nothing about behaviour at other scales, although the reported hardware would allow larger models. A short justification, and ideally one model outside this band, would help.

## Relevance

The problem is real and the security framing is sound. An LLM that suggests a dependency name that does not exist creates an opening that has already been documented, and mitigating it inside the model rather than around it is a reasonable thing to want.

That said, the scope is narrow. The paper solves the question of whether a name exists, and only that question. Engineering-wise the pipeline is interesting and clearly the product of careful work, but the application domain is limited, and the paper does not help the reader see how this improvement sits within a larger production chain. I would ask the authors to make that argument explicitly in the introduction: what happens downstream of a correct package name, and what fraction of the problem this link actually covers. Taken together with the points under Rigor, an assessment of the quality of the generated code, and of its minimal conformance to the user stories or the questions being analysed, would do more for the relevance of this work than further gains on the existing metrics.

## Verifiability and Transparency

The replication package is available, well organised and easy to follow.

## Presentation

The introduction is the strongest part of the paper. Section II is not at the same level, and since it introduces the central construct, this matters more than its length suggests.

P1. Figure 1 is not legible. The prompt box and the twelve package labels are set too small for a single-column figure. There is also a mismatch with the text: Section I states that the boundary is represented by the dashed separation line in Figure 1, whereas the figure shows two closed dashed regions, one green and one red, plus a separate label box.

P2. ECMWF is used as the motivating example but is never expanded or placed in a domain. A reader who does not know the organisation loses the example at exactly the point where the central construct is being introduced. One line of explanation would be enough. The example does not explain why some of the packages shown matter and others do not. Among the valid packages, `iris` and `xarray` are the domain's data handling stack, while `requests`, `cffi` and `xmltodict` are generic and have nothing specific to do with the task; on the hallucinated side, nothing indicates why `ecmwftools`, `ecmwfr`, `pycdox`, `pyeawr` and `pyecmw` are plausible, e.g., ecwfr exists https://bluegreen-labs.github.io/ecmwfr/. I recognise the space constraints, but one or two sentences would make the example do its work. This also connects to the distinction the authors themselves draw in Section IV-C, between existing and being appropriate for the task, which the figure flattens.

P4. Terminology should be checked for consistency. Package, library, dependency and module are used with some interchange. The one that matters is module, which carries two incompatible senses in the same paper: the transformer projection matrices that are the target of the edit, as in key module localisation and localised module set, and Python modules that are imported, as in extract the import modules. The weaker transfer to code generation is attributed to hallucinated module imports, in a paper whose mechanism is editing modules. This is not only cosmetic: in Python the import name and the distribution name often differ, and that difference is the one the RQ2 mapping step has to bridge.

P6. Consider renaming the metrics into standard terms. Package-HR is the complement of precision and could be reported as precision directly. The complement of Sample-HR is a success rate at the answer level. Valid-Rate would be better named a hit rate, so that readers do not take it for a recall the evaluation cannot compute.

### Questions for authors’ response

Q1. What exactly are the code generation prompts, and how do they differ from the package recommendation prompts?

Q2. Is the generated code checked for syntactic validity at any point?

Q3. Was the link between each prompt and the package whose description generated it retained? If so, why is it not used to assess whether the recommendations are appropriate?

## [Review #677C](https://icse2027.hotcrp.com/review/677C)

------

### Overall merit

**2.** Weak reject

### Novelty

**2.** Incremental - modest extension, adaptation, combination, or improvement

### Rigor

**2.** Fair - some weaknesses, but the main claims are at least partially supported

### Relevance

**1.** Limited - addresses a narrow or weakly motivated problem with limited expected impact

### Verifiability and Transparency

**3.** Good - Sufficient information is provided to understand the work and support verification of the main claims

### Presentation

**3.** Good - clear, well organized, and easy to follow

### Paper summary

This paper presents BOUND, a localized model-editing approach for package hallucination. BOUND constructs a risk signal from the logit difference between tokens associated with hallucinated and registry-existing package names, uses gradient-times-weight saliency to identify the attention/MLP modules most associated with this risk, and applies LoRA updates only to the highest-ranked modules. Its objective increases the likelihood of registry-existing packages, applies an unlikelihood loss to hallucinated packages, and uses a KL locality loss to preserve behavior on unrelated inputs. Experiments on DeepSeek-Coder-6.7B-Instruct, Qwen3-8B, and Llama-3.1-8B-Instruct report average reductions of approximately 65.4% in unseen Package-HR and 63.7% in unseen Sample-HR on model-specific, preselected high-risk prompts, with small changes on HumanEval.

### Strengths

- Package hallucination has concrete reliability and supply-chain implications because nonexistent dependencies cause installation failure and may create opportunities for malicious package registration.
- BOUND provides a persistent, internal intervention that could be useful for open-weight models deployed offline, without network access, or without an enforceable external verifier.
- The direction of improvement is consistent across three models, and the evaluation includes unseen high-risk prompts, cross-task settings, generic coding benchmarks, and several loss/module ablations.

### Weaknesses

- The paper evaluates tool-free 6.7B/8B open models but makes broader claims about current AI coding tools. Modern coding agents can query PyPI/npm/Cargo registries before accepting a dependency, so the intended deployment threat model is underspecified.
- PackMonitor already addresses the same package-hallucination problem through registry-aware constrained decoding, while CREME uses a closely related layer-aware code-model editing framework. The lack of adequate comparison makes the current novelty claim too strong.
- The test sets are selected by retaining prompts for which the base model has Sample-HR greater than 0.5. This is a useful stress test, but it cannot estimate prevalence or deployment benefit on the natural request distribution.
- “Valid” means only that a package name existed on PyPI before the cutoff. It does not establish relevance, installability, importability, API correctness, compatibility, or safety, so the main metrics measure registry existence rather than dependency correctness.
- The localization ablation is primarily against random modules. This does not demonstrate that a package-validity boundary exists or that localization outperforms ordinary LoRA, all-module LoRA, or established layer-localization methods.

### Detailed comments for authors

**Novelty.** BOUND's package-specific risk score and its combination of valid-package likelihood, hallucinated-package unlikelihood, and locality loss for top-module LoRA editing provide a task-specific technical increment. However, the paper currently presents this increment as more independent from prior work than the evidence supports. PackMonitor (ISSTA 2026) already targets the same failure using an authoritative registry, package-name parsing, and constrained decoding; it directly occupies the problem-solution space of preventing nonexistent package names, and could be treated as a primary baseline. CREME (ICSE 2026) already proposes layer-aware localization and lightweight editing for failures of code models, while DINM, TruthX, and RaLFiT respectively contain closely related ideas in target-layer localization, editing truthfulness/hallucination representations, or allocating LoRA capacity by module. I therefore view BOUND's exact objective as potentially new, but the overall method as an adaptation of an established localization-and-editing pattern.

**Rigor.** The consistent and sizable reductions across three models show that BOUND changes the targeted output distribution, but the current evaluation does not support broad deployment claims. First, each prompt is sampled five times and only prompts with base-model Sample-HR>0.5 are retained. The resulting test set is therefore, by construction, a conditional distribution on frequent base-model failure. Second, each model uses its own risk and editing sets, which weakens direct cross-model comparison; a common prompt set and cross-evaluation on other models' risk sets would help. Third, PyPI existence is an inadequate correctness construct. Installability, import-name agreement, API existence, version/platform compatibility, task-semantic suitability, and end-to-end execution should be measured separately. Valid-Rate requires only one existing package and can improve if the model inserts an irrelevant but common dependency. Finally, **all evaluated models are tool-free 6.7B/8B systems**. The evaluation **should include stronger recent models and an actual agentic setting**, with mandatory registry checking, a post-hoc verifier, RAG, PackMonitor, and BOUND-plus-verifier as baselines. Without these experiments, the supported claim is limited to preselected high-risk prompts for small, tool-free models.

**Relevance.** The underlying failure has not disappeared, however, in a modern agentic workflow, package existence is no longer merely an open-ended prediction problem that must be solved inside model parameters. It is a low-cost, decidable constraint that can be checked against an authoritative registry and enforced before writing requirements.txt/pyproject.toml or running an installer, rather than leaving tool use to the model's discretion. The paper neither evaluates this common systems design nor clearly states whether BOUND targets offline/on-device deployment, latency-sensitive autocomplete, network-restricted sandboxes, or defense in depth. The practical case would be stronger if the claims were narrowed to open-weight deployments where online registry access or constrained decoding is unavailable, and if BOUND were positioned as a complement to external verification rather than a replacement. As written, extrapolation to modern coding agents overstates the likely impact.

**Verifiability & transparency.** The public Zenodo artifact is clear, and the paper reports the main objectives, training settings, and several ablations.

**Presentation.** The paper is generally well organized, and easy to follow.

### Artifact assessment

**3.** Satisfactory, i.e., the artifacts are in line with what is declared in the submission form or the paper [OR] the authors explained why the artifacts are not provided and I find the explanation to be reasonable.

### Comments on artifact assessment

The declared Zenodo artifact is publicly accessible, contains BOUND.zip, and provides an open license. Following the review-form instruction, I assessed availability only and did not execute the code. Public availability is a strength, although full verification of the main claims requires the prompt-selection traces, registry snapshot, complete generations, and statistical scripts discussed above.

### Questions for authors’ response

1. What is BOUND's intended deployment setting? Can you compare it with mandatory PyPI verification, post-hoc registry filtering, and PackMonitor on the same models, prompts, and latency/compute budget, and quantify what additional benefit editing provides when an agent can be required to call a registry tool?
2. On a natural prompt set without filtering for base-model Sample-HR>0.5, what are the initial hallucination rates and BOUND's absolute benefits? Please report events per thousand generations, confidence intervals, refusal rates, and, if possible, results for a stronger recent model or a tool-using agent.
3. Relative to ordinary/no-localization LoRA, all-module LoRA, CREME/DINM-style localization, and alternative saliency methods, what does the proposed risk score and top-module localization contribute independently? Is there direct evidence that the selected modules represent a stable package-validity “boundary,” rather than simply having large gradients for the current loss?
4. Do the gains remain when correctness requires successful installation and import, valid APIs/versions, semantic suitability, and end-to-end execution? On prompts where the base model originally selected a correct dependency, does BOUND increase replacement errors, over-refusal, or systematic rejection of legitimate packages released after the cutoff?