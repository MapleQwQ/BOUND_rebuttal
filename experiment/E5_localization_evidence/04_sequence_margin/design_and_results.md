# 实验4：未参与编辑的候选包的完整序列概率间隔

## 核心问题与预先固定的评分

对每个模型的原RQ2 unseen prompt `x`，在**同一个固定上下文**中用teacher forcing分别评分有效包`g`与幻觉包`h`的全部token。设`c(x)`为论文包推荐chat模板及固定回答前缀`[ANSWER]\n`，候选包名按同一规范化规则呈现。主分数为

`s_M(p|x) = (1/T_p) Σ_{t=1}^{T_p} log P_M(p_t | c(x), p_{<t})`，

`margin_M(x,g,h)=s_M(g|x)-s_M(h|x)`。

这里的`T_p`是该模型tokenizer对候选字符串的token数；一次forward中的所有候选token都计入，不退化为第一token。评分不采样、不执行生成代码。主结果按每个prompt内的所有有效/幻觉候选两两形成pair后先求**prompt均值**，再在100条unseen prompt中有两类候选者上求均值；模型和fold等权。另报告未归一化log probability以及候选字符串前加空格的敏感性。记录每个token的logprob、token数、score与prompt/包标签，确保可复算。

## 候选固定与泄漏控制

- 候选源为`knowledgeEdit/results/rq2_cross_task_20260611/{model}/test100/rq2_test100.jsonl`中的历史`valid`/`hallucinated`标记。三模型分别使用自己的100个原unseen提示；Base与该模型四折BOUND对**同一候选字符串**评分。
- 按PEP 503式大小写/`-_.`归一化去重；保守地排除**四个edit folds任一折**的`valid_reference`或`hallucinated`中出现的包名，并核对unseen问题文本不在编辑case中。候选集合不因模型评分结果而改变。
- `../results/04_sequence_margin/candidate_manifest_preliminary.jsonl`直接沿用原RQ2的cutoff-aware `valid`/`hallucinated`标签，作为主分析候选集；这里的“preliminary”是文件早期命名。另有`candidate_manifest_registry_screened.jsonl`：利用2026-09-24 PyPI项目名快照，仅保留当前存在的历史valid名和当前不存在的历史hallucinated名，作为更保守的敏感性分析。当前是否存在仍不能单独证明模型cutoff时的状态，已删除项目也可能造成误判。不能将pip import名与distribution名混淆。
- 对所有原RQ2主分析候选，使用历史`rq2_pypi_release_cache`、CCFA缓存和E2/E3留存首发时间，按**原RQ2各模型`case.json`中记录的cutoff**再次审计（DeepSeekCoder 2023-11-02、Qwen3 2025-04-29、Llama-3.1 2024-07-23），结果见`candidate_date_audit.jsonl`与`candidate_date_audit_summary.json`。489次valid候选出现均有首发日期且早于相应cutoff；hallucinated候选中17次有首发日期且晚于cutoff，547次当前PyPI索引不存在且无缓存首发日期，27次当前存在但缓存无日期，后27次标签仍不确定。现有缓存不能证明“当前不存在”者从未存在过，故还需注明这一局限。
- 仅排除编辑包后的双类别prompt数：DeepSeekCoder **53/100**（374对）、Qwen3 **39/100**（658对）、Llama-3.1 **67/100**（714对）。再做当前PyPI索引筛选后依次为**52/100（351对）、35/100（579对）、65/100（671对）**；这仍是候选初稿，不是cutoff核验完成集。选择覆盖率必须和主结果一起报告；另外对全部候选分别报告valid分数变化与hallucinated分数变化，防止只报有pair的子集。

## 模型、比较和统计

Base模型每模型加载一次；四折BOUND加载论文对应的历史`blast_50/blast_delta.pt`，保持同一tokenizer、模型revision、chat模板和候选manifest。投稿replication package保留生成结果但未见adapter文件，故评分所需adapter从`knowledgeEdit/results/robust_nonedit_highrisk_20260605`读取，并在运行前核对其配置/来源。新推理只用GPU 2或3；一个GPU进程一次只装一个模型，结果按`model/fold`独立落盘，已完成单元可跳过。

主对照：同prompt、同(g,h)对的`Δmargin = margin_BOUND − margin_Base`。逐模型逐折报均值、中位数、正margin比例和`Δmargin`；四折宏平均，再三模型等权。对prompt ID成组paired bootstrap 10,000次；同prompt的所有候选pair与四fold一起重采样。另报`Δs_valid`、`Δs_hallucinated`、候选级AUROC（只作补充）、模型/包类别分层；若margin增大仅由valid分数大幅下降造成，不能称“有效包得到保留”。不要按pair数将一个含大量包的prompt赋予更高权重。

## 结论阈值与限制

若跨模型/折的`Δmargin`方向一致、prompt CI支持正变化，同时valid score没有明显退化，可写“编辑增强了未见候选上的**operational score separation**”。若结果混合或覆盖率/标签核验不足，只描述数值。完整序列score separation仍不等于实际安装成功、生成代码正确或存在稳定表示空间几何边界。

## 主结果：原RQ2 cutoff-aware标签

GPU 3已完成三模型×四折的同候选评分，`../results/04_sequence_margin/scores_preliminary/per_fold_summary.csv`保留原RQ2标签主分析的12折结果，`summary.json`保留固定随机种子和10,000次prompt成组paired bootstrap结果。表中分数单位为每token平均自然对数概率之差；每个prompt先平均其候选pair，再对prompt与fold等权平均。`Δmargin=BOUND−Base`。

| 模型 | 双类别prompt | Base margin | BOUND四折均值 | Δmargin [95% prompt bootstrap CI] | Δvalid score | Δhallucinated score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 53 | -0.153 | 0.248 | +0.401 [0.070, 0.735] | -0.254 | -0.656 |
| Qwen3 | 39 | -0.245 | 0.586 | +0.832 [-0.581, 2.382] | +2.109 | +1.277 |
| Llama-3.1 | 67 | -0.372 | 0.600 | +0.972 [0.606, 1.356] | -0.454 | -1.426 |
| 三模型宏平均 | — | — | — | **+0.735 [0.233, 1.280]** | — | — |

12/12折`Δmargin`均为正；DeepSeekCoder与Llama-3.1的valid候选绝对分数也有所下降，故不能将margin增大解释为valid概率绝对改善。Qwen3的prompt区间跨0。双类别覆盖率为53%、39%、67%；这是由原提示中有无两类未参与编辑的候选包决定的。可称在**原RQ2标签、可组成pair的未见候选上**，编辑增强了操作层面的score separation；不能据此推出所有提示或表示空间中有稳定几何边界。

作为当前registry存在性筛选的敏感性分析，`scores_registry_screened/summary.json`在52/35/65个双类别prompt上得到三模型宏平均`Δmargin=+0.908`，95% CI `[0.429,1.464]`；逐模型为+0.467、+1.183、+1.074，方向一致。该筛选同时移除了部分有首发日期且晚于cutoff的真实post-cutoff包，所以它不能替代原RQ2主分析。

另一项日期审计敏感性分析从原RQ2评分中只排除27次“当前存在但缓存无首发日期”的hallucinated出现，保留已知晚于cutoff的包；`scores_cutoff_audited/summary.json`在52/36/65个双类别prompt上得到三模型宏平均`Δmargin=+0.987`，95% CI `[0.509,1.528]`。三种候选规则的宏平均方向均为正。

从同一逐token输出改用**未做长度归一化的序列总log probability**，`scores_preliminary_sum_logprob/summary.json`得到三模型宏平均`Δmargin=+1.806`，95% CI `[0.848,2.766]`；Qwen3单模型区间仍跨0。此分数受包名token数影响，因此仅作敏感性检查，主指标仍为每token平均分数。

在同一上下文把每个候选包名前加一个空格并重新评分12折，`scores_preliminary_leading_space/summary.json`得到三模型宏平均`Δmargin=+0.803`，95% CI `[0.232,1.426]`；DeepSeekCoder、Qwen3、Llama-3.1依次为+0.465、+1.016、+0.930，Qwen3单模型区间仍跨0。结论方向不依赖是否添加前导空格，但绝对Base/BOUND margin会变化。

状态：**两套候选集的全量模型评分、原RQ2主统计、日期审计、未核实标签排除、未归一化分数与前导空格敏感性分析均完成**。27次当前存在但缓存无首发日期的历史hallucinated标签仍未独立核实；排除后方向不变。GPU 3的1提示smoke仅验证流程，不进入上表。
