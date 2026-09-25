# 实验4过程记录

## 2026-09-24：同候选manifest初稿

- 从每模型原RQ2 test100文件取unseen问题与历史有效/幻觉包名，按包名归一化去重；排除四折50-case编辑文件中任一有效或幻觉包，检查编辑提示文本与unseen问题无重合。
- 写入`../results/04_sequence_margin/candidate_manifest_preliminary.jsonl`和带源文件SHA-256的`candidate_inventory.json`。剩余双类别提示数为DeepSeekCoder53、Qwen3 39、Llama-3.1 67，分别构成374、658、714个候选pair。
- 本轮只读CPU处理，没有计算完整序列概率、没有运行GPU。下一步先核验registry/cutoff标签并冻结manifest，再在GPU 2或3上对Base和四折BOUND同候选评分。

## 2026-09-24：当前PyPI筛选与GPU脚本smoke

- 从E2留存的2026-09-24 PyPI Simple项目名快照筛选候选，写入`candidate_manifest_registry_screened.jsonl`和`registry_screening.json`（含快照SHA-256）。筛后双类别prompt为52/35/65；当前存在性不能代替cutoff首发时间核验。
- 新增`../script/score_sequence_margin.py`，对同一prompt和包名用teacher forcing计算每个token logprob、序列总分及长度归一化分数，可按模型/fold在GPU 2或3运行；只读已有adapter，不训练。
- 沙箱内CUDA不可见，1提示smoke首次报“No CUDA GPUs are available”；随后经环境批准在GPU 3沙箱外成功完成DeepSeekCoder fold A 1提示smoke，输出4条Base/BOUND候选分数到`../results/04_sequence_margin/smoke/deepseekcoder/fold_A/`。全量评分尚未运行。

## 2026-09-24：启动三模型四折评分

- 新增`../script/run_sequence_queue.py`，顺序调度12个model/fold评分单元，先验证CUDA仅暴露指定GPU，已有完整结果可跳过、部分结果需人工检查。
- GPU 3空闲时启动`tmux`会话`e5_margin_gpu3`，使用当前registry-screened manifest逐单元评分；队列事件与日志在`../results/04_sequence_margin/scores_registry_screened/`。历史标签尚未经模型cutoff首发时间确认，所以任何分数仍标为provisional。

## 2026-09-24：全量评分和配对统计完成

- 12/12个model/fold评分单元成功结束，逐候选token分数和配置/adapter SHA-256均保存。新增`../script/analyze_sequence_margin.py`，逐折核对行数和Base跨fold一致性，按prompt计算valid/hall均值及margin，对prompt成组bootstrap 10,000次。
- 三模型四折宏平均`Δmargin=+0.908`，95% paired bootstrap CI `[0.429,1.464]`；逐模型和fold见`design_and_results.md`与CSV。标签仍只经过当前registry筛选，不能据此作cutoff有效性确认；原始候选和每token分数保留，便于后续重新过滤和计算。

## 2026-09-24：原RQ2标签主分析与日期审计

- 复核原RQ2候选标签来自论文cutoff-aware分类。GPU 3补跑未作当前registry筛选的原RQ2候选集，12/12单元完成；`../script/analyze_sequence_margin.py --candidate-manifest preliminary`按相同prompt配对程序得到三模型宏平均`Δmargin=+0.735`、95% CI `[0.233,1.280]`。原registry筛选结果改作敏感性分析。
- 新增`../script/audit_candidate_dates.py`，从**原RQ2 `case.json`**读取每模型cutoff，合并已有RQ2、CCFA、E2/E3首发时间缓存并记录源SHA-256。489次valid候选出现都有早于原模型cutoff的日期；hallucinated候选中17次有晚于cutoff的日期，547次当前PyPI索引不存在且无缓存日期，27次当前存在但无缓存日期。后者标签未能独立复核，保留为已知局限。

## 2026-09-24：排除未核实hallucinated标签的敏感性分析

- 不追加GPU推理，从原RQ2完整评分中排除27次“当前存在但首发日期缓存缺失”的hallucinated出现，同时保留有证据晚于cutoff和当前不存在的候选。`analyze_sequence_margin.py --candidate-manifest cutoff_audited`在52/36/65个双类别提示上得到三模型宏平均`Δmargin=+0.987`、95% prompt配对CI `[0.509,1.528]`，方向与原RQ2主分析一致。结果写在`../results/04_sequence_margin/scores_cutoff_audited/`。

## 2026-09-24：未归一化分数敏感性分析

- 直接复用已保存的完整token logprob求和，用`analyze_sequence_margin.py --candidate-manifest preliminary --score-field sum_logprob`按相同prompt paired bootstrap复算，三模型宏平均`Δmargin=+1.806 [0.848,2.766]`。该结果受候选token数影响，仅作敏感性检查。前导空格版本的GPU脚本已准备，待GPU 2/3空闲运行。

## 2026-09-24：前导空格敏感性分析完成

- GPU 2对原RQ2候选集完成三模型×四折前导空格版本的teacher-forced序列评分，12/12单元成功、逐token分数保存在`../results/04_sequence_margin/scores_preliminary_leading_space/`。相同prompt bootstrap得三模型宏平均`Δmargin=+0.803 [0.232,1.426]`，与无前导空格主分析同方向。Qwen3单模型区间仍跨0。
