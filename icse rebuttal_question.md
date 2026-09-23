### Response #677A

1. **[Q1-Tool-Augmented Benchmark]**

   **Q:** Could a tool-augmented or agentic LLM that verifies package names against PyPI achieve comparable or better hallucination mitigation? Please justify the need for model editing and explain what advantages BOUND offers over such a validation-based approach.

   A key missing baseline is an agentic/tool-augmented LLM that verifies candidate packages against PyPI before producing the final response. Since BOUND is motivated partly by avoiding external retrieval and additional inference-time complexity, directly comparing its accuracy and efficiency with such a practical validation pipeline would substantially strengthen the claim that model editing is advantageous.

   通过查询 PyPI 验证包名的工具增强或智能体式 LLM，能否实现相当或更好的包幻觉缓解效果？请论证模型编辑的必要性，并说明 BOUND 相比这种基于验证的方法有哪些优势。

   缺少的一个关键基线是工具增强或智能体式 LLM：它在生成最终回答之前，对照 PyPI 验证候选包。BOUND 的动机之一是避免外部检索和额外的推理时复杂性，因此，直接比较 BOUND 与这种实际验证流程的准确性和效率，将显著增强模型编辑具有优势的论证。

2. **[Q2-Task Relevance of Recommended Packages]**

   **Q:** How does BOUND ensure that reductions in Package-HR correspond to better package recommendations rather than merely replacing nonexistent packages with real but task-irrelevant packages?

   BOUND 如何确保 Package-HR 的降低意味着包推荐质量得到改善，而不只是把不存在的包替换成真实存在但与任务无关的包？

3. **[Q3-Multi-token Package Names in Localization]**

   **Q:** How are multi-token package names handled in the localization risk score?

   BOUND evaluates a next-token logit vector at the beginning of the answer and maps complete package strings into token-level candidate sets, but the manuscript does not make sufficiently clear how multi-token names, shared prefixes, or tokenizer collisions are handled in the risk score.

   定位风险评分如何处理由多个 token 构成的包名？

   BOUND 在回答开头计算 next-token logit 向量，并将完整包名字符串映射为 token 级候选集合，但论文没有充分说明风险评分如何处理多 token 包名、共享前缀或分词器造成的 token 碰撞。

4. **[Other-Evidence for the Package-Validity Boundary]**

   However, the paper should provide stronger evidence for the proposed “package-validity boundary” interpretation. For example, an analysis of representations or package-score separation before and after editing could demonstrate that BOUND actually sharpens a validity boundary rather than simply learning a task-specific suppression objective.

   不过，论文应为提出的“包有效性边界”解释提供更有力的证据。例如，分析编辑前后的表征或有效包与幻觉包的分数分离情况，可以展示 BOUND 是否确实使有效性边界更清晰，而不只是学到了针对特定任务的抑制目标。

5. **[Other-Edge Cases in Package Validity Checking]**

   The package-validity procedure is reproducible but has important edge cases that deserve clarification. The paper should explain how it handles renamed packages, aliases, namespace packages, packages whose import name differs from their PyPI distribution name, and packages released after the model-specific knowledge cutoff.

   包有效性检查流程可以复现，但其中有一些重要边界情况值得澄清。论文应解释如何处理重命名的包、别名、命名空间包、导入名与 PyPI 发行包名不同的包，以及在各模型的知识截止日期之后发布的包。

6. **[Other-Evaluation on High-Risk Prompts]**

   The evaluation is restricted to prompts already selected as high-risk for each model.

   评测仅限于已经针对各模型筛选出的高风险提示。

7. **[Other-Statistical Evidence and Result Stability]**

   The statistical evidence is weaker than the breadth of experiments suggests.

   统计证据的充分程度弱于实验覆盖广度所给人的印象。

8. **[Other-Novelty of the Formulation and Integration]**

   The strongest novelty of this work is the application-specific formulation and integration rather than a fundamentally new editing primitive. Gradient-based module localization, LoRA, NLL supervision, unlikelihood training, and KL locality constraints are individually established techniques; the contribution is in combining and adapting them specifically to package hallucination.

   这项工作最突出的创新在于面向特定应用的问题建模与技术整合，而不是提出了根本性的新编辑操作。基于梯度的模块定位、LoRA、NLL 监督、反似然训练和 KL 局部性约束分别都是已有技术；本文的贡献在于专门针对包幻觉组合并适配这些技术。

### Response #677B

1. **[Q1-Code Generation Prompts and Task Differences]**

   **Q:** What exactly are the code generation prompts, and how do they differ from the package recommendation prompts?

   W4. It is not clear in what sense the code generation task differs from the package recommendation task, and no prompt template is given for any of the three tasks.

   代码生成任务的提示具体是什么？它们与包推荐任务的提示有何区别？

   W4. 不清楚代码生成任务与包推荐任务究竟有何不同，而且三种任务都没有提供提示模板。

2. **[Q2-Syntactic Validity and Generated Code Quality]**

   **Q:** Is the generated code checked for syntactic validity at any point?

   The second step is that the generated code is never compiled, executed or syntax checked. Only the imports are extracted from it. As a result, if editing degraded the ability to produce working code while leaving plausible import statements in place, the RQ2 metrics would still improve. What Section V-B calls code generation is, operationally, the presence of import statements. A syntax check with `ast.parse` would cost nothing and would close this. HumanEval in Section VI-B does not cover it, since it runs on different prompts and serves a different purpose.

   是否在任何阶段检查了生成代码的语法有效性？

   第二个未经验证的步骤是：生成代码从未经过编译、执行或语法检查，只从中提取了 import。因此，即使编辑削弱了生成可工作代码的能力，只要 import 语句看起来合理，RQ2 的指标仍可能改善。第 V-B 节所称的代码生成，在实际评测中仅体现为是否出现 import 语句。使用 ast.parse 进行语法检查几乎没有成本，可以补上这一缺口。第 VI-B 节中的 HumanEval 不能覆盖这个问题，因为它使用不同的提示，服务于不同的评测目的。

3. **[Q3-Evaluation of Package Recommendation Effectiveness]**

   **Q:** Was the link between each prompt and the package whose description generated it retained? If so, why is it not used to assess whether the recommendations are appropriate?

   A package counts as valid if it is on PyPI with at least one release before the model's knowledge cutoff. The authors are candid about this, i.e.,"does not imply that the package is semantically correct for the given task", but the consequences are not drawn. No notion of how good, how appropriate, how maintained or how commonly used the recommended dependency is enters the evaluation at any point. The paper therefore demonstrates that BOUND suppresses names that do not exist, which is a narrower claim than the one the framing invites, namely that it improves the reliability of package-related outputs.

   **The three metrics can be satisfied by a degenerate answer.** Package-HR is the share of hallucinated names among those extracted, Sample-HR flags answers containing at least one hallucinated name, and Valid-Rate flags answers containing at least one existing package. A model that answered `requests` to every prompt would score Package-HR 0, Sample-HR 0 and Valid-Rate 1, a perfect result on all three while being useless. Valid-Rate was introduced, correctly, to catch methods that reduce hallucination by suppressing package output, and it does catch the extreme cases visible in Tables II and III. It does not separate suppression from generic answering.

   **There is a precision but no recall.** Package-HR is exactly the complement of precision. Valid-Rate is a hit rate, not a recall, because recall would require the set of packages the task actually called for, and that set does not exist anywhere in the evaluation. This is not a missing metric but a consequence of the missing notion of task-appropriate package. What makes this correctable, and what leads me to weak reject rather than reject, is that the ground truth is already there. In the dataset each prompt of the LLM-generated subset is produced by asking a model to write a coding prompt from the PyPI description of one specific package, so every prompt has an originating package attached. Retaining that link would give a reference point against which recommendations could be scored, and a recall alongside the precision.

   是否保留了每条提示与用于生成该提示的包描述所属包之间的对应关系？如果保留了，为什么不利用它来评估推荐是否适合任务？

   只要包存在于 PyPI，且至少有一个版本在模型知识截止日期之前发布，就会被判定为有效。作者坦诚说明这“并不意味着该包在语义上适合给定任务”，但没有进一步讨论这一点的后果。推荐依赖的质量、适用性、维护状况和使用普遍程度，从未进入评测。因此，论文证明的是 BOUND 能抑制不存在的包名；这一结论比论文整体表述所暗示的“提高包相关输出的可靠性”更窄。

   **三个指标都可以被退化回答满足。** Package-HR 是提取出的包名中幻觉包名的比例；Sample-HR 标记至少包含一个幻觉包名的回答；Valid-Rate 标记至少包含一个真实包的回答。一个对所有提示都回答 requests 的模型，会得到 Package-HR 为 0、Sample-HR 为 0、Valid-Rate 为 1，即三个指标全部完美，却毫无用处。引入 Valid-Rate 来识别依靠抑制包输出降低幻觉的方法是正确的，它也确实识别出了表 II 和表 III 中的极端情况。但它无法区分抑制包输出与泛化的通用回答。

   **有精确率，却没有召回率。** Package-HR 恰好是精确率的补数。Valid-Rate 是命中率，而不是召回率，因为计算召回率需要知道任务实际需要哪些包，但评测中没有这样的集合。这并非仅仅缺少一个指标，而是缺少“适合任务的包”这一概念的结果。这个问题可以修正，也是我给出弱拒而非拒稿的原因：真值已经存在。在数据集的 LLM 生成子集中，每条提示都是让模型根据某个特定包的 PyPI 描述生成的，因此每条提示都有对应的来源包。保留这一关联，就能提供一个评价推荐的参照，并在精确率之外计算召回率。

4. **[Other-Validation through Real Projects or a User Study]**

   **validation** Two further routes would strengthen the paper considerably, and I would encourage the author to consider at least one of them. The first is a user study supporting the usefulness of the recommendations. The second, which I think is the stronger option, is an experiment on real client projects: take existing projects, derive prompts from their specifications or requirements, and check whether the recommended packages match the dependencies those projects actually declare. The dependency manifest supplies the missing ground truth, and this would allow the quality and the pertinence of the recommended dependencies to be measured rather than assumed.

   **验证。** 还有两种方式可以显著增强论文，我建议作者至少考虑其中一种。第一种是开展支持推荐有用性的用户研究。第二种在我看来更有说服力：在实际使用这些依赖的项目上开展实验，根据项目规格或需求生成提示，然后检查推荐包是否与这些项目实际声明的依赖相匹配。依赖清单可以提供目前缺失的真值，使推荐依赖的质量和相关性得到测量，而不是被直接假定。

5. **[Other-Reliability of Import-to-Package Mapping]**

   **The RQ2 pipeline contains two unverified steps.** In Section V-B the edited model generates Python code, the import statements are extracted, and the imported module names are mapped to PyPI package names using "the corresponding unedited base model". Metrics are then computed on the mapper's output. The mapper is precisely the model that was selected into the high-risk pool because it hallucinates package names in more than half of its generations. If it invents a name, the hallucination is charged to the edited model; if it normalises towards popular names, the bias runs the other way. Either way the RQ2 numbers include a component that is never validated, and neither the mapping prompt nor any accuracy figure for the mapping is reported. This is avoidable: the Python standard library exposes the module to distribution mapping through `importlib.metadata.packages_distributions()`, and tooling that derives a project's dependencies from its imports is widely available. There is no technical reason to place a language model in this position, and the paper gives none.

   **RQ2 流程包含两个未经验证的步骤。** 在第 V-B 节中，编辑后的模型生成 Python 代码，随后提取 import 语句，并使用“对应的未编辑基模”将导入模块名映射到 PyPI 包名。指标在映射器的输出上计算。这个映射器恰好就是因超过一半生成结果包含包幻觉而用于筛选高风险提示的模型。如果它编造包名，幻觉会被计到编辑后的模型头上；如果它倾向于将名称规范化为热门包名，偏差则相反。无论哪种情况，RQ2 的结果都包含一个从未验证的组成部分，而且没有报告映射提示或映射准确率。这是可以避免的：Python 标准库通过 importlib.metadata.packages_distributions() 提供模块到发行包的映射，也已有大量工具能根据项目 imports 推导依赖。没有技术上的理由必须在这里使用语言模型，论文也未给出理由。

6. **[Other-HumanEval Setup and Evidential Value]**

   **The HumanEval material adds noise.** HumanEval appears in the discussion without being introduced: what the benchmark measures, how it was run, and how the reported figures were validated are never explained. As it stands it reads as an aside rather than as evidence, and the reader cannot tell what the numbers establish. Either present it properly or drop it.

   **HumanEval 材料增加了噪声。** HumanEval 在讨论部分出现，却没有得到介绍：它测量什么、如何运行，以及报告的数值如何验证，都没有说明。目前它更像旁注，而非证据，读者无法判断这些数字能说明什么。应当完整呈现这项评测，或者将其删除。

7. **[Other-Synthetic Prompts, Popularity Bias, and Temporal Scope]**

   W2. Recall is never measured, and it could be. Prompts derived from real projects would allow the authors to check whether the packages those projects actually declare are in fact recommended. A study of the long tail is also needed: recommending pandas or numpy is not the same problem as recommending a less well known library, and only the second case carries real risk.

   **The prompt dataset carries three properties that the paper does not discuss.** The subset used is the LLM-generated one from [12], built by taking the five thousand most downloaded Python packages, scraping their PyPI descriptions and asking Llama-2 70B to generate a coding prompt from each; the "recent" split consists of the packages most downloaded in 2023. The prompts are therefore synthetic rather than drawn from real projects or real developer questions; the prompt space sits entirely at the head of the popularity distribution, so the long tail, where plausible non-existent names are hardest to tell apart and where the risk is concentrated, is excluded by construction; and 2023 material is used to edit models released in 2024 and 2025 under a validity criterion tied to each model's own cutoff. This does not invalidate the results, but it bounds them, and the bound belongs in the paper. Look at

   W2. 没有测量召回率，但实际上可以测量。根据真实项目构造提示，可以检查这些项目实际声明的包是否被推荐。还需要研究长尾包：推荐 pandas 或 numpy 与推荐不那么知名的库不是同一个问题，只有后者才涉及真正的风险。

   **提示数据集有三个未被论文讨论的特征。** 使用的是文献 [12] 的 LLM 生成子集：选取下载量最高的五千个 Python 包，抓取其 PyPI 描述，再让 Llama-2 70B 为每个包生成一条编码提示；其中“recent”划分包含 2023 年下载量最高的包。因此，提示是合成的，并非来自真实项目或开发者问题；提示空间完全处于热门包分布的头部，而那些看似合理的不存在包名最难区分、风险最集中的长尾部分，在构造时就被排除了；此外，作者用 2023 年的材料编辑 2024 年和 2025 年发布的模型，同时采用与各模型自身截止日期绑定的有效性标准。这并不使结果失效，但限定了结果的适用范围，论文应明确说明这一范围。［原文末尾为未完成短语“Look at”。］

8. **[Other-Model Selection and Model Scale]**

   **The choice of models is not motivated.** Section IV-D lists the three models without saying why these three, and Section VI-C only explains the preference for open-source over commercial models, which is a different question. All three sit in the same 6.7 to 8 billion parameter range, so the evaluation says nothing about behaviour at other scales, although the reported hardware would allow larger models. A short justification, and ideally one model outside this band, would help.

   **模型选择缺少理由。** 第 IV-D 节列出了三个模型，却没有说明为什么选择它们；第 VI-C 节只解释了为何偏好开源模型而不是商业模型，这是另一个问题。三个模型都处于 6.7B 至 8B 参数范围，因此评测无法说明其他规模下的行为，尽管报告的硬件可以运行更大的模型。补充简要理由会有帮助，最好再增加一个该规模区间之外的模型。

9. **[Other-Engineering-Oriented Novelty]**

   Framing package hallucination as a boundary problem rather than a factual rewriting problem is a useful and well-motivated perspective. At the same time, I would characterise the main novelty of the work as primarily engineering-oriented rather than conceptual. As the authors themselves show, the proposed method builds on and improves over existing model-editing techniques, adapting them effectively to the specific dependency recommendation.

   将包幻觉建模为边界问题，而不是事实重写问题，是一个有用且动机充分的视角。与此同时，我认为这项工作的主要创新偏向工程层面，而非概念层面。正如作者所展示的，所提方法建立在已有模型编辑技术之上，对其进行改进，并有效适配到特定的依赖推荐场景。

10. **[Other-Position in the Development Workflow and Scope of Claims]**

   The paper never positions its contribution within the larger production chain it belongs to. Preventing a non-existent dependency from being suggested is one link in a longer sequence that ends with code that a developer accepts, integrates and maintains. Making that placement explicit in the introduction would help the reader calibrate the contribution, and would cost a paragraph.

   That said, the scope is narrow. The paper solves the question of whether a name exists, and only that question. Engineering-wise the pipeline is interesting and clearly the product of careful work, but the application domain is limited, and the paper does not help the reader see how this improvement sits within a larger production chain. I would ask the authors to make that argument explicitly in the introduction: what happens downstream of a correct package name, and what fraction of the problem this link actually covers. Taken together with the points under Rigor, an assessment of the quality of the generated code, and of its minimal conformance to the user stories or the questions being analysed, would do more for the relevance of this work than further gains on the existing metrics.

   论文从未说明这项贡献在更大生产流程中的位置。避免推荐不存在的依赖，只是更长流程中的一环；该流程最终要产出开发者愿意接受、集成和维护的代码。在引言中明确这一位置，有助于读者准确理解贡献，而且只需增加一段文字。

   不过，研究范围较窄。论文只解决包名是否存在这一问题。从工程角度看，流程有意思，显然经过认真设计，但应用范围有限，也没有帮助读者理解这项改进如何融入更大的生产流程。我希望作者在引言中明确说明：得到正确包名之后还会发生什么，这一环节覆盖了整体问题的多大部分。结合严谨性部分的意见，评估生成代码的质量及其对用户故事或所分析问题的最低程度符合情况，会比在现有指标上取得进一步提升，更能增强工作的相关性。

11. **[Other-Figure 1 Readability and Consistency]**

   P1. Figure 1 is not legible. The prompt box and the twelve package labels are set too small for a single-column figure. There is also a mismatch with the text: Section I states that the boundary is represented by the dashed separation line in Figure 1, whereas the figure shows two closed dashed regions, one green and one red, plus a separate label box.

   P1. 图 1 难以辨认。作为单栏图，提示框和十二个包名标签的字号太小。此外，图与正文不一致：第 I 节称图 1 中的虚线分隔线表示边界，但图中展示的是两个闭合虚线区域，一个绿色、一个红色，以及一个单独的标签框。

12. **[Other-ECMWF Motivating Example and Package Explanations]**

   P2. ECMWF is used as the motivating example but is never expanded or placed in a domain. A reader who does not know the organisation loses the example at exactly the point where the central construct is being introduced. One line of explanation would be enough. The example does not explain why some of the packages shown matter and others do not. Among the valid packages, `iris` and `xarray` are the domain's data handling stack, while `requests`, `cffi` and `xmltodict` are generic and have nothing specific to do with the task; on the hallucinated side, nothing indicates why `ecmwftools`, `ecmwfr`, `pycdox`, `pyeawr` and `pyecmw` are plausible, e.g., ecwfr exists https://bluegreen-labs.github.io/ecmwfr/. I recognise the space constraints, but one or two sentences would make the example do its work. This also connects to the distinction the authors themselves draw in Section IV-C, between existing and being appropriate for the task, which the figure flattens.

   P2. ECMWF 被用作动机示例，但没有展开缩写或说明所属领域。不了解这一机构的读者，会恰好在引入核心概念的位置无法理解例子，一行解释即可解决。例子也没有解释为什么图中的一些包与任务有关，而另一些无关。在有效包中，iris 和 xarray 属于该领域的数据处理工具，而 requests、cffi 和 xmltodict 是通用包，与该任务没有特定联系；在幻觉包一侧，也没有说明 ecmwftools、ecmwfr、pycdox、pyeawr 和 pyecmw 为什么看起来合理，例如原文指出 ecwfr 存在，并给出 https://bluegreen-labs.github.io/ecmwfr/。我理解篇幅限制，但增加一两句话就能让例子发挥作用。这也关联到作者在第 IV-C 节作出的“存在”与“适合任务”的区分，而图中淡化了这种差别。

13. **[Other-Terminology and the Two Meanings of Module]**

   P4. Terminology should be checked for consistency. Package, library, dependency and module are used with some interchange. The one that matters is module, which carries two incompatible senses in the same paper: the transformer projection matrices that are the target of the edit, as in key module localisation and localised module set, and Python modules that are imported, as in extract the import modules. The weaker transfer to code generation is attributed to hallucinated module imports, in a paper whose mechanism is editing modules. This is not only cosmetic: in Python the import name and the distribution name often differ, and that difference is the one the RQ2 mapping step has to bridge.

   P4. 应检查术语一致性。Package、library、dependency 和 module 在文中有些混用。其中 module 尤其重要，因为它在同一篇论文中有两种不同含义：一是被编辑的 transformer 投影矩阵，例如关键模块定位和定位模块集合；二是 Python 中被 import 的模块，例如提取导入模块。论文把较弱的代码生成迁移效果归因于幻觉模块导入，而方法本身又是在编辑模块。这不仅是措辞问题：在 Python 中，导入名和发行包名经常不同，而这一差别正是 RQ2 映射步骤必须跨越的。

14. **[Other-Standard Metric Names and Interpretation]**

   P6. Consider renaming the metrics into standard terms. Package-HR is the complement of precision and could be reported as precision directly. The complement of Sample-HR is a success rate at the answer level. Valid-Rate would be better named a hit rate, so that readers do not take it for a recall the evaluation cannot compute.

   P6. 建议将指标改为标准名称。Package-HR 是精确率的补数，可以直接报告精确率。Sample-HR 的补数是回答层面的成功率。Valid-Rate 更适合称为命中率，以免读者误认为它是当前评测无法计算的召回率。

### Response #677C

1. **[Q1-Deployment Setting and Registry-Verification Baselines]**

   **Q:** What is BOUND's intended deployment setting? Can you compare it with mandatory PyPI verification, post-hoc registry filtering, and PackMonitor on the same models, prompts, and latency/compute budget, and quantify what additional benefit editing provides when an agent can be required to call a registry tool?

   **Relevance.** The underlying failure has not disappeared, however, in a modern agentic workflow, package existence is no longer merely an open-ended prediction problem that must be solved inside model parameters. It is a low-cost, decidable constraint that can be checked against an authoritative registry and enforced before writing requirements.txt/pyproject.toml or running an installer, rather than leaving tool use to the model's discretion. The paper neither evaluates this common systems design nor clearly states whether BOUND targets offline/on-device deployment, latency-sensitive autocomplete, network-restricted sandboxes, or defense in depth. The practical case would be stronger if the claims were narrowed to open-weight deployments where online registry access or constrained decoding is unavailable, and if BOUND were positioned as a complement to external verification rather than a replacement. As written, extrapolation to modern coding agents overstates the likely impact.

   BOUND 面向什么部署场景？能否在相同模型、提示以及延迟/计算预算下，将其与强制 PyPI 验证、事后注册表过滤和 PackMonitor 比较，并量化当智能体可以被要求调用注册表工具时，模型编辑还能带来多少额外收益？

   **相关性。** 这一底层问题并没有消失，但在现代智能体工作流中，包是否存在已经不再只是必须依靠模型参数解决的开放式预测问题。它是一个成本低且可判定的约束，可以对照权威注册表检查，并在写入 requirements.txt/pyproject.toml 或运行安装器之前强制执行，而不是由模型自行决定是否使用工具。论文既没有评估这种常见系统设计，也没有明确 BOUND 是否面向离线/端侧部署、延迟敏感的自动补全、网络受限沙箱或纵深防御。如果把结论收窄到无法使用在线注册表或约束解码的开放权重部署，并将 BOUND 定位为外部验证的补充而非替代，其实际价值会更有说服力。现有写法将结论外推到现代编码智能体，夸大了可能的影响。

2. **[Q2-Natural Prompt Distribution and Statistical Evidence]**

   **Q:** On a natural prompt set without filtering for base-model Sample-HR>0.5, what are the initial hallucination rates and BOUND's absolute benefits? Please report events per thousand generations, confidence intervals, refusal rates, and, if possible, results for a stronger recent model or a tool-using agent.

   First, each prompt is sampled five times and only prompts with base-model Sample-HR>0.5 are retained. The resulting test set is therefore, by construction, a conditional distribution on frequent base-model failure.

   在未按基模 Sample-HR>0.5 筛选的自然提示集合上，初始幻觉率和 BOUND 的绝对收益分别是多少？请报告每千次生成的事件数量、置信区间、拒答率，并在可能的情况下报告更强的新近模型或使用工具的智能体的结果。

   首先，每条提示采样五次，只保留基模 Sample-HR>0.5 的提示。因此，测试集从构造上就是以基模频繁失败为条件的分布。

3. **[Q3-Localization Contribution and Package-Validity Boundary Evidence]**

   **Q:** Relative to ordinary/no-localization LoRA, all-module LoRA, CREME/DINM-style localization, and alternative saliency methods, what does the proposed risk score and top-module localization contribute independently? Is there direct evidence that the selected modules represent a stable package-validity “boundary,” rather than simply having large gradients for the current loss?

   The localization ablation is primarily against random modules. This does not demonstrate that a package-validity boundary exists or that localization outperforms ordinary LoRA, all-module LoRA, or established layer-localization methods.

   相较于普通/不进行定位的 LoRA、全模块 LoRA、CREME/DINM 式定位以及其他显著性评分方法，所提出的风险评分和 top-module 定位各自有什么独立贡献？是否有直接证据表明，选中的模块表示一个稳定的包有效性“边界”，而不只是对当前损失具有较大的梯度？

   定位消融主要与随机模块比较。这既不能证明包有效性边界的存在，也不能证明该定位方法优于普通 LoRA、全模块 LoRA 或已有的层定位方法。

4. **[Q4-Dependency Correctness and Editing Side Effects]**

   **Q:** Do the gains remain when correctness requires successful installation and import, valid APIs/versions, semantic suitability, and end-to-end execution? On prompts where the base model originally selected a correct dependency, does BOUND increase replacement errors, over-refusal, or systematic rejection of legitimate packages released after the cutoff?

   Third, PyPI existence is an inadequate correctness construct. Installability, import-name agreement, API existence, version/platform compatibility, task-semantic suitability, and end-to-end execution should be measured separately. Valid-Rate requires only one existing package and can improve if the model inserts an irrelevant but common dependency.

   如果正确性要求成功安装和导入、有效的 API/版本、语义适用性以及端到端执行，性能收益是否仍然存在？对于基模原本选择了正确依赖的提示，BOUND 是否会增加错误替换、过度拒答，或对知识截止日期之后发布的合法包产生系统性排斥？

   第三，PyPI 存在性不足以构成正确性的定义。可安装性、导入名一致性、API 存在性、版本/平台兼容性、任务语义适用性和端到端执行应分别测量。Valid-Rate 只要求存在一个真实包，因此模型插入一个无关但常见的依赖，也可能使该指标提高。

5. **[Other-Novelty Relative to PackMonitor and Related Editing Methods]**

   **Novelty.** BOUND's package-specific risk score and its combination of valid-package likelihood, hallucinated-package unlikelihood, and locality loss for top-module LoRA editing provide a task-specific technical increment. However, the paper currently presents this increment as more independent from prior work than the evidence supports. PackMonitor (ISSTA 2026) already targets the same failure using an authoritative registry, package-name parsing, and constrained decoding; it directly occupies the problem-solution space of preventing nonexistent package names, and could be treated as a primary baseline. CREME (ICSE 2026) already proposes layer-aware localization and lightweight editing for failures of code models, while DINM, TruthX, and RaLFiT respectively contain closely related ideas in target-layer localization, editing truthfulness/hallucination representations, or allocating LoRA capacity by module. I therefore view BOUND's exact objective as potentially new, but the overall method as an adaptation of an established localization-and-editing pattern.

   **创新性。** BOUND 面向包的风险分数，以及用于 top-module LoRA 编辑的有效包似然、幻觉包反似然和局部性损失组合，提供了针对特定任务的技术增量。但论文目前把这一增量表述得比证据所支持的更加独立于已有工作。PackMonitor（ISSTA 2026）已经利用权威注册表、包名解析和约束解码处理同一种失败；它直接处于防止不存在包名的问题与解决方案空间中，可以作为主要基线。CREME（ICSE 2026）已经针对代码模型失败提出了考虑层位置的定位与轻量编辑；DINM、TruthX 和 RaLFiT 则分别包含目标层定位、真实性/幻觉表征编辑，以及按模块分配 LoRA 容量等密切相关的思想。因此，我认为 BOUND 的具体目标函数可能有新意，但整体方法是对已有定位与编辑模式的适配。

6. **[Other-Common Prompt Sets and Cross-Model Evaluation]**

   Second, each model uses its own risk and editing sets, which weakens direct cross-model comparison; a common prompt set and cross-evaluation on other models' risk sets would help.

   第二，每个模型使用各自的高风险集合和编辑集合，这削弱了直接进行跨模型比较的有效性；使用共同提示集，并在其他模型的高风险集合上交叉评测，会有所帮助。

7. **[Other-Stronger Models and an Actual Agentic Setting]**

   Finally, **all evaluated models are tool-free 6.7B/8B systems**. The evaluation **should include stronger recent models and an actual agentic setting**, with mandatory registry checking, a post-hoc verifier, RAG, PackMonitor, and BOUND-plus-verifier as baselines. Without these experiments, the supported claim is limited to preselected high-risk prompts for small, tool-free models.

   最后，**所有被评估的模型都是不使用工具的 6.7B/8B 系统**。评测**应包括更强的新近模型和真实的智能体设置**，并采用强制注册表检查、事后验证器、RAG、PackMonitor 和 BOUND 加验证器作为基线。没有这些实验，当前证据所支持的结论只能限于小型、不使用工具的模型在预先筛选出的高风险提示上的表现。

8. **[Other-Artifacts Required for Full Verification]**

   The declared Zenodo artifact is publicly accessible, contains BOUND.zip, and provides an open license. Following the review-form instruction, I assessed availability only and did not execute the code. Public availability is a strength, although full verification of the main claims requires the prompt-selection traces, registry snapshot, complete generations, and statistical scripts discussed above.

   声明的 Zenodo 材料可公开访问，包含 BOUND.zip，并提供开放许可证。按照审稿表说明，我只评估了材料的可访问性，没有执行代码。公开可访问是一项优点，但要完整验证主要结论，还需要前文提到的提示筛选记录、注册表快照、完整生成结果和统计脚本。
