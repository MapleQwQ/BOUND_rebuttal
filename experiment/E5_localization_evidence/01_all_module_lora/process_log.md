# 实验1过程记录

## 2026-09-24：历史运行定位与静态成本核查

- 找到三模型×四折`wo_localization_all_lora`全部12个adapter、配置、timing和RQ3指标；配置将七类候选投影后缀作为LoRA目标，实际扩展为DeepSeekCoder 224、Qwen3 252、Llama-3.1 224个linear模块。
- 使用tensor-only `torch.load(weights_only=True)`计数adapter参数并记录文件大小，输出`../results/01_all_module_lora/existing_runs.csv`。对照BOUND各折来自`robust_nonedit_highrisk_20260605/.../blast_50`。未发现该All-module条件的HumanEval逐题或summary。
- 本轮只读重分析未用GPU；下一步HumanEval与必要成本重测只用GPU 2、3。历史timing来自其他GPU和不同运行阶段，不能直接称为公平wall-time比较。

## 2026-09-24：HumanEval运行脚本验证

- 新增`../script/run_all_module_humaneval.py`，将同论文HumanEval的164题、生成设置和判分器应用于现有12个All-module adapter；GPU参数仅接受2或3，结果写入E5，逐fold记录运行事件。
- 沙箱内CUDA不可见的首次smoke落到CPU，已立即停止且未产生可用summary。经环境批准后在GPU 2对DeepSeekCoder fold A做1题smoke，summary显示加载224个LoRA模块、完成1题判分。该1题pass@1仅验证流程，不进入实验表。全量12折HumanEval尚未运行。

## 2026-09-24：启动全量HumanEval

- 确认GPU 2和3均空闲后，在GPU 2启动DeepSeekCoder四折的全量164题运行。进程在`tmux`会话`e5_humaneval_gpu2`；命令由`../script/run_all_module_humaneval.py`执行，逐折事件和详细输出写在`../results/01_all_module_lora/humaneval/`。本条仅记录启动，不将尚未完成的结果计入表格。
- GPU 3的margin评分完成后启动Qwen3、Llama-3.1四折队列。复核历史论文HumanEval发现最终表格使用每题10个样本及多run，Qwen3 thinking还有不同生成配置；当前队列每题1个样本，因此仅为单次pass@1审计，不能直接与最终论文表格比值或推出pass@10。后续表格按此限制标注。

## 2026-09-24：12折单样本HumanEval完成

- GPU 2完成DeepSeekCoder四折；其后GPU 2提前完成Llama-3.1 D、C，GPU 3完成Qwen3四折和Llama-3.1 A、B。12/12个summary均存在、每个164题且逐题判分齐全，队列正常退出。
- 新增`../script/analyze_all_module_humaneval.py`，核对历史单样本对照的题目ID与生成参数，计算四折均值和10,000次题目配对bootstrap CI。三模型All-module−BOUND依次为−2.29、+1.52、+0.91百分点，区间均跨0。结果表写入`design_and_results.md`；不能据此声称通用代码能力下降。

## 2026-09-24：RQ3逐提示配对复算

- 从原RQ3 ablation目录读取每折同一100条unseen prompt的`BOUND`和`wo_localization_all_lora`逐提示结果；新增`../script/analyze_rq3_pairs.py`，按prompt配对、四折等权bootstrap 10,000次，写出`../results/01_all_module_lora/paired_rq3_per_fold.csv`和summary。三模型Valid-Rate均显著降低；HumanEval单样本差异则仍不确定。

## 2026-09-24：同GPU四折成本重测完成

- 新增`../script/benchmark_edit_cost.py`和`../script/summarize_edit_cost_rebench.py`。在GPU 2运行DeepSeekCoder、Llama-3.1，GPU 3运行Qwen3；每折两条件以新进程完成定位/训练阶段，24/24单元成功。保存adapter、逐折配置、源编辑case哈希、阶段wall time及CUDA峰值reserved memory。
- 汇总器确认同折两条件编辑case和源配置哈希一致、重测BOUND模块与原实验一致；24格数据和四折均值分别写入`../results/01_all_module_lora/cost_rebench/per_fold.csv`和`summary.json`。All-module编辑阶段显存高约7.6–9.1 GiB、总耗时高约59–65秒、adapter大约43–73倍。完整结论见设计结果表。

## 2026-09-24：论文HumanEval协议补跑启动

- 新增`../script/run_paper_protocol_humaneval.py`：每题10样本、四折各5次run、seed=43–47；DeepSeekCoder/Llama-3.1保持512新token，Qwen3使用论文thinking补充设置的chat template、thinking启用和2048新token。所有逐run结果只写E5，GPU参数只接受2或3，完整summary可跳过。
- GPU 2空闲后启动DeepSeekCoder四折×5run队列；Qwen3/Llama-3.1待GPU 2或3空闲时按同协议运行。此队列耗时较长，本条仅记录启动，不将未完成run计入性能表。

## 2026-09-25：论文协议队列扩展到GPU 3

- DeepSeekCoder继续占用GPU 2；风险项共同随机数评估退出后GPU 3空闲，启动Qwen3 thinking四折×5run。另启`../script/wait_then_run_llama_humaneval.py`，每30分钟检查DeepSeekCoder队列及GPU 2状态；仅在20/20个DeepSeekCoder summary完成且GPU 2空闲后自动启动Llama-3.1四折×5run。
- 新增`../script/analyze_paper_protocol_humaneval.py`用于逐模型/折/run核对164题×10样本、seed和Qwen thinking配置，与历史论文BOUND运行按任务配对计算pass@1/pass@10区间。只有60/60个All-module run完成后才能生成最终论文协议比较。

## 2026-09-25：核对论文HumanEval主表并纠正队列

- 用户指出论文HumanEval不要求五次重复。复核`paper/Package_Hallucination_icse/catalogue/discussion.tex`及`E0_version_audit/results/paper_cell_provenance.csv`确认：主表的Edited值是每模型四个编辑折**各选一次**的算术平均，每次164题×10样本；不是四折×五次的平均。先前将历史补充实验的五次重复及Qwen3 thinking协议误当成主表协议，已停止对应三个tmux队列，不再把这些部分结果用于主表对照。
- 主表选中run：DeepSeekCoder A1/B1/C2/D2，Qwen3 A5/B4/C4/D1，Llama-3.1 A1/B2/C2/D4。历史summary确认各run的seed=42+run、`max_new_tokens=512`、`temperature=0.2`、`top_p=0.95`，Qwen3主表没有chat template/thinking配置。用户同时将允许的GPU扩展为1、2、3。
- 新增`../script/run_paper_table_humaneval.py`和`../script/analyze_paper_table_humaneval.py`，按上述选中run生成并逐题对照历史BOUND。已完成的DeepSeekCoder A1（164题×10样本）从误设队列目录复制到新结果目录，并核对summary及1640条判分；DeepSeekCoder A2中断片段、Qwen3 thinking A1中断片段仅保留在旧目录作过程证据。
- 启动三个新队列：DeepSeekCoder GPU 1、Qwen3普通生成 GPU 3、Llama-3.1 GPU 2；输出均在`../results/01_all_module_lora/humaneval_paper_table/`。最终需12/12个summary齐全、运行`analyze_paper_table_humaneval.py`并把主表对应pass@1/pass@10及区间写入设计结果文档。

## 2026-09-25：论文主表同配置HumanEval完成

- 三个队列正常退出，12/12个指定fold/run的summary齐全；每单元核对164题、1640生成、1640判分、seed、512新token及未启用thinking/chat template。DeepSeekCoder A1是前一队列中已完成且同配置的运行，复制后同样通过完整性审计；其余11格由纠正后的队列生成。
- 执行`../script/analyze_paper_table_humaneval.py`，逐题与历史BOUND同fold/run比较，10,000次题目配对bootstrap。得到DeepSeekCoder/Qwen3/Llama-3.1的All-module−BOUND pass@1分别为−0.82/−0.64/−1.69百分点；仅Llama的95%区间完全低于0。pass@10及各区间写入`design_and_results.md`，完整原值保存在`../results/01_all_module_lora/humaneval_paper_table/`。
- 历史BOUND四折均值与论文HumanEval表的Edited栏一致；历史运行与新增运行不在同GPU/时间，未把推理wall time用于公平速度比较。实验1的RQ3、成本、adapter大小、HumanEval均已有可复算结果。
