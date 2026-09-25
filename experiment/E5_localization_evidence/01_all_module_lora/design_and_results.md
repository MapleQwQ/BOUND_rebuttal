# 实验1：All-module LoRA baseline

## 目的与对照

检验将同一BOUND编辑目标施加到**全部候选linear projections**时，RQ3质量、通用编码能力和成本如何变化。这里的候选空间严格是论文定位使用的七类投影：`q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`，不是所有`nn.Linear`（如`lm_head`）。对照为每模型四折的已定位BOUND；同一fold使用同一50个编辑case、rank 8、alpha 16、dropout 0.05、3 epochs、batch size 1、学习率2e-4，以及相同的valid NLL、unlikelihood、locality KL权重。改变的是LoRA插入范围及由此带来的参数预算。

现有`knowledgeEdit/results/rq3_ablation_20260613/{model}/fold_{A-D}/wo_localization_all_lora`就是这个baseline，12/12折均有配置、adapter、RQ3结果与timing。`blast_config.json`中的`resolved_target_modules`为七个投影后缀，实际`n_edited_modules`为224/252/224；不能将`rq3_metrics.json`里的`edited_modules=7`误读为仅7个实际linear模块。原BOUND adapter来自`knowledgeEdit/results/robust_nonedit_highrisk_20260605/.../blast_50`，RQ3 BOUND结果在历史与论文快照的12格指标一致。

## 已有结果：CPU核查

`results/01_all_module_lora/existing_runs.csv`逐折列出实际模块数、从adapter tensor数目得到的可训练参数数、文件字节数、历史时间及RQ3指标。下表为四折均值，MiB按2²⁰字节；历史耗时来自不同运行，作为描述性成本，**不能充当同GPU同负载的精确速度优势**。

| 模型 | BOUND模块/参数/adapter | All-module模块/参数/adapter | 历史BOUND编辑时间 | 历史All-module编辑时间 |
| --- | --- | --- | ---: | ---: |
| DeepSeekCoder | 7 / 0.459M / 0.88 MiB | 224 / 19.988M / 38.26 MiB | 72.5 s | 150.2 s |
| Qwen3 | 9 / 0.369M / 0.71 MiB | 252 / 21.823M / 41.78 MiB | 86.0 s | 160.9 s |
| Llama-3.1 | 7 / 0.287M / 0.55 MiB | 224 / 20.972M / 40.13 MiB | 90.7 s | 175.3 s |

| 模型 | BOUND Sample-HR / Valid-Rate | All-module Sample-HR / Valid-Rate |
| --- | --- | --- |
| DeepSeekCoder | 36.20% / 88.35% | 41.10% / 83.10% |
| Qwen3 | 13.00% / 72.65% | 10.10% / 63.70% |
| Llama-3.1 | 47.00% / 86.45% | 46.80% / 75.85% |

低Sample-HR不能单独代表更好；Qwen3与Llama-3.1的All-module Valid-Rate明显较低。对同一100条unseen prompt按prompt成组配对bootstrap 10,000次，以下为All-module−BOUND差值（百分点）；每折先算，再对四折等权。源逐提示输出和复算结果见`../results/01_all_module_lora/paired_rq3_summary.json`。

| 模型 | ΔSample-HR [95% CI] | ΔPackage-HR [95% CI] | ΔValid-Rate [95% CI] |
| --- | ---: | ---: | ---: |
| DeepSeekCoder | +4.90 [0.90, 8.90] | +6.75 [4.14, 9.30] | -5.25 [-8.35, -2.15] |
| Qwen3 | -2.90 [-6.80, 0.85] | -0.85 [-3.41, 1.60] | -8.95 [-13.25, -4.95] |
| Llama-3.1 | -0.20 [-4.85, 4.65] | +0.42 [-2.60, 3.45] | -10.60 [-13.55, -7.60] |

All-module在三模型的Valid-Rate均降低；DeepSeekCoder的幻觉率亦显著升高。Qwen3、Llama-3.1的幻觉率差异区间跨0，不能声称该条件在所有模型都提高或降低幻觉率。

## 新增结果：164题单样本HumanEval审计

`../results/01_all_module_lora/humaneval/`保存12折的逐题completion、执行判分和summary。`humaneval_single_sample_per_fold.csv`及`humaneval_single_sample_summary.json`与历史`knowledgeEdit/results/humaneval_paper3_20260608`的同配置单样本Base/BOUND对照；全部检查为164题×1样本，四折等权，95%区间按题目成组配对bootstrap 10,000次。四折逐值见CSV。

| 模型 | Base pass@1 | BOUND四折pass@1 | All-module四折pass@1 | All-module−BOUND [95% paired CI] |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 73.17% | 67.99% | 65.70% | -2.29 pp [-6.86, +2.29] |
| Qwen3 | 30.49% | 21.80% | 23.32% | +1.52 pp [-1.68, +4.88] |
| Llama-3.1 | 45.12% | 38.41% | 39.33% | +0.91 pp [-3.35, +5.34] |

三模型的配对区间均跨0；这批单样本结果**不支持**“All-module LoRA必然损害HumanEval”这一主张。它显示All-module的参数与产物大小显著增加，但通用代码准确率的差异目前不确定。论文最终表格采用每题10样本、每个编辑折选一次，共四次；Qwen3主表未启用thinking。这里的单样本数值不能直接与论文表格的pass@1/pass@10相减。

同批新增HumanEval运行的All-module生成耗时均值分别为DeepSeekCoder **17.72秒/题**、Qwen3 **23.56秒/题**、Llama-3.1 **18.39秒/题**（各四折平均，完整加载/生成/判分时间见逐折summary）。它们是实际测得的绝对运行成本；历史BOUND推理来自其他运行，不能据此作同GPU吞吐比值。

## 同GPU四折成本重测

`../script/benchmark_edit_cost.py`在GPU 2、3上分别以独立进程重测三模型×四折×两条件，使用相同编辑case及源配置。BOUND重新定位再训练，All-module直接对七类投影的全部实际模块训练；每单元保存adapter、源输入SHA-256、wall time和CUDA峰值reserved memory。`../results/01_all_module_lora/cost_rebench/per_fold.csv`保留24格原值，`summary.json`为四折均值。复算器确认每折两条件编辑case/源配置哈希一致、BOUND选中模块与原实验一致。

| 模型 | BOUND定位/编辑/总耗时 | All-module编辑/总耗时 | 编辑阶段峰值显存 BOUND→All | adapter大小 BOUND→All |
| --- | ---: | ---: | ---: | ---: |
| DeepSeekCoder | 16.8 / 67.2 / 84.1 s | 142.9 / 142.9 s | 17.9→26.3 GiB | 0.88→38.26 MiB（43.5×） |
| Qwen3 | 19.4 / 83.2 / 102.7 s | 163.1 / 163.1 s | 21.6→29.2 GiB | 0.71→41.78 MiB（58.9×） |
| Llama-3.1 | 18.2 / 82.4 / 100.7 s | 165.3 / 165.3 s | 22.3→31.4 GiB | 0.55→40.13 MiB（72.7×） |

显存数值是`torch.cuda.max_memory_reserved`，只比较**编辑阶段**；BOUND定位阶段另有峰值26.7/30.6/30.2 GiB。All-module虽然省去定位，却使四折平均总耗时增加约59–65秒、训练峰值显存增加约7.6–9.1 GiB、adapter扩大约43–73倍。时间包含模型加载和保存，且同一条件不同fold顺序运行；逐折数据可检查方差。

## 补充运行与判定

1. **HumanEval**：先对12个现有All-module adapter运行164题、每题1个样本的单次pass@1审计，保留逐题判分和每fold值，可与历史`humaneval_paper3_20260608`中的同配置单样本Base/BOUND作描述性对照。论文主表每题10个样本、每折一次，共四次，并报告pass@1/pass@10；Qwen3主表使用普通生成（不启用thinking/chat template），512 token上限。主表四折选用的历史run编号由`E0_version_audit/results/paper_cell_provenance.csv`逐格核验：DeepSeekCoder A1/B1/C2/D2，Qwen3 A5/B4/C4/D1，Llama-3.1 A1/B2/C2/D4。E5按这些fold/run/seed分别生成All-module结果，与同折同run BOUND逐题配对；**单样本审计不能直接与论文主表比较，也不能得出pass@10。**
2. **成本**：逐折报告定位时间（BOUND）、编辑时间、完整wall time、峰值GPU显存、训练参数数、adapter文件字节数和模型加载/生成吞吐。已有时间日志可作先验清单；若要公平比较wall time或峰值显存，在GPU 2/3以同环境重测双方。输出目录只在`E5/results/01_all_module_lora/`；新脚本只在`E5/script/`。
3. **RQ3质量**：直接重用已有100条unseen prompt×5次生成的同折结果，核对ID/问题/版本，再做prompt配对bootstrap；将Sample-HR、Package-HR、Valid-Rate和Empty-Rate并列呈现。
4. **解释边界**：此对照同时改变定位范围和可训练参数预算，证明宽覆盖替代方案的实际权衡，不能单独量化“定位优于同预算随机位置”。HumanEval下降需要实测，不能由adapter较大预言。

## 输出与状态

- 已有：`../results/01_all_module_lora/existing_runs.csv`，由`../script/reanalyse_existing.py`只读生成。
- 已有：12折单样本HumanEval逐题与汇总、prompt配对RQ3差值、历史及同GPU四折成本重测、可精确复核的参数/adapter大小。论文主表对应的四折×10样本HumanEval正在GPU 1、2、3运行，结果写入`../results/01_all_module_lora/humaneval_paper_table/`。先前误按四折×五次且Qwen3 thinking启动的队列已停止，其部分结果保留在`humaneval_paper_protocol/`，不进入主表比较。GPU 2的一题smoke仅验证流程，不进入上表。
