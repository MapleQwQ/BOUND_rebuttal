# E2new 实验过程日志

## 2026-09-24：初版设计

- 用户要求根据reviewer意见重新设计E2，本轮仅设计，不实施实验。
- 阅读审稿问题与旧E2证据边界，参照E1标注和E3共享样本协议；使用指标设计技能，将主要问题收窄为强制验证下编辑的增量质量/成本价值。
- 新建`design_and_results.md`：A强制验证、B原生PackMonitor、C真实工具执行切片；给出样本、四折配对、registry双口径、标注、失败处理、成本、统计与冻结门。
- 明确已接触旧探索结果、100任务/30任务审计的精度限制、默认不作非劣性承诺，以及C安装执行前的安全授权门。
- 保留旧E2全部内容；本目录results/script仅占位，尚无新数据、代码运行、联网收集、标注或执行结果。

## 2026-09-24：按作者补充意见调整部署动机

- 增加第0.1节，围绕离线无验证组件、验证/repair成本、未执行验证时的原始风险组织证据；保留强制验证主比较，不回避reviewer点名基线。
- 明确缓存verifier/PM也可离线、查表不必增加模型token、用户验证采用率尚无行为实证；不将名称风险降低扩展为供应链安全保证。
- Raw升为关键次要部署终点并纳入完整配对审计；更新A/B双标预算为3,300次，补充预设采用率情景分析及其假设限制。
- 仍处于设计阶段，未运行新实验。

## 2026-09-24：按最新更正收敛为Base+在线verifier

- 以用户最后更正为准，新增Base+verifier而非BOUND+verifier。在设计文档顶部写入v2优先生效协议，将旧v1保留为历史/可选扩展。
- 最小主对照改为Base、BOUND四折、Base+串行逐包在线PyPI验证后过滤；共享Base原回答，不重生成，因此verifier额外模型token为0。
- 明确网络unknown、标准库、回答内去重、会话复用、超时/重试、缓存敏感性、端到端计时和独立质量审计，避免将慢网络或过滤空输出误作方法优势。
- 更新最低预算：1,500次初始生成，30任务审计540条回答、双标1,080次；旧大规模组合矩阵不是本版最低交付。
- 保留C要求的组合增量和实际agent尚未覆盖的事实。本轮没有联网查询或启动实验。

## 2026-09-24：改为原论文全量高风险unseen协议（v3）

- 根据用户要求核对原论文experimentalsetup.tex、三模型复现YAML与旧E2源结果manifest，取消100条shared/单次greedy设置。
- 当前主测试范围为DeepSeekCoder 541、Qwen3 409、Llama-3.1 934条原始unseen高风险提示；不包含各模型4×50条编辑提示，不把模型特定风险池误称共同测试集。
- 对齐五次采样、temperature=0.7、top_p=0.9、包推荐128-token上限及原四折adapter；top_k=40及其余实现细节需按runtime核对冻结。
- 预算更新为47,100条初始回答与9,420条BOV派生记录；全量自动指标与每模型30任务随机trial语义审计分开。明确联网请求数按候选数而非回答数计。
- 记录默认YAML与历史源结果的DeepSeek/Llama cutoff冲突，要求实施前溯源最终论文配置；区分旧cutoff对齐表与现实存在性表。
- 本轮只更新设计，不启动推理、联网核验或标注。

## 2026-09-24：精简设计文档

- 移除已被替代的v1/v2全文、重复部署论述与非当前执行清单；方案演变保留在本日志，旧E2文件及实验数据不变。
- 整理为目的/对照、数据/生成、在线验证、指标/审计、成本/统计、预算/执行、结论/结果七部分。
- 保留全量高风险设置、缓存敏感性、cutoff待核对项与关键质量约束；本次只精简表达，未启动实验。

## 2026-09-24：固定cutoff及总耗时口径

- 按用户指定采用replication package三份YAML：DeepSeekCoder 2023-10-29、Qwen3 2025-04-29、Llama-3.1 2023-12-31。移除cutoff待决事项；各条件重算标签但保持原prompt划分，旧结果不覆盖。
- 明确逐回答T_BOV=T_Base+T_verify，后者含解析、联网查询、重试/等待和过滤；先逐条求和再计算均值/p50/p95，不相加分位数。
- 原Base若无可靠计时需补测或明确标注估计，不当作0。本轮仅更新设计，未启动实验。

## 2026-09-24：复用旧回答，开始E2new执行

- 阅读官方PyPI Index API/JSON API文档，在线验证使用项目Simple端点，明确200/404与unknown状态；逐回答第三方候选串行查询，不跨回答应用层缓存。
- 新增`script/run_existing_generations.py`，含源数据审计、SHA256 manifest、可断点续跑的逐包查询及逐回答验证耗时。已有生成原文保持不变。
- 源数据审计通过：DeepSeekCoder/Qwen3/Llama分别541/409/934个任务，Base试次2705/2045/4670，四折BOUND试次10820/8180/18680；各折任务文本和Base答案一致。Base第三方候选前的去重计数8469/6926/16453，共31848个回答内候选。
- 历史全部9420条Base试次均缺逐回答生成耗时，故本阶段不填造`T_Base`和`T_BOV`；需要独立、固定协议的GPU补测才能报告端到端时延。
- 在线试运行完成10条Base回答、44个候选：30个存在、14个404，不含unknown；保存于`results/online_verifier_answers.jsonl`。结果仅用于协议运行检查，随后按固定顺序续跑全量，不单独纳入效果估计。
- 全量Base逐回答验证已启动，输出每回答flush，可依唯一键断点续跑；同时下载官方PyPI全局Simple JSON项目索引（响应序列号41394637、897748个规范名），保存名称列表、响应日期和原响应SHA256，供所有条件独立的现实存在性评价。
- 新增`script/summarize_existing_generations.py`：全量Base/BOUND/BOV当前存在性指标、四折均值、prompt级配对bootstrap和验证耗时汇总。只有9420条BOV记录全部完成才输出最终全量表。
- 新增`script/fetch_release_dates.py`：为输出中存在的项目按唯一规范名查询官方Simple项目JSON最早上传时间，支持断点续跑并保存响应证据；用于replication package cutoff重标。其查询与BOV运行时逐回答验证分别计量，不混入BOV时延。
- 核对replication package的`bound/bound.py::fetch_first_release_date`后，发现其实际用PyPI项目JSON API各版本首文件的最早`upload_time`并以cutoff日期午夜比较。已停止初始Simple项目页日期查询；其少量探索记录保留在`package_first_release.jsonl`但不用于主结果。正式日期证据改存`package_first_release_jsonapi.jsonl`，严格复用原代码的最早时间规则，线上逐回答HEAD验证不受影响。
- 新增`script/summarize_raw_current.py`并完成阶段性全量当前存在性计算（官方索引序列号41394637）：DeepSeekCoder Base/BOUND四折Sample-HR为0.7238/0.3272，Qwen3为0.7482/0.1424，Llama为0.7709/0.3663。BOUND四折空回答率依次0.0675/0.2282/0.1220，需与错误率共同解释。该表仅是原始Base/BOUND的现实存在性阶段结果，BOV联网过滤和cutoff日期审计尚在运行，不作最终E2new结论。
- 新增`script/summarize_cutoff.py`，待逐包发布时间证据和BOV全量记录完成后重算replication package的三套cutoff口径；未知状态给上下界。已通过Python语法检查，但最终汇总尚未运行。

## 2026-09-24 04:42 UTC：在线实验中途审计

- BOV逐包查询已越过1000/9420条回答，正式截止日期JSON证据已越过1000/5951个名称，两个队列均在持续写入，可断点恢复。
- 核对当前已完成记录的HTTP响应与冻结索引：已见的确认存在/确认不存在结果无矛盾；`unknown`主要为无法构成单一distribution名的字符串，单列而非计为不存在。
- E1既有300条独立仲裁标签与对应旧回答包集合逐条完全一致。新增`script/reuse_e1_semantic.py`，待BOV对应任务完成后在E1已有每模型20任务上做**探索性**槽覆盖保留推导；BOV标签不是新一轮人工双标，不冒充设计中的每模型30任务确认性审计。
- 注意正式BOV存在性查询与独立cutoff元数据审计曾同时访问PyPI，故其逐回答耗时受研究并发负载影响，不直接宣称无背景负载时的部署延迟。为后续干净的验证阶段时延测量，已按结果盲SHA256排序冻结各模型30任务、各任务一个generation index，共90条的`results/timing_subset_manifest.csv`；待两个全量查询队列结束再单独计时，避免用已观察的错误案例选样。

## 2026-09-24：按用户更正重启完整Base+verifier计时

- 用户指出仅复用旧回答无法获得Base生成耗时，要求完整Base生成+逐包验证并指定GPU2、GPU3。已停止旧回答逐包验证与cutoff元数据审计队列；原始部分记录保留为探索/溯源，不混入新端到端计时。正式在线baseline将使用**新生成的Base回答**。
- GPU2/GPU3经`nvidia-smi`确认空闲。沙箱内PyTorch无法初始化CUDA；按环境要求申请沙箱外执行，GPU2测试返回`torch.cuda.is_available=True`，然后在两卡启动DeepSeekCoder与Llama-3.1各2任务的独立smoke。
- 新增`script/generate_base_timed.py`：复用原仓库`gen_chat`、推荐提示模板、包名抽取，按temperature0.7/top_p0.9/top_k40/max128五次采样；逐trial固定seed、GPU同步计时，保存回答、包名、token数和T_Base，可断点续跑。GPU2计划顺序跑DeepSeekCoder→Qwen3，GPU3跑Llama-3.1。
- 后续新增验证脚本以新Base回答为输入，逐回答保存T_verify和T_BOV=T_Base+T_verify；旧BOUND回答仍用于已完成的效果对照，不能把旧BOUND未记录的生成耗时填造出来。

## 2026-09-24 05:00 UTC：完整生成与在线验证开始

- 两个smoke均完成：GPU2 DeepSeekCoder和GPU3 Llama-3.1各2任务、每任务5次；输出隔离为`*_smoke2.jsonl`，不进入正式分析。
- GPU2正式运行DeepSeekCoder的541×5=2705条Base生成，GPU3正式运行Llama-3.1的934×5=4670条。两者均已成功加载模型并持续追加逐回答耗时与答案；GPU2完成后立即继续Qwen3的409×5=2045条。
- 新增`script/verify_timed_base.py`，分别追踪两个GPU生成文件，逐回答串行向PyPI项目Simple端点请求，记录每包响应与耗时、过滤后包集合、`T_verify`及`T_BOV=T_Base+T_verify`。每个模型的验证队列已启动，可断点续跑；不使用先前旧Base验证记录补齐新结果。
- 此阶段为运行中状态，不能将尚未完成的分子/分母当作全量结果。在线网络时延随PyPI响应及研究期间并发而变，最终会注明计时环境。
- 根据用户要求，长时间运行时约每10分钟集中核对一次结果文件与进程；GPU生成、在线验证均持续后台运行，避免高频轮询带来的对话消耗。
- 新增`script/summarize_full_timed.py`，严格读取新Base/新BOV及旧BOUND四折，校验逐条答案—包集合—时间相加关系，按prompt配对bootstrap输出Sample-HR与重新聚合比值的Package-HR区间，并汇总Base/验证/BOV逐回答时延及请求状态。
- `script/fetch_release_dates.py`和`script/summarize_cutoff.py`改为包含新Base/新BOV；正式cutoff日期审计计划在在线验证计时结束后启动，避免审计网络流量干扰BOV时延。

## 2026-09-24 05:16 UTC：约10分钟进度检查

- DeepSeekCoder新Base 1416/2705、对应在线验证1118/2705；Llama-3.1新Base 1774/4670、在线验证928/4670。四个进程均仍运行且定期写出进度，无退出错误。
- 验证速度慢于GPU生成，因此会产生待验证队列；不能因为生成完成就宣布BOV全量完成。下次按约10分钟检查，并在DeepSeekCoder完成时立即把GPU2切换到Qwen3。
- 为避免10分钟检查间隔造成GPU2空闲，新增并启动`script/queue_qwen_after_deepseek.py`：等待当前DeepSeekCoder GPU进程退出，确认2705条唯一生成记录完整后，自动在GPU2启动Qwen3全量409×5次生成。若DeepSeekCoder不完整则拒绝切换，不静默跳过。
- Qwen3的在线验证追踪进程也已提前启动，将等待其新Base文件出现；各模型验证各自保存逐回答记录。

## 2026-09-24 05:26 UTC：第二次集中检查

- DeepSeekCoder新Base 2170/2705、在线验证1697/2705；Llama-3.1新Base 2725/4670、在线验证1445/4670。四个正式进程均持续正常输出；Qwen自动接力和验证等待进程也未退出。
- GPU生成仍快于逐回答串行联网验证；保持冻结协议，不把不同实现的验证时延混算。DeepSeekCoder剩余535条后会按自动接力切换到Qwen。

## 2026-09-24 05:36 UTC：第三次集中检查与GPU2自动接力

- DeepSeekCoder新Base全量2705/2705、GPU进程正常退出；自动队列校验完整性后已在GPU2启动Qwen3，当前284/2045条，GPU2没有等待人工轮询才切换。
- Llama-3.1新Base 3895/4670；在线验证DeepSeekCoder 2322/2705、Qwen3 228/2045、Llama-3.1 1979/4670。全部验证进程仍在运行，DeepSeekCoder验证尚未全量完成。
- Qwen3生成、验证与另外两模型验证有同时访问PyPI的时段，实际验证时延含此并发背景负载；最终报告不能把该时延当作单用户、无负载网络常数。
- DeepSeekCoder全量BOV随后也达到2705/2705，并用`script/summarize_full_timed.py --model deepseekcoder`完成首个单模型质量/时延完整性检查：新Base/BOV/旧BOUND四折的当前快照Sample-HR为0.6695/0.0011/0.3272；新Base/验证/BOV平均时延分别0.753/0.970/1.723秒。此为单模型阶段结果，其他模型仍未完成。
- 审计发现一个确切的时间窗口差异：`pyupio-safety`在早先下载的全局索引中不在名单，但在后续逐包HEAD查询中返回200，出现3次。因此BOV在**冻结索引**口径有3次名称错误，而在**在线查询**口径这些名称已被确认存在；不得笼统说验证器漏检或强行合并两个不同时点的真值。汇总脚本增加双向索引/HEAD冲突记录。

## 2026-09-24 05:56 UTC：第四次集中检查

- 三模型新Base生成计数依次2705/2705、1877/2045、4670/4670；DeepSeekCoder与Llama GPU任务均正常完成，Qwen在GPU2剩余168条。
- 三模型在线验证计数依次2705/2705、1302/2045、2957/4670；两个未完成验证队列仍持续输出。未启动发布时间审计，以免额外请求与验证计时混杂。

## 2026-09-24 06:06 UTC：第五次集中检查

- 三模型新Base全部生成完成：DeepSeekCoder 2705、Qwen3 2045、Llama-3.1 4670，共9420条；GPU2/GPU3生成进程均正常退出，GPU推理阶段结束。
- BOV逐条在线验证依次2705/2705、1798/2045、3431/4670；Qwen与Llama验证进程仍持续输出。尚不能发布三模型全量汇总。

## 2026-09-24 06:16 UTC：第六次集中检查

- Qwen3在线验证2045/2045正常完成；Llama-3.1在线验证3904/4670，仍在运行。三模型新Base与DeepSeekCoder、Qwen3的BOV记录均已完整。
- Qwen3单模型完整性与汇总脚本通过：新Base/BOV/旧BOUND四折的冻结索引Sample-HR分别0.7046/0/0.1424；新Base/验证/BOV平均时延分别0.719/1.074/1.793秒。仍待Llama全量后生成三模型主表。

## 2026-09-24 06:26 UTC：第七次集中检查与cutoff审计自动接力

- Llama-3.1在线验证4346/4670，剩余324条，进程持续输出；另外两模型BOV已完整。
- 新增并启动`script/queue_release_audit.py`：等待Llama在线验证进程退出，先逐模型确认全部9420条BOV记录及唯一键，再自动启动独立PyPI JSON发布时间查询。此顺序保证发布时间请求不会与主在线验证计时并发；若验证不完整则拒绝启动审计。

## 2026-09-24 06:36 UTC：全量Base+BOV完成并汇总

- Llama在线验证于约06:33 UTC完成4670/4670，正常退出；自动接力核查三模型全部9420条BOV唯一记录后，启动独立cutoff发布时间审计。日期审计目标6298个当前存在的规范名，先前已完成2369条；该流量从主验证全部结束后才恢复。
- `script/summarize_full_timed.py`三模型全量运行成功，逐条核对新Base/BOV键集合、包集合及`T_Base+T_verify=T_BOV`。当前冻结索引Sample-HR：DeepSeekCoder Base/BOV/BOUND四折=0.6695/0.0011/0.3272，Qwen3=0.7046/0/0.1424，Llama=0.6848/0/0.3663。
- 对应Base/验证/BOV平均时延（秒）：DeepSeekCoder 0.753/0.970/1.723，Qwen3 0.719/1.074/1.793，Llama 0.582/1.195/1.777。详细逐模型p50/p95、Package-HR、无包率、unknown和配对CI已写入`results/full_timed_summary.json`及`results/full_timed_by_fold.csv`，并更新中文`design_and_results.md`。
- 结果不支持“BOUND比联网验证器更低幻觉”的表述；可报告的是BOUND推理时不依赖联网/专用验证器，而本次BOV增加时间。BOUND旧回答没有实测生成耗时，不能声称已直接测得BOUND比BOV快；语义充分性仍待审计。

## 2026-09-24 06:46 UTC：cutoff首发时间审计进度

- PyPI项目JSON首发时间证据3184/6298条，自动审计进程持续输出，无退出错误。查询为逐唯一规范名进行，与已完成的BOV计时无重叠。
- 仍须等待所有当前存在的名称都有日期/未知记录后，才能按DeepSeekCoder 2023-10-29、Qwen3 2025-04-29、Llama-3.1 2023-12-31生成完整cutoff表；不以当前半数证据推算未完成部分。
- 为缩短与主实验计时无关的元数据审计，已正常中断串行查询并保留逐行flush的已有记录；`fetch_release_dates.py`增设最多4个线程、线程本地HTTP会话及主线程唯一写入。以`--workers 3`从已有记录续跑，仍逐项目请求同一官方JSON端点、保留相同最早上传时间规则；查询并发只影响审计用时，不进入BOV时延。

## 2026-09-24 07:07 UTC：有限并发日期审计检查

- 日期证据已达到约5720/6298，3线程进程持续输出，未出现429。阶段文件中多数为`dated`；存在少量`no_file_date`及JSON API 404，后者不能直接判定项目已从PyPI消失。
- 单独核对`base62`：Simple项目端点返回200，但项目JSON端点返回404。因此脚本历史状态名`no_longer_on_index`只是**JSON端点404/无发布时间元数据**的旧命名，不代表Simple注册表项目不存在。cutoff重标将这些记录列为日期未知，不计为不存在；最终文档需澄清。

## 2026-09-24 07:11 UTC：cutoff审计全量完成

- 6,298/6,298条不同项目名的首发时间证据齐全且唯一；审计进程正常退出。6,071条有日期、134条无文件日期、93条项目JSON返回404；未见429。后两类日期未知保留在分母，不硬判为post-cutoff或不存在。
- `script/summarize_cutoff.py`全量运行成功，采用replication package三模型cutoff及原代码最早上传时间规则，输出`results/cutoff_by_fold.csv`与`results/cutoff_summary.json`。逐折和BOV的下/上界已写入中文`design_and_results.md`；这些是未知标签敏感性界，不是统计置信区间。
- BOV保留的cutoff后但当前真实存在包，在三个模型中分别出现104、41、153次；当前存在性验证与旧模型cutoff有效性不能混称。确认Simple 200/JSON 404可并存后，将未来脚本状态名改为`json_404_no_release_metadata`；本轮已保存的93条旧状态名保持原始溯源，分析一律按日期未知处理。

## 2026-09-24：最终完整性验证

- 新增并运行`script/validate_outputs.py`：三模型提示数541/409/934、成对新Base/BOV记录2705/2045/4670均齐全；逐条检查唯一键、固定seed、原回答与候选集一致、在线检查与过滤规则一致、三个时间非负且可相加。6,298条首发日期记录名称唯一。全部通过。
- `script/summarize_full_timed.py`及`script/summarize_cutoff.py`均已成功输出全量结果；未发现仍在运行的E2new生成、验证、日期审计进程。中文`design_and_results.md`已包含当前存在性、cutoff敏感性、时间和未完成语义审计边界。

## 2026-09-24：按论文Cost of BOUND风格重排结果

- 根据用户反馈，核对论文`catalogue/discussion.tex`中的Cost of BOUND：其主表按方法列行、成本指标列列，后接少量解释性文字。E2new结果第7节改为相同的“结论→按方法的三模型等权平均主表→每模型耗时→存在性与cutoff敏感性→结论边界”阅读顺序。
- 移除正文中旧Base探索性大表，避免与本次新Base/BOV直接对照；旧结果仍保存于`results/raw_current_interim.json`。p50、逐折Package-HR、完整请求状态等保留在原结果文件，不在主结果正文重复堆表。
- 主表数字从`results/full_timed_summary.json`重新计算三模型等权平均；明确BOUND旧输出缺少可比时延、不能把原论文11.30秒Test time直接填入本轮表。未改动原始实验数据或统计脚本。

## 2026-09-24：追溯原始BOUND时间

- 按用户要求核对replication package的12份`results/paper/package_recommendation/{model}/fold_{A-D}/BOUND/timing.json`。每份均有`eval_num_generations=5`及`inference.unseen_total_sec`；对应`eval_unseen_prompts.json`有每模型541/409/934个提示、每提示5条编辑回答。
- 新增`script/audit_bound_historical_timing.py`，验证12份replication输出与本工作区E2new复用的BOUND评估输出逐文件SHA256相同，输出`results/bound_historical_timing_by_fold.csv`和`results/bound_historical_timing_summary.json`。全部完整性检查通过。
- 原论文11.30秒可准确复现：每份`unseen_total_sec/n_prompts`，先四折平均再三模型等权平均，得到11.297826秒/提示（每提示5次生成）。模型均值为DeepSeekCoder 13.2108、Qwen3 8.2931、Llama-3.1 12.3896秒/提示；平摊每条回答分别2.6422、1.6586、2.4779秒，但不是单条纯推理时延。若误用编辑提示计时则为14.8202秒/提示，不符合论文表。
- 核对生产脚本`run_robust_one.py`：`unseen_total_sec`是整个`eval-unseen`子进程从启动到退出的wall-clock；`knowledgeEdit/package_edit.py::evaluate_after_edit`在这个子进程中加载模型、生成回答、抽包、调用PyPI/cutoff分类并写结果。因此旧时间含评估时联网，不代表BOUND部署推理必须联网，且与本次新Base+BOV的逐回答GPU/后置验证计时不可直接作速度比。
- 将上述历史BOUND时长作为独立旧口径表补入中文`design_and_results.md`，主表BOUND“本次同协议时间”仍标为不可比，而不是继续称原始时间找不到。

## 2026-09-24：统一边界补测启动

- 用户要求使用GPU0/GPU1补测BOUND，并把Base+Verifier明确拆为生成、包名抽取、逐包在线验证/过滤；同时加入PackMonitor的存在性、空包和成本基线。
- 检查GPU0/GPU1均为空闲A100 80GB。旧Base生成已在GPU2/GPU3完成，但其计时未包括原始文本抽包；旧BOV验证时间包含已抽取候选整理、查询和过滤，不能冒充完整三段分项。
- 新增`script/generate_bound_timed.py`，按原高风险unseen任务、四折、五次生成、与新Base相同的prompt-trial seed日程，分段测BOUND生成及包名抽取；排除预热、模型加载、评估PyPI查询和写盘，逐回答保存可续跑记录。
- PackMonitor原生约束仅适用于Markdown `pip install`区域；其安装命令协议与原论文纯包名列表不同，须在单独共同协议下测量，不能把旧E2的100条greedy结果混入原协议主表。
- `generate_bound_timed.py`在GPU0用DeepSeekCoder fold A前2个提示、共10条回答完成smoke，adapter加载与分段计时正常；首次沙箱运行看不到GPU，按权限流程获批后在GPU0成功运行。
- 11:43:59 UTC启动GPU0队列：DeepSeekCoder A–D、Qwen3 A–D；11:44:19 UTC启动GPU1队列：Llama-3.1 A–D。每折全量unseen、每提示5次、逐回答落盘且可续跑；两个GPU原先均为空闲A100 80GB。
- 新增`retime_base_extraction.py`并完成三模型现有新Base回答的抽包重放：DeepSeekCoder 2705、Qwen3 2045、Llama-3.1 4670条，均和原`packages`字段逐条一致；每条抽包操作运行11次取中位数。该阶段是确定性CPU重放微基准，不伪称原生成时同步测得。
- 新增`script/summarize_uniform_cost.py`，在逐回答层面将原新Base生成、重放抽包、原BOV在线验证/过滤相加，并汇总新BOUND生成+抽包。旧BOV验证阶段本来已包含候选整理、串行联网查询、重试和过滤，但不能无依据再细拆为网络/过滤两个独立实测段。
- 长时间GPU任务后续约每10分钟检查一次，异常与阶段结果及时续写本日志。
- PackMonitor新对照已配置：沿用旧E2预先冻结的每模型100提示manifest，改为每提示5次、温度0.7、128 token，Base与PackMonitor在同一安装命令协议及同一prompt-trial seed下重新生成；生成和安装命令包名抽取分别计时。原版grammar有`NATATURAL_LANG`拼写错误，仍只使用旧E2已披露的最小兼容修正。其registry为官方仓库冻结名单，最终质量另按E2new的2026-09-24 PyPI名单独立评价。
- 已启动GPU1后续队列：确认Llama四折各4670条落盘后自动跑DeepSeekCoder、Qwen3、Llama-3.1的PackMonitor原生协议对照；等待阶段不占GPU。输出分模型保存原始JSONL、运行汇总及日志。**该对照协议不同于论文原纯包名列表，主表将分块呈现，不能直接把PackMonitor的安装命令结果与原协议BOUND/BOV作无条件排名。**
- PackMonitor runner新增记录每条的生成/约束解码时间、安装命令抽包时间、交付总时间；Base与PackMonitor固定同一prompt-trial seed。正式计时前另做16-token生成预热及一次registry grammar构建，分别记录这两项和模型加载时间，避免首条请求把一次性构建费混入稳态均值。生成输出仍逐条包含错误、触发和包名，失败不能被算作成功空回答。
- `summarize_uniform_cost.py --allow-partial`首次核算通过：现有BOV三模型生成均值0.7532/0.7186/0.5816秒，抽包重放中位数均值约43/43/46微秒，在线验证+过滤0.9702/1.0742/1.1949秒；BOUND还在生成，**此时不作最终比较结论**。

## 2026-09-24 11:54 UTC：约10分钟检查

- GPU0 DeepSeekCoder fold A已写428/2705条，GPU1 Llama-3.1 fold A已写1075/4670条；两条执行会话仍正常输出100条一次的进度。GPU0/1显存约13.7/16.0 GiB，利用率59%/67%，未闲置。
- 沙箱内一次`nvidia-smi`提示无法与驱动通信，但同命令经已批准的外部执行立即返回正常GPU状态；两个生成进程持续产出，判定为沙箱可见性问题而非GPU故障。
- 后续保持约10分钟检查；PackMonitor队列仍在等待GPU1的BOUND四折完成，没有抢占同卡显存。
- 独立核对PackMonitor约束名单与E2new冻结PyPI评价名单：规范化后前者706,618名，后者897,748名；约束名单独有5,756名，评价名单独有196,886名。说明PackMonitor使用的冻结registry既不是评价时点的全量名单，也不是其子集；其可能拒绝当前真实包、允许评价时已不在名单的名字。保留两套原始名单并独立评价，不以约束名单成员资格替代当前存在性标签。
- 为避免上述旧名单时间偏差，最终PackMonitor主对照改用E2new同一2026-09-24冻结PyPI名称名单（897,748名）作为约束registry，保存JSON及源/目标SHA256元数据。官方算法实现仍不改，只更换公开可缓存名单；同一名单也用于存在性评价，报告时明确这种机械对应，不称独立安全证明。旧官方名单及旧E2结果仍保留作溯源，不混入本轮主对照。
- 已停止未占GPU、仍在等待中的旧registry队列，并在同一GPU1等待条件下重新启动指向新冻结名单的PackMonitor队列；BOUND的两个GPU任务未中断。若新较大registry的grammar编译失败，将保留错误日志并报告，不悄悄回退到旧名单。

## 2026-09-24 12:04 UTC：第二次约10分钟检查

- GPU0 DeepSeekCoder fold A已写814/2705，GPU1 Llama-3.1 fold A已写2181/4670；两者相对11:54检查持续增长，尚无中断或空闲。以当前速度推算，全量12个模型—fold条件需数小时，故保留持续落盘和可续跑机制，不把前缀试验值写成全量结论。
- PackMonitor使用新冻结名单的等待队列仍未占GPU；成本汇总暂不填最终BOUND或PackMonitor数值。下次约10分钟后再核对进度。
- `summarize_packmonitor_baseline.py`增加对100提示×5代际×两条件完整性、唯一键及配对seed的检查；Sample-HR/Package-HR差异按提示成组bootstrap，不把500条回答误当500个独立任务。计时保留一次性加载、预热、grammar构建与逐回答稳态成本的不同粒度。脚本已通过语法检查，待GPU1队列生成后再运行并验证数值。
- 为尽早发现更大冻结PyPI名单是否超出PackMonitor grammar限制，启动仅在CPU上编译当前897,748名约束表的兼容性probe，不加载生成模型、不占GPU；结果将单独保存`results/packmonitor_registry_cpu_probe.json`。它只能确认DeepSeekCoder tokenizer下grammar可编译，不能替代三模型GPU生成测试。
- 首次CPU probe在创建llguidance tokenizer时失败：代码误传`tokenizer.vocab_size=32000`，实际含新增token为`len(tokenizer)=32022`，尚未运行到grammar。已修正为与实际tokenizer长度一致并重试；此错误仅在预检脚本，不涉及官方PackMonitor runner或BOUND任务。
- 修正后CPU预检成功：897,748个冻结名称在DeepSeekCoder tokenizer下的PackMonitor grammar matcher可编译，实测构建6.08秒、无matcher错误，证据在`results/packmonitor_registry_cpu_probe.json`。这不证明Qwen3/Llama tokenizer兼容或约束实际触发，仍待GPU1完整生成检查。

## 2026-09-24 12:15 UTC：第三次间隔检查

- GPU0 DeepSeekCoder fold A达到1263/2705，GPU1 Llama-3.1 fold A达到3370/4670；相对12:04分别新增449和1189条，持续落盘无停滞。此处只记录完成度，**不将当前前缀的时间均值当全量结果**。
- CPU registry预检已完成且不占GPU；PackMonitor正式队列仍等待Llama四折完成。继续约10分钟间隔检查。

## 2026-09-24 12:24 UTC：第四次间隔检查

- GPU0 DeepSeekCoder fold A为1686/2705；GPU1 Llama-3.1 fold A为4447/4670。相对12:15仍正常增长，Llama fold A接近完成，下一折由队列自动启动。
- 仍无完整四折成本结果；继续只监控落盘与错误，不根据前缀时延修改协议。

## 2026-09-24 12:34 UTC：第五次间隔检查

- GPU1 Llama-3.1 fold A已完整4670/4670并自动转fold B（检查时约771条）；GPU0 DeepSeekCoder fold A约2112/2705，持续增长。`summarize_uniform_cost.py --allow-partial`核对已完整的Llama fold A：生成0.5467秒/回答、抽包0.000110秒/回答、合计0.5468秒/回答；同模型BOV现有全量合计1.7766秒/回答。**该BOUND数值只是单折阶段结果，不能替代四折最终均值或统计区间。**
- 抽包耗时差异很小，但BOUND是本轮原位计时、Base是后续重放微基准；口径透明保留，不用微秒差异解释主要成本变化。

## 2026-09-24 12:46 UTC：进度与剩余时间估计

- 用户询问总剩余时间。读取落盘数：GPU0 DeepSeekCoder fold A 2529/2705；GPU1 Llama fold A 4670/4670、fold B 1696/4670。两队列仍在运行。
- 依据迄今DeepSeekCoder约40–45条/分钟、Llama约100–120条/分钟，GPU0尚有DeepSeekCoder余下三折及Qwen3四折；Qwen3与三模型PackMonitor本轮尚未实测速度。初步估计从12:46起约5–7小时（18:00–20:00 UTC）完成全部生成与汇总；这是区间估计，可能因Qwen3/PackMonitor grammar构建、网络/共享GPU负载改变。后续每约10分钟根据实际速度修正，不把预计完成时间当承诺。
- 为允许GPU1完成Llama/PackMonitor后协助Qwen3且避免两个GPU同时写同一fold，`generate_bound_timed.py`新增逐输出文件的排他锁；未来新进程先持锁检查已完成键，再生成。当前两个正在运行的fold进程未被中断；代码已通过语法检查。是否拆分Qwen3队列需等实际完成时间评估，不现在更改数据或采样规则。

## 2026-09-24 12:58 UTC：第六次间隔检查

- GPU0 DeepSeekCoder fold A已完整2705/2705并自动切换fold B（检查时597条）；GPU1 Llama fold B为2702/4670。两队列持续运行，无掉卡或写盘停滞。
- 完整DeepSeekCoder fold A的同边界阶段核算：BOUND生成1.4810秒/回答、抽包0.000098秒、交付1.4811秒；同模型BOV全量交付1.7234秒。**这是单折阶段核算，不等于四折/三模型最终结论，也不含后续PackMonitor。**

## 2026-09-24 13:09 UTC：第七次间隔检查

- GPU0 DeepSeekCoder fold B达到1557/2705，GPU1 Llama fold B达到3790/4670，持续产出。DeepSeekCoder fold B目前输出速度明显快于fold A；阶段前缀交付均值约0.682秒/回答，fold A完整均值1.481秒。fold差异可能由生成长度/回答类型等造成，**前缀均值不具最终代表性**，继续按预定四折完整汇总；原12:46 ETA可能偏保守，待更多完整fold后再修正。
- 为缩短总时长、避免GPU1在PackMonitor结束后闲置，已启动另一个等待队列：它须等最后一个PackMonitor模型的summary落盘并额外等待模型退出，再在GPU1运行Qwen3 fold C/D。GPU0原队列按A/B/C/D运行Qwen3；未来C/D进程通过同一输出文件`flock`排他，先锁后检查完整键，已完整则直接退出，避免重复生成。若PackMonitor最后一模型失败，则该队列不会悄悄越过失败继续，人工检查日志后再决定。

## 2026-09-24 13:24 UTC：第八次间隔检查

- GPU0 DeepSeekCoder A/B均完整2705条，已进入C（约194条）；GPU1 Llama A/B均完整4670条，已进入C（约679条）。完整fold交付均值：DeepSeekCoder A 1.4811、B 0.6747秒/回答；Llama A 0.5468、B 0.6554秒/回答，存在fold差异，最终仍按四折等权汇总。
- 核对新计时回答的无包率：DeepSeekCoder A 16.86%、B 4.18%；Llama A 14.43%、B 32.83%。fold时延差异不能简单解释为“更快但只输出空包”，应与无包和包数一并报告。`summarize_uniform_cost.py`已加入每折无包率与平均去重包数，防止成本表脱离输出行为解释。
- 同一汇总脚本另加入**新计时回答自身**在冻结PyPI名单下的Sample-HR、Package-HR、Valid-Rate和无包率，避免用旧seed的BOUND质量结果解释本次新seed的时延；Base+BOV仍逐条配对。中途完整性/语法复算通过，但正式主表等12折记录齐全再定稿。

## 2026-09-24 13:36 UTC：第九次间隔检查

- GPU0 DeepSeekCoder fold C为1280/2705，GPU1 Llama fold C为2064/4670；两者继续正常增长。C折速度与B折接近，之前12:46的5–7小时剩余估计可能偏保守，但Qwen3与新PackMonitor全量100×5仍未实测，不提前发布更窄完成时间。

## 2026-09-24 13:47 UTC：第十次间隔检查

- GPU0 DeepSeekCoder fold C为2188/2705，GPU1 Llama fold C为3342/4670；按当前速度，C折短期内可以完成。尚无错误日志或数据停滞，仍保持约10分钟检查。

## 2026-09-24 13:58 UTC：第十一次间隔检查

- GPU0 DeepSeekCoder A/B/C均完整2705条，D已启动约153条；GPU1 Llama A/B完整、C达到4601/4670，短期将切换D。所有已完成fold均由队列自动衔接，未见崩溃或重复写入。下一检查仍约10分钟。

## 2026-09-24 14:09 UTC：第十二次间隔检查

- GPU0 DeepSeekCoder D为556/2705，当前速度约40条/分钟，类似fold A，明显慢于B/C；GPU1 Llama C已完整、D为1069/4670，持续运行。DeepSeekCoder折间速度异质再次得到验证，后续必须同时呈现各折值与四折均值。Qwen3尚未开始，PackMonitor队列仍等待Llama D。
- 上述数次检查的标题时间最初由计划的等待间隔推算，复查各记录`measured_utc`发现相对实际时钟逐步偏早；现已按对应行的真实写盘时间校正12:46–14:09的标题。记录数量、实验输出与结论未改动。后续检查标题直接读取UTC时钟，不再按等待次数推算。
- CPU-only PackMonitor名单预检扩展至Qwen3和Llama tokenizer：同一897,748名grammar分别约6.00和6.01秒编译成功、无matcher错误，结果在`results/packmonitor_registry_cpu_probe_{model}.json`。三模型tokenizer层面已过初步兼容检查，正式GPU约束生成仍未开始。

## 2026-09-24 14:19 UTC：第十三次间隔检查

- 直接读取系统UTC时钟后检查：GPU0 DeepSeekCoder fold D 913/2705，GPU1 Llama fold D 2178/4670；两队列继续正常增长。按近期速率，Llama D可能约14:40–14:50完成并触发PackMonitor，DeepSeekCoder D可能约15:00完成并触发Qwen3；这些仅是排程估计。
- PackMonitor作为baseline若只有Base-vs-monitor，而BOUND仍用纯包名原协议，则不能给审稿人一张真正同语法的直接比较表。故在不更改主实验的前提下，为安装命令次要对照预留每模型BOUND fold A、100提示×5次的无约束生成，复用同prompt/seed及官方vanilla生成器；只报告单折边界。原runner新增`--only-unconstrained`开关以免无需求地再跑BOUND+PackMonitor，已通过语法检查。此锚点应在GPU1完成既定Llama/PM/Qwen任务后运行，避免抢占主计时。

## 2026-09-24 14:31 UTC：第十四次间隔检查

- 读取系统UTC时钟与文件行数：GPU0 DeepSeekCoder D 1371/2705；GPU1 Llama D 3484/4670。按最近约10分钟增量分别458/1306条，均持续运行，无新错误。Llama D接近末尾，PackMonitor队列预期下一检查窗口开始；主结果仍待四折完整。

## 2026-09-24：用户新增BOUND+Online Verifier及过滤/token对照

- 用户明确新增BOUND+Online Verifier。此分支将复用本轮GPU0/GPU1逐条计时的BOUND回答，不再生成模型回答；每个fold的同一回答先取已测生成与抽包时间，再在线逐包查询PyPI并过滤，因此总交付时间为三段之和。联网验证与旧BOV保持相同`run_existing_generations.query`语义、回答内串行、跨回答无应用缓存。
- 将对Base+Verifier与BOUND+Verifier同时报告过滤后无包率、每回答被过滤的**当前不存在**包数、因网络未知被保守过滤的包数、过滤前后平均包数；对Base、BOUND、两个Verifier分支、PackMonitor分开记录生成token与验证额外LLM token。两个纯后置Verifier分支额外LLM token均应为0，但必须由记录规则核验，不能混同网络请求成本。
- 为赶上GPU生成，计划启动最多3个CPU联网worker跟随append-only BOUND输出；每个回答内仍串行逐包查询。所有HTTP状态、重试及时间逐回答保存，失败不静默丢弃；正式汇总仍采用冻结PyPI评价名单并保留在线查询与快照冲突。
- 已新增并通过语法检查`script/verify_timed_bound.py`。它从12个append-only BOUND JSONL增量读取，每条按输出键去重，可续跑；单回答内串行查询，最多3个回答worker并行，逐回答保存候选、各包HTTP证据、`absent`/`unknown`、过滤后包名、验证耗时及三段总交付耗时。意外代码错误会停止而不写伪成功结果。
- **2026-09-24 14:37 UTC**在批准的联网环境启动全量BOUND+Online Verifier（预期37,680条，3个CPU worker），初始0条；GPU0/GPU1生成队列未中断。并发只用于不同回答的后台补测，单回答内部仍按原BOV顺序逐包验证，HTTP共享节点负载差异将如实列为计时限制。
- 新增`script/summarize_filter_comparison.py`并在当前部分输出上完成语法/逻辑试算：严格配对原回答与过滤回答、检查每候选在线状态和最终保留列表一致，按冻结PyPI名单独立统计每回答被过滤的当前不存在包、在线unknown及可能误删的当前真实包；同时报告过滤后无包率、候选数、HTTP尝试次数、三段时间及验证增量LLM token。部分输出只作管线检查，不作论文结果。
- 新增`script/reencode_bound_tokens.py`：待每模型四折完整后，用原模型tokenizer离线重编码BOUND新回答，逐回答和同seed Base的输入/输出token对应，统计BOUND输出token差与B+OV额外LLM token=0。重编码值与生成器内部实际采样步数并非完全同义，最终命名将保留`reencoded`说明。
- 14:40 UTC初步检查：BOUND+Online Verifier已写629条/37680，三worker持续产出；GPU0/GPU1生成也持续推进。正式速度和过滤结论等全量完成后报告。
- 14:41 UTC联网先导检查约959条验证记录：每回答平均验证耗时约0.74秒；已观察到200与404状态，尚未见429，少量unknown已按未知保存并不交付。临时检查用一次性命令最初因标准库条目的`attempts`是整数而列表推导报错，修正检查命令后得到约1883个HTTP 200、231个404；**实验进程及原始记录不受影响**。后续继续监视429和unknown比例，不能以先导样本代表全量网络时延。

## 2026-09-24 14:47 UTC：Llama四折完成、PackMonitor启动

- GPU1的Llama-3.1 A/B/C/D均已完整4670条；等待队列于约14:44自动启动DeepSeekCoder的PackMonitor共同协议运行，14:47已有125/1000条Base+PackMonitor回答落盘。GPU0 DeepSeekCoder D为1915/2705，未中断。BOUND+Online Verifier已有2130/37680条，3个CPU worker持续运行。
- Llama四折完整时使用原tokenizer重编码18,680条新BOUND回答并逐fold检查ID完整，输出`results/bound_tokens_reencoded_llama3.1-release.jsonl`；这一步不占GPU。四折阶段成本均值：BOUND生成0.57118秒、抽包0.000112秒、交付0.57129秒/回答；同模型BOV交付1.77656秒/回答。**该模型当前BOUND Sample-HR约0.3676，而BOV接近零，速度不是唯一判断维度；三模型和B+OV仍未全量完成。**

## 2026-09-24 14:59 UTC：第十五次间隔检查

- GPU0 DeepSeekCoder D为2339/2705，预计短期完成后自动转Qwen3；GPU1 PackMonitor的DeepSeekCoder共同协议为539/1000条（两条件×100提示×5次），持续写入。BOUND+Online Verifier已写4299/37680条；抽查约4315条的HTTP结果有200 9914次、404 1417次，未见429，另有10条候选为unknown。联网队列没有因GPU/PackMonitor任务停止。
- 这里的unknown候选数量不是回答数量，也不能因HTTP无429就推断全部未来查询稳定；完整错误/过滤比例等最终分母齐全后计算。

## 2026-09-24 15:11 UTC：DeepSeekCoder四折完成、Qwen3启动

- GPU0 DeepSeekCoder A/B/C/D各2705条全部完整，队列已自动进入Qwen3 fold A（检查时137条）；GPU1的PackMonitor DeepSeekCoder Base+约束对照达948/1000条，接近切换Qwen3。BOUND+Online Verifier已写6187/37680条，持续运行。
- DeepSeekCoder四折新BOUND回答已用原tokenizer重编码10,820条token记录并校验fold完整。四折同边界BOUND交付均值1.13741秒/回答，同模型BOV为1.72342秒/回答；新BOUND Sample-HR约0.3226、Valid-Rate约0.8980、无包率约0.0701。**更快不等于存在性或语义更好**；Qwen3、B+OV、PackMonitor完整结果仍待完成。
- 已启动GPU0后续等待队列：仅在Qwen3四折各2045条完整并额外等待60秒后，运行三模型预先指定BOUND fold A的100提示×5次原生安装命令协议锚点。此队列目前只轮询文件、无GPU占用；与GPU1的Base/PackMonitor及Qwen3 C/D后续任务不竞争同卡。输出分模型保存JSONL、summary和错误日志；若某模型失败不把空输出当成功，继续保留其他模型日志供诊断。

## 2026-09-24 15:27 UTC：第十六次间隔检查

- GPU0 Qwen3 fold A为1783/2045；GPU1 PackMonitor已完成DeepSeekCoder共同协议Base/约束各500条，并进入Qwen3（检查时约201/1000条）；BOUND+Online Verifier已写8347/37680条，持续推进。
- DeepSeekCoder原生安装命令协议阶段汇总：约束registry大小897,748，grammar一次构建4.86秒（另报）；Base与PackMonitor的500条均无生成异常，安装区域触发率约93.2%/93.0%，registry-invalid回答率42.2%/0.8%，无包率6.8%/7.2%，生成均值1.6461/1.6448秒。**这些只是单模型次要协议结果，尚未含其他模型、BOUND-A锚点及冻结名单正式汇总，不与原纯包名主表混排。**

## 2026-09-24 15:38 UTC：第十七次间隔检查

- GPU0 Qwen3 fold A已完整2045条、fold B为922/2045；GPU1 PackMonitor Qwen3为339/1000条。Qwen3在原生PackMonitor生成器下明显慢于DeepSeekCoder，因此此前按DeepSeekCoder速度推算的PackMonitor完成时间不可靠；坚持保存原样输出，不为了缩短时间修改128-token上限或协议。
- BOUND+Online Verifier达9862/37680条，三worker仍持续联网查询。后置在线验证当前是可能的总完成时间瓶颈之一，不停止、也不删减到只看先完成的模型/折。

## 2026-09-24 15:49 UTC：第十八次间隔检查

- GPU0 Qwen3 A/B各2045条完整、C约98条；GPU1 PackMonitor Qwen3约491/1000条；BOUND+Online Verifier 11961/37680条。三项工作均持续推进。Qwen3原生PackMonitor约15条/分钟，明显比原协议BOUND慢；不把不同协议生成时延直接等同“算法额外开销”，最终应与原生Base同协议比较。

## 2026-09-24 15:50 UTC：DeepSeekCoder的B+OV四折验证完整

- 联网输出中DeepSeekCoder A/B/C/D各2705条验证记录均齐全；`summarize_filter_comparison.py --allow-partial`在该模型上通过原/过滤回答、候选及保留规则逐条检查。DeepSeekCoder BOV过滤后无包率13.46%，每回答删除当前不存在包0.8758个，总交付1.7234秒；B+OV四折均值分别为9.70%、0.4334个、2.2691秒。B+OV保留当前真实包的回答率约89.80%，BOV约82.77%。
- 这项**单模型完整结果**显示BOUND在联网验证前减少了待删除的无效包，且B+OV过滤后无包较少，但B+OV没有速度优势，反而因BOUND生成/验证成本总和更慢；不能单凭valid hit证明依赖充分性。两条验证器均无额外LLM重生成token；当前评估快照与在线时点存在少量不一致，Sample-HR未严格为0。
- 修正部分汇总保护：只有某模型四折的BOUND和B+OV各折记录数均达到预期，才写四折均值；即使`--allow-partial`也不再对四个未完成前缀生成貌似完整的macro。DeepSeekCoder此项已满足，Qwen3/Llama仍待联网结果。
- 逐回答token重编码阶段结果：DeepSeekCoder新BOUND平均46.80输出token、同seed Base平均31.26，差约+15.54；Llama新BOUND平均22.21、同seed Base平均22.47，差约−0.26。它们是**模型输出长度差**，不是验证器额外LLM token；BOV/B+OV后置流程额外LLM token仍为0。最终主表将同时列输出token与后置增量，避免把“无需重生成”误写成“总token相同”。

## 2026-09-24 16:01 UTC：第十九次间隔检查

- GPU0 Qwen3 A/B完整、C为1074/2045；GPU1 PackMonitor Qwen3为663/1000；BOUND+Online Verifier已达15813/37680。三队列均持续推进，无新报错。最近联网验证吞吐较前一段提高，可能受候选数量/HTTP延迟变化影响；不能用吞吐量代替单回答计时。

## 2026-09-24 16:12 UTC：第二十次间隔检查

- GPU0 Qwen3 C为1978/2045，即将进入D；GPU1 PackMonitor Qwen3为818/1000，即将进入Llama；BOUND+Online Verifier已写17962/37680条。约半数联网验证完成，仍无先导证据提示429限流；正式网络状态分布将在全量结果中核算。

## 2026-09-24 16:23 UTC：第二十一次间隔检查

- GPU0 Qwen3 A/B/C均完整、D约770/2045；GPU1 PackMonitor Qwen3约971/1000，下一模型即Llama；BOUND+Online Verifier约19987/37680。在线验证抽查到20,000条时，候选状态累计约47,170个exists、7,740个absent、33个unknown、1,151个stdlib，HTTP尝试未见429；仍需待最终完整分母核算。
- 过滤对照汇总脚本增加三模型等权总表生成逻辑：在Base、BOUND四折、BOV、B+OV全齐且token文件就绪时，输出Sample-HR、Package-HR、Valid-Rate、过滤后无包、被删当前无效包/回答、unknown/回答、生成/抽包/在线验证分段和总时间、重编码输出token及后置额外LLM token。第一次语法检查发现一个括号拼写错误，立即修正；`--allow-partial`再次通过并保持未完成fold不输出宏均值。脚本错误未触及运行中的GPU/联网原始数据。

## 2026-09-24 16:32 UTC：第二十二次间隔检查

- GPU0 Qwen3 D为1426/2045，其他11个BOUND计时fold已齐；GPU1 PackMonitor DeepSeekCoder和Qwen3各1000/1000条已齐，Llama为398/1000；BOUND+Online Verifier为21567/37680条。各队列继续运行。
- 扩展PackMonitor原生安装命令协议的汇总脚本：当同任务、同seed的BOUND fold A锚点完成时，一并核验并列出Base、PackMonitor和BOUND-A三条件。此项仅作为共同语法下的次要直接对照，不与原论文纯包名协议的全量主表混合。

## 2026-09-24 17:22 UTC：原生PackMonitor协议质量纠正

- GPU0已完成原论文高风险unseen集合12个BOUND计时fold（DeepSeekCoder每折2705、Qwen3每折2045、Llama每折4670条）；Qwen3 token重编码8180条完成；全量`uniform_cost_summary.json`通过条数、seed和阶段耗时校验。三模型等权均值：BOUND交付0.7870秒/答；Base+Online Verifier交付1.7643秒/答（Base生成0.6845、抽包回放0.000044、联网验证/过滤1.0797秒）。此比较是各方法**不同生成回答**上的真实耗时，不是同一文本的后处理耗时差。
- 三模型原生PackMonitor各1000条均已跑完，但检查回答发现Qwen3在128-token限制下几乎全部处于`<think>`段：Base的安装命令触发率0%、无包100%，PackMonitor触发率2.8%、无包97.2%。这些值反映设置缺陷，不能用于判定PackMonitor在Qwen3的有效性或做三模型有效主结论。DeepSeekCoder和Llama可单独作为已完成结果。
- 已在本地runner加入Qwen3 chat-template `enable_thinking=False`的显式设置（官方生成逻辑仍原样，仅复用原来披露的grammar拼写修正），原始Qwen3数据保留。GPU1于17:21 UTC启动Qwen3 Base/PackMonitor同任务同seed重测，独立文件后缀`_nothink`；GPU0已有的Qwen3 BOUND锚点仍是旧思考模式，需另行以相同禁思考协议重测，二者不会混算。
- BOUND+Online Verifier全量输出约30091/37680，持续在线逐包查询；此环节仍是总进度关键路径。GPU0运行原生BOUND-A锚点，DeepSeekCoder500条已齐、Qwen3旧设置约389条；GPU1重测Qwen3 PackMonitor。原生协议的结论以有效输出触发率和独立重测结果为准。

## 2026-09-24 17:24 UTC：中途汇总校验

- `summarize_filter_comparison.py --allow-partial`检查了30345条BOUND+Online Verifier记录；DeepSeekCoder和Qwen3的四折原始及验证后记录均完整，Llama A/B/C完成、D进行中。Qwen3 BOUND四折均值Sample-HR14.21%、Package-HR12.46%、无包23.45%、交付0.6524秒；B+OV过滤后Sample-HR/Package-HR均0%、无包24.74%、平均删除当前无效包0.2840个/答、交付1.3564秒。它们仍属于原论文纯包名协议，不与原生PackMonitor安装命令协议直接混合。
- Qwen3禁思考重测的首批回答已确实生成`pip install`命令，并检出Base错误包名与PackMonitor约束后的合法名称，验证原先的128-token思考段问题得以缓解。待全500对完成才计算正式比例。

## 2026-09-24 17:24 UTC：遵循新的GPU空闲约束

- 用户明确要求今后仅使用GPU0/1且必须在设备**空闲**时启动，否则等待、每30分钟复查。立即检查`nvidia-smi`：GPU0有本实验原生BOUND-A锚点约22 GiB，未发现第二个计算进程；GPU1有本实验刚启动的Qwen3禁思考重测约16.8 GiB，另有一个约30.1 GiB的既有计算进程。为避免与他人占用重叠，已终止本实验GPU1重测PID 1493627（退出码143），保留约已生成的前缀记录，**不纳入正式指标**。
- 同时取消预排队的GPU0 Qwen3禁思考重测（退出码130），以免当前锚点结束后未经重新确认空闲便自动启动。当前已在GPU0运行的本实验锚点继续完成；之后任何新GPU任务先检查空闲，非空闲每30分钟复查。CPU联网验证不受GPU约束，继续运行。

## 2026-09-24 17:36 UTC：CPU联网与原生锚点进度

- BOUND+Online Verifier已完成约32906/37680条，输出持续增长；GPU0先前已启动的原生BOUND-A锚点中DeepSeekCoder/Qwen3各500条完成，Llama约382/500。Qwen3这一锚点仍属于思考模式128-token的无效共同协议样本，原始数据保留但将从有效三条件比较中排除。
- 遵照用户新规则，本次仅检查记录文件进度，**未提前轮询GPU空闲状态或启动任何新GPU任务**；首次30分钟空闲复查计划约17:54 UTC。

## 2026-09-24 17:47 UTC：继续等待GPU复查窗口

- BOUND+Online Verifier在线记录约34993/37680，持续推进。未提前复查或使用GPU。
- PackMonitor汇总脚本设保护：Qwen3禁思考完整1000条尚未生成前，排除原128-token思考模式记录，不发布三模型等权均值；已重跑汇总，明确列出`pending_models=[qwen3-release]`。原失败记录仍在文件中，保留可审计。

## 2026-09-25 00:49 UTC：审批等待后恢复、全量在线验证完成

- GPU任务审批等待使实际启动时间跨至次日。启动脚本于00:48:28 UTC再次查GPU0显存仅1 MiB，确认空闲才运行Qwen3禁思考Base/PackMonitor共同协议；GPU1仍不使用。GPU0两阶段之间同样先复查空闲，如被占用每30分钟重试。之前GPU1中断前缀输出保留，新任务写`_nothink_full`独立文件，不覆盖。
- CPU上的BOUND+Online Verifier已达到**37680/37680**条。`summarize_filter_comparison.py`无`--allow-partial`校验了三模型12折完整键集合与原/过滤回答、保留规则，产出`filter_comparison_summary.json`。三模型等权：Base、BOUND、BOV、B+OV的Sample-HR依次为68.63%、27.74%、0.037%、0.035%；Package-HR为28.19%、15.46%、0.017%、0.013%；总交付耗时为0.6845、0.7870、1.7643、1.7330秒/答。
- 过滤后的无包率BOV13.42%、B+OV16.17%；每回答删除当前不存在包BOV0.8748、B+OV0.4698。B+OV不是全面更优：DeepSeekCoder它更慢（2.2691对1.7234秒），Qwen3过滤后无包更高（24.74%对14.33%）；模型级明细必须一并报告。两个后置验证器均不重生成，额外LLM token=0，模型自身输出长度另报。

## 2026-09-25 01:07 UTC：Qwen3共同协议补测完成与汇总修正

- GPU0 Base/PackMonitor禁思考对照在00:58:33 UTC完成1000/1000条；脚本同一时刻再次检测GPU0显存仅1 MiB，才启动BOUND fold A锚点，01:03:28 UTC完成500/500条。两个阶段及原有DeepSeekCoder/Llama锚点均无生成错误。GPU1未使用。
- 首次三模型汇总发现Qwen3 BOUND锚点被误指向保留的旧思考模式文件，形成虚假的100%无包。根据原始行核查后修正文件选择条件，并新增runtime `disable_thinking=true`校验；重新运行汇总，Qwen3正确的BOUND-A锚点Sample-HR36.4%、Package-HR21.29%、Valid-Rate86.8%、无包0%、交付0.5584秒/答，不再是旧文件的0%/100%假象。
- 最终原生协议三模型等权Base/PackMonitor/BOUND-A：Sample-HR分别54.87%/0.53%/41.93%；Package-HR 28.21%/0.20%/20.18%；Valid-Rate 81.07%/97.40%/89.80%；无包3.47%/2.40%/2.20%；交付0.9696/1.0869/1.0277秒/答。PackMonitor相对同协议Base的输出token三模型等权多1.79个/答、交付多0.1174秒/答；不能推断原纯包名协议亦如此。详见`packmonitor_native_metrics_summary.json`。

## 2026-09-25 01:11 UTC：最终核验与中文报告交付

- 再次运行原生PackMonitor三条件汇总：检查各模型每条件500条、100个预定prompt×5次生成、无重复key、三条件同prompt—generation seed匹配；Qwen3明确引用`_nothink_full`的Base/PackMonitor与BOUND-A两个来源文件，并验证BOUND-A runtime确实关闭思考。`pending_models=[]`；错误旧文件及GPU1被中断前缀保留，但未进入正式表。
- 全量主对照由无`--allow-partial`的汇总产生，Base/BOV各9420条、BOUND/B+OV各37680条；`validate_outputs.py`对Base/BOV逐回答内容、seed、候选与保留规则通过；`summarize_uniform_cost.py`对12个BOUND fold条数、seed、阶段加和及prompt任务集合通过；相关Python脚本`py_compile`通过。
- 更新中文`design_and_results.md`：第8.1节给出四方法同边界质量、过滤后无包、删除无效包、输出/额外token、HTTP次数与分段/总成本；第8.2节给出原生PackMonitor三条件及模型级结果、Qwen3协议修正和限制。旧第7节标题明确为历史阶段追溯，避免与最终同边界结果混读。
- 未新增GPU2/3任务；本次用户GPU规则生效后，GPU1出现其他占用即终止本实验进程，后续新任务只在GPU0确认空闲后启动并在阶段切换再次确认。没有删除原始或失败前缀数据。

## 2026-09-25 04:56 UTC：整理设计与结果文档

- 按用户要求重组`design_and_results.md`，从“计划—历史阶段结果—新结果”交叉叙述改为“结论摘要→两个不可混合的协议→主实验数据/在线流程/指标→主实验结果与模型差异→PackMonitor共同协议→rebuttal结论边界→历史口径和复算入口”。删除已过时的待执行预算与实验步骤语气；未完成的语义审计、安装/导入测试、缓存敏感性及新B+OV cutoff重标明确放入证据缺口，而非写成既有结果。
- 从`filter_comparison_summary.json`与`packmonitor_native_metrics_summary.json`独立复核三模型等权Sample-HR、Package-HR、Valid-Rate、无包率和交付时延；检查主实验BOV 1.7643秒、B+OV 1.7330秒、共同协议PackMonitor 0.53% Sample-HR与保存结果一致。保留37,680/9,420回答分母、四折Package-HR聚合、Qwen3禁思考有效重测、网络未知和历史11.30秒不可比较等关键限制。
- 此轮只编辑中文Markdown、读取保存结果，未启动任何GPU或重新联网查询。原始结果和脚本未修改。
