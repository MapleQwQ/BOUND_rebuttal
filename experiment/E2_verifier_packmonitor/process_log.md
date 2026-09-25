# E2——实验过程记录

本文件按时间顺序追加，记录外部依赖版本、兼容性尝试、运行命令、失败、状态机决策和结果版本。

## 2026-09-23

- 将 PackMonitor 从可选项提升为 E2 的重点对照和首个兼容性任务。
- 将“同一初始 generations”改为方法内共享：Base 分支共享 Base 初始回答，BOUND 分支共享 BOUND 初始回答。
- 明确 PackMonitor 必须重新约束解码，不能用旧回答后处理模拟。
- 新增 repair 后全候选重新验证和超预算后的显式终态。
- 删除“不可联网即天然优于 PackMonitor”的论证；改为测量约束解码依赖、延迟、内存、覆盖和 utility。
- 明确 one-shot repair 不是完整 coding agent 实验。

### 小规模实验启动记录

- 已完整检查 E2 设计与现有输出。现有目录尚无 E2 执行脚本和结果文件。
- 确认 `knowledgeEdit/results/robust_nonedit_highrisk_20260605` 已保存三个论文模型、四个 BOUND folds 的 held-out 高风险集 Base/BOUND 回答；每个 prompt 每条件均有 5 次生成，包级 `valid`/`hallucinated` 标签已随输出冻结。
- 数据盘点结果：DeepSeekCoder、Qwen3、Llama-3.1 的 eligible pool 分别为 541、409、934 个 prompts；同一模型的 Base 回答在四折间一致，可只保留一份 Base 而不伪造四份独立观测。
- 已决定第一阶段从每个模型固定抽取最多 100 个 prompts，复用已有回答运行无需 GPU 的 post-hoc verifier。该阶段明确不冒充 PackMonitor 或 one-shot repair。
- 已新增 `script/run_posthoc_verifier.py`：使用 `seed=20260923` 和 prompt ID 的 SHA-256 稳定排序冻结样本；写出 manifest、逐回答过滤记录、按模型/折汇总和缓存标签快照；脚本禁止样本数超过 100。
- GPU 检查：当前 sandbox 内 `nvidia-smi` 无法与驱动通信；主线程随后确认物理 GPU 2 空闲。下一步使用 GPU 2 做独立 smoke，但必须避免覆盖历史结果。
- CPU smoke（每模型 2 prompts）首次运行触发了数据完整性断言：`deepseekcoder/prompt 429/bound_fold_C/generation 0` 的 `packages` 不等于 `valid ∪ hallucinated`。未忽略该异常，也尚未生成正式结果；正在核对它是否属于标准库/未分类候选，并将为未知标签保留显式状态。
- 核对确认上述 residue 为历史 evaluator 有意排除在第三方包分母外的 Python 标准库名称（该例为 `ctypes`）。脚本已改为显式保存 `stdlib_passthrough`：不把它伪装成 PyPI-valid，也不在过滤时删除它；Package-HR 分母继续使用 `valid + hallucinated`，保持原指标口径。
- GPU 2 smoke 首次启动命令使用 tmux `e2_gpu2_smoke`，但进程在加载模型前立即退出；日志显示原因为实验脚本路径执行时仓库根目录未进入 `sys.path`（`ModuleNotFoundError: knowledgeEdit`）。这是启动环境错误，未占用 GPU、未产生实验数据；将通过显式 `PYTHONPATH` 重启。
- 15:00 UTC 已用显式 `PYTHONPATH` 在 tmux `e2_gpu2_smoke` 重启；shell PID `1916052`、Python PID `1916054`，物理 GPU 2 通过 `CUDA_VISIBLE_DEVICES=2` 固定。日志已完成 DeepSeekCoder 两个 checkpoint shards 的加载，正在执行 fold-A BOUND adapter 的单 prompt 贪心生成。输出限定为 `results/gpu2_adapter_smoke.json`，并标注 `included_in_metrics=false`。
- 修正标准库边界后，CPU smoke（每模型 2 prompts）通过：共 150 条回答、15 个模型/条件汇总行；Base 跨折一致性、valid/hallucinated 不重叠和缓存标签同 cutoff 内无冲突等断言全部通过。smoke 输出位于 `/tmp/e2_posthoc_smoke`，不纳入正式结果。
- 100-prompts 正式运行首次尝试在汇总前被一致性断言停止：同一模型/cutoff 内发现 6 个包在历史输出中既被标为 valid 又被标为 hallucinated（DeepSeekCoder：`flask-restful`、`werkzeug`、`aws-cdk-aws-s3`、`textacy`；Qwen3：`opentelemetry-instrumentation-asyncio`；Llama-3.1：`aws-s3`）。这表明历史逐次在线查询标签不能直接充当稳定 registry snapshot。当前已停止使用逐回答标签直接过滤；将先构建一致快照，并保留冲突与消解策略供审计后再重跑。
- 采用预先可解释的 `valid-wins` 消解：同一 cutoff 下至少一次成功查到发布时间是存在性的正证据，而失败查询可能来自瞬时网络错误；所有冲突仍完整保存在 `registry_snapshot.json`。重跑完成，正式样本为每模型 100 prompts，共 7,500 条回答、15 个模型/条件汇总行。
- GPU 2 smoke 于 15:00:44 UTC 完成并自动退出：A100 80GB 成功加载 DeepSeekCoder 与 fold-A `blast_delta.pt`，prompt 270 生成 `matplotlib, pandas, pytest, requests`。该记录只证明模型/adapter/生成链路可用，未进行 registry 验证且不纳入指标。
- 已获取并静态审计 PackMonitor 官方仓库 commit `8808362e14891fe692b17b8192ed123dff4d64d2`。发现当前环境缺少官方约束解码依赖，输入协议仅约束 Markdown bash block 中的 `pip install`，且官方 runner 尚含占位模型配置；详细证据写入 `results/packmonitor_compatibility.md`。未安装大型依赖，也未用 post-hoc filter 冒充 PackMonitor。
- 15:08 UTC 已在 GPU 2 启动可恢复的 DeepSeekCoder one-shot repair 小规模实验，tmux `e2_gpu2_repair100`、shell PID `2405487`、首段 Python PID `2405489`。流程先跑 Base/BOUND fold-A 各 2 prompts 的 smoke；成功后自动扩展至固定 manifest 的 100 prompts，每个 prompt 每条件取已有 generation 0，最多修正一次，修正后重验全部候选，残余 invalid 执行显式 `final_filter`。registry 使用 PackMonitor commit 中 706,618 名称的冻结文件；不进行网络查询。输出逐条 flush 至 `results/repair_generations.jsonl`，可按 `(condition,prompt_id)` 恢复。
- 15:10 UTC 低频检查：2-prompts smoke 已成功返回并自动进入 100-prompts 正式段，新 Python PID `2424905`；JSONL 已完成 45/200 个 condition-prompt 状态（当前仍在 Base 分支）。已观察到 `repair_verified`、`final_filter`、`explicit_refusal_or_empty` 和 `initial_verified` 四种终态，说明 repair 后重验及超预算策略均实际触发，而非只记录计划。
- 约 15:13 UTC 正式段完成并释放 GPU 2；`repair_generations.jsonl` 恰有 200 个唯一 `(condition,prompt_id)`，Base 与 BOUND fold-A 各 100 条，无重复。
- 汇总结果：Base 初始 invalid 率 0.740，repair 后过滤前仍含 invalid 0.430，最终空回答率 0.250，尝试 repair 中 0.243 达到非空且全通过；BOUND fold-A 对应为 0.190、0.080、0.180、0.526。repair 延迟 p50/p95 分别为 Base 2.969/3.467 秒、BOUND 3.047/3.374 秒。
- 结果边界：本轮只含 DeepSeekCoder、一个 BOUND fold、每 prompt 一条已有初始回答；registry 是 PackMonitor commit 随附的 deployment-name list 而非 model-cutoff 时间快照。结果写入 `repair_summary.md/json`、`repair_state_transitions.csv` 和 `latency_and_calls.csv`，不能替代三模型四折确认性比较。
- 将历史标签 post-hoc 表的状态明确降为“探索性/暂定”：虽然 `valid-wins` 能生成内部一致的描述性快照，但在 E7 使用带首发日期的冻结快照复核并完成冲突敏感性分析前，不用于最终 rebuttal claim。
- 收尾 QA：`repair_generations.jsonl` 为 200 行且 200 个唯一键，Base/BOUND fold-A 各 100；post-hoc 明细为 7,500 行；registry 冲突计数为 DeepSeekCoder 4、Qwen3 1、Llama-3.1 1。GPU 2 相关 tmux 已自然退出，卡已回报主线程可供 E3 使用。
- 16:26 UTC 为避免 GPU3 在 E3 Llama Base/A 完成后闲置，启动 Qwen3 的 E2 one-shot repair100 扩展。首次命令错误引用不存在的 `/tmp/PackMonitor/constraints/list.json`，在模型加载前即退出、未占用 GPU、未写结果；随即改用先前 DeepSeekCoder 运行实际冻结的 `/tmp/PackMonitor/HFuzzer/valid_packages/pypi_packages.json` 重启。该错误批次只保留日志，不计入结果。
- 重启会话 `e2_gpu3_qwen3_repair100_v2` 已成功加载 Qwen3 与 fold-A adapter，并产生首条 Base 状态；输出逐条写入 `results/repair_generations_qwen3.jsonl`，运行日志为 `results/gpu3_qwen3_repair100_v2.log`。仍采用固定 100 prompts、每条件已有 generation 0、至多一次 repair、repair 后全量重验和残余 invalid 最终过滤。
- Qwen3 repair100 已自然完成 200/200 个唯一 condition-prompt 状态（Base 与 BOUND fold-A 各100）；GPU3 随即启动 Llama-3.1 的同协议 repair100，会话 `e2_gpu3_llama31_repair100`，输出 `results/repair_generations_llama31.jsonl`。这样 GPU2 继续 E3 Llama folds、GPU3 扩展 E2 至第三模型，二者不争用同一卡。
- Qwen3 汇总：Base/BOUND-A 初始 invalid 率 0.710/0.120，repair 后过滤前仍有 invalid 0.290/0.030，最终空回答率 0.040/0.140，尝试中的 repair 成功率 0.592/0.750。可见存在性改善伴随 BOUND 最终空回答增加。
- Llama-3.1 repair100 随后完成 200/200 并汇总：Base/BOUND-A 初始 invalid 率 0.700/0.310，repair 后过滤前仍有 invalid 0.280/0.120，最终空回答率 0.010/0.200，repair 成功率 0.600/0.613。三模型都证明“一次 repair”不能强制保证有效，且后两模型 BOUND 的空回答副作用明显。
- GPU3 随即转入预先定义的 fold sensitivity：DeepSeekCoder fold-B repair100，会话 `e2_gpu3_deepseek_foldb_repair100`。脚本新增显式 `--bound-condition`，避免把 fold-B 结果错误标成 fold-A；Base 仍用于同 manifest 配对校验。
- DeepSeekCoder fold-B sensitivity 完成：Base/BOUND-B 初始 invalid 率 0.740/0.340，repair 后过滤前残余 invalid 0.430/0.220，最终空回答率 0.250/0.080，尝试中的 repair 成功率 0.243/0.324。与 fold-A 相比，fold-B 残余 invalid 明显更高，提示 E2 同样存在 fold 异质性。
- GPU3 继续无缝运行 Qwen3 fold-B repair100（`e2_gpu3_qwen3_foldb_repair100`）；输出使用独立文件并标记 `bound_fold_B`，不覆盖 fold-A 结果。
- Qwen3 fold-B sensitivity 完成：Base/BOUND-B 初始 invalid 率 0.710/0.120，repair 后过滤前残余 invalid 0.290/0.030，最终空回答率 0.040/0.450，repair 成功率 0.592/0.750。BOUND-B 虽减少不存在包，但 45% 最终空回答是严重 utility guardrail 退化，必须与幻觉指标同时报告。
- GPU3 随即运行 Llama-3.1 fold-B repair100（`e2_gpu3_llama31_foldb_repair100`），继续按模型顺序补齐第二折 sensitivity，而不根据结果选择模型或 adapter。
- Llama-3.1 fold-B sensitivity 完成：Base/BOUND-B 初始 invalid 率 0.700/0.410，repair 后过滤前残余 invalid 0.280/0.140，最终空回答率 0.010/0.340，repair 成功率 0.600/0.634；再次出现存在性错误下降但空回答显著增加。
- GPU3 继续进入 fold-C 顺序，先运行 DeepSeekCoder fold-C repair100（`e2_gpu3_deepseek_foldc_repair100`）。这是补齐四折 sensitivity 的既定顺序，不依据前述结果选择折。
- DeepSeekCoder fold-C 完成：Base/BOUND-C 初始 invalid 率 0.740/0.180，repair 后过滤前残余 invalid 0.430/0.070，最终空回答率 0.250/0.070，repair 成功率 0.243/0.611。
- E3 三模型五条件全部结束、GPU2 释放后，E2 fold-C sensitivity 改为两卡并行：GPU2 运行 Qwen3 fold-C（`e2_gpu2_qwen3_foldc_repair100`），GPU3 运行 Llama-3.1 fold-C（`e2_gpu3_llama31_foldc_repair100`）。两者均为固定100 prompts并写入独立结果文件。
- fold-C 并行任务完成。Qwen3 Base/BOUND-C 的残余 invalid 为 0.290/0.030、最终空回答率 0.040/0.280；Llama-3.1 为 0.280/0.170、最终空回答率 0.010/0.000。后者与 folds A/B 的空回答退化方向不同，再次说明必须报告逐折而非只挑选单折。
- 最后一轮 fold-D 已接续：GPU2 顺序运行 DeepSeekCoder→Qwen3，GPU3 运行 Llama-3.1。全部使用独立文件和 `bound_fold_D` 标签；完成后将形成三模型四折的 E2 repair sensitivity。
- fold-D 三项均完成 200/200 行，至此三模型 A/B/C/D repair sensitivity 全部结束：12 个 BOUND fold 条件各100 prompts；每个模型的 Base 配对结果也保留在逐折文件中，但总体汇总只取 fold-A 的一份 Base，避免重复计权。
- 新增 `script/summarize_all_repair_folds.py` 并生成 `results/all_models_four_folds_repair.md/json`。四折 BOUND macro 相对 Base 的“初始 invalid→repair 后残余 invalid→最终空回答”为：DeepSeekCoder `0.295→0.163→0.092`（Base `0.740→0.430→0.250`）；Qwen3 `0.155→0.055→0.260`（Base `0.710→0.290→0.040`）；Llama-3.1 `0.382→0.135→0.135`（Base `0.700→0.280→0.010`）。存在性错误均下降，但后两模型空回答显著增加，不能宣称无 utility 代价。
- GPU2/GPU3 的本轮 E1/E2/E3 队列均已自然结束；没有异常 seed 重跑、没有依据效果选择 folds，所有中间 JSONL、日志和失败记录均保留。
- 17:15 UTC 继续 PackMonitor 原生约束解码兼容性工作。再次核验 `/tmp/PackMonitor` HEAD 为冻结的官方 commit `8808362e14891fe692b17b8192ed123dff4d64d2`，工作树无本地修改。官方实现入口为 `HFuzzer/Framework/packmonitor_generate.py`，通过 `LLMatcher.compute_logit_bias()` 在逐 token 生成中屏蔽不允许 token，属于真实生成中约束而非 post-hoc 过滤。
- 当前 EasyEdit Python 环境缺少官方固定的 `llguidance==1.1.0` 与 `guidance-stitch==0.1.5`；`torch` 和 `transformers` 已存在。官方完整 `requirements.txt` 包含大量与最小约束 smoke 无关的依赖，因此先只隔离安装这两个直接依赖，避免污染主环境。
- 静态复核发现冻结提交的 grammar 存在明显标识符拼写不一致：声明为 `NATURAL_LANG`，`start` 规则却引用 `NATATURAL_LANG`。将先保存官方原样 grammar 的失败证据；若依赖可用，再在实验包装脚本中仅修正该拼写并显式标为 compatibility patch，不修改 `/tmp/PackMonitor` 官方工作树，也不把补丁版冒充零修改复现。
- 已将 `llguidance==1.1.0` 和 `guidance-stitch==0.1.5` 隔离安装到 `/tmp/packmonitor_deps`，未修改 EasyEdit 环境。使用 DeepSeekCoder 原 tokenizer 构造 matcher 的原样复现确实返回 `unknown name: "NATATURAL_LANG"`；仅将该引用改为 `NATURAL_LANG` 后 matcher 正常、未报错。完整错误将写入 runtime 结果文件。
- 使用官方随附 `pypi_packages.json` 的 706,618 个名称测试补丁版完整 grammar：grammar 约 12.98M 字符，构建 matcher 用时约 5.41 秒，整段进程峰值 RSS 约 1.55 GiB，首步 logit bias 计算约 0.001 秒；说明依赖与完整词表本身可运行，下一步进入真实模型逐 token 约束 smoke。该构建只验证约束引擎，不计入 Base/PackMonitor 生成指标。
- 新增 `script/run_packmonitor_native_smoke.py`：冻结 E2 manifest 排序最前的 5 个 DeepSeekCoder unseen prompt IDs（429、3896、3151、4369、1728），统一转换为官方支持的 Markdown `bash` + 单行 `pip install` 协议；Base/PackMonitor 共用同一模型、任务、词表、`max_tokens=64` 和 greedy decoding。脚本保存逐任务原始输出、安装区域触发、包名、invalid、empty、错误堆栈、延迟与 CUDA 峰值，并在启动时再次保存官方原样 grammar 错误证据。
- 17:37 UTC GPU 复核：GPU2 正运行 E3 confirmatory-200 的 DeepSeekCoder Base（PID 4032990，约 13.5 GiB），GPU3 也运行 E3 Qwen3 队列，其余 GPU 约占 70 GiB。为避免并发模型加载改变 E3 时延/显存与可复现性，PackMonitor 未抢占显卡。新增 `script/run_packmonitor_after_e3_gpu2.sh`，将由 tmux 低频等待 `e3_confirm200_gpu2` 自然退出，再在 GPU2 启动本 smoke；等待阶段不占 GPU。
- 17:39 UTC 等待队列已启动，tmux 会话为 `e2_packmonitor_after_e3_gpu2`，等待 shell PID 4156567；实时日志为 `results/packmonitor_runtime.log`。已确认它与 `e3_confirm200_gpu2` 同时存活且当前只有等待 shell、没有加载 PackMonitor 模型。E3 会话退出后将自动执行日志中冻结的命令，不依据 E3 或 E2 效果选择任务。
- 17:45 UTC 低频复核发现首个等待会话提前退出、runtime 日志为 0 字节且没有生成结果；GPU2 的 E3 Python PID 4032990 与队列 shell PID 4032975 实际仍存活。原因定位为不同执行上下文下 `tmux has-session` 未连接到 E3 所在 tmux server，导致等待条件错误地判为结束；没有证据表明 PackMonitor 完成，因此不计为运行结果。
- 已将等待条件改为对 E3 GPU2 队列 shell PID 4032975 使用只读 `kill -0` 存活检查，每 120 秒一次。该 PID 在完整 GPU2 confirmatory queue 期间保持存活；只有它退出后才加载 PackMonitor。将以新会话重启，并在启动后核验等待 shell 仍存活。
- 17:46 UTC 二次进程级核验更正上一条中的“首个等待会话提前退出”：旧等待 shell PID 4156567 实际仍存活，只是外部 `tmux ls` 没有连到其 socket，且 0 字节日志是正常等待状态，不是 PackMonitor 启动失败。为避免两个等待器在 E3 完成后重复加载模型，已仅停止旧等待 shell/父 shell（4156567/4156563），未触碰 E3；保留修正版 v2 等待 shell PID 310864。核验时 E3 队列 PID 4032975 和 v2 等待器均存活，且没有 PackMonitor Python 进程。
- 18:18 UTC 移交主线程前最终核验：`e2_packmonitor_after_e3_gpu2_v2` 与 `e3_confirm200_gpu2` 均存活；等待 shell PID 310864（父 shell 310853），E3 GPU2 当前 Python PID 697732、约 13.7 GiB。`packmonitor_runtime.log` 仍为 0 字节，符合尚未启动 PackMonitor 的预期。E3 队列 shell 4032975 退出后，等待器将自动运行 5-task Base/PackMonitor smoke，并写 `packmonitor_runtime_generations.jsonl`、`packmonitor_runtime_summary.json` 与实时日志；后续低频监督由主线程接管。
- 20:04 UTC E3 的 GPU2 队列自然结束后，等待器按冻结顺序启动并完成 PackMonitor 原生约束解码 smoke。共同支持的 5 个 DeepSeekCoder 安装命令任务共得到 10 条回答；Base 的安装区域触发率为 1.00、含不在冻结 registry 中包名的回答率为 0.20、空包率为 0，PackMonitor 对应为 1.00、0、0。平均生成时延由 0.433 秒增至 1.286 秒（样本很小，不作稳定性能估计），模型加载 5.31 秒，CUDA 峰值 allocated/reserved 为 12.805/12.826 GiB。
- 原生 smoke 保留了官方 grammar 原样失败证据，并且只应用 `NATATURAL_LANG→NATURAL_LANG` 的最小兼容补丁；官方工作树未修改。结果位于 `packmonitor_runtime_generations.jsonl`、`packmonitor_runtime_summary.json` 和 `packmonitor_runtime.log`。这是真实逐 token 约束解码，不是后处理，但规模仅 5 个任务，不能替代主统计比较。
- GPU2 已空闲。为补齐设计中的组合问题，已扩展同一 runner 支持在 PackMonitor 已加载模型上注入冻结的 BOUND fold-A delta，计划立即在同一 5 任务上比较 `BOUND` 与 `BOUND + PackMonitor`；新结果使用独立文件，绝不覆盖 Base/PackMonitor smoke。
- 20:08 UTC 组合 smoke 完成：同一 5 任务上，BOUND 与 BOUND+PackMonitor 的安装区域触发率均为 1.00、invalid answer rate 均为 0、空包率均为 0；平均时延为 0.395/1.330 秒。该结果证明 BLAST delta 与原生 PackMonitor 约束可以组合，但由于 BOUND 在这 5 条上已经全通过，无法从该 smoke 估计增量收益。
- 为利用空闲 GPU2 并把原生对照提升到用户指定的小规模上限，已冻结 `manifest.json` 中 DeepSeekCoder 的同一 100 prompts，新增 `run_packmonitor_native_100_gpu2.sh`。队列顺序固定为 Base vs PackMonitor、BOUND fold-A vs BOUND fold-A+PackMonitor，共 400 条原生生成；仍使用相同模型、任务、greedy seed/protocol 和 706,618 名称 registry。
- 20:11 UTC 原生 100-task 队列已在 GPU2 启动（tmux `e2_packmonitor100_gpu2`）；20:12 UTC Base/PackMonitor 阶段已写出67/200条逐条件记录，模型正常加载且未见异常。完成后将自动进入 BOUND-A/BOUND-A+PackMonitor，不根据中间结果改变任务或顺序。
- 20:13 UTC Base/PackMonitor 100-task 阶段完成并自动进入 BOUND 组合阶段。Base→PackMonitor 的 invalid-answer rate 为0.45→0.04，empty为0.02→0.01，安装区域触发率为0.98→0.99，平均时延为0.603→0.744秒。PackMonitor剩余4个invalid均由固定64-token预算在包名中途截断形成（如`slack-`、`google-p`），不是词表允许了未注册完整名称；这说明生成中约束仍需配合终止/截断后验证，不能宣称强制后必为零错误。
- 20:16 UTC BOUND组合100-task阶段完成。BOUND→BOUND+PackMonitor 的invalid-answer rate为0.29→0.04（配对prompt bootstrap差值-0.25，95% CI [-0.35,-0.16]），empty均为0，安装区域触发率均为1.00，平均时延为0.549→0.708秒。Base→PackMonitor的配对invalid差值为-0.41，95% CI [-0.51,-0.31]。汇总已写入 `packmonitor_native100_summary.md/json`。
- 由于64-token条件下的4个PackMonitor residual invalid均为末尾截断，立即启动一个明确标为事后探索性的`max_tokens=128`敏感性（同一100 prompts、Base/PackMonitor），用于区分约束机制失败与固定输出预算截断；不替换64-token主结果，也不依据敏感性结果重定义主要协议。GPU2在主队列结束后无空档接续该任务。
- 20:19 UTC 128-token敏感性完成：Base/PackMonitor invalid-answer rate为0.47/0.03，残余3例仍是在重复合法包名时耗尽预算并截断为`collectd-ceph`、`slack-`、`google-p`。这排除了“只需把64简单翻倍即可保证完整”的解释；主64-token结果保持不变。
- GPU2随后仅对64-token下的4个截断case启动256-token定向诊断。该样本由结果触发，严格标为探索性机制排查，不纳入100-task效应估计；目的只是核验matcher在外部强制停止时是否会留下未闭合安装命令/包名前缀。
- 20:22 UTC 256-token定向诊断完成：4个case中PackMonitor仍有2个invalid，且平均时延升至8.95秒；逐回答继续表现为重复合法名称直到外部预算截断。这进一步支持“需要终止完整性检查/最终重验”，但由于case是事后选取，不作总体率估计。GPU2任务至此自然结束。
- 最终QA通过：原生主对照两个JSONL均为200行（各100 prompts×2条件），128-token敏感性200行，256-token定向诊断8行；配对汇总可复算，全部E2 Python脚本通过`py_compile`。设计文档、主计划和过程日志已同步，E2小规模主任务标记完成。

## 2026-09-24 03:24 UTC：详细方法与结果文档更新

- 按用户要求扩充`design_and_results.md`，记录三个分支的实际干预、固定抽样、Base去重、registry口径、repair提示与终态、PackMonitor版本/最小补丁、指标分母及统计方法。本次只更新文档，未启动新生成或改写实验数据。
- 核对`all_models_four_folds_repair.json`，补充四折绝对差异及逐折残余invalid/空回答表；明确1,500个去重任务—条件记录不等于1,500次新增模型调用。
- 按分析验证技能检查结论边界：已有PackMonitor时加入BOUND的invalid率为4%→4%，未显示进一步下降；E2新输出尚未完成充分性/相关性标注，不能直接替用E1原回答标签。
- 补充64/128/256-token结果、时延解释限制及可复现文件索引；256-token仅为4个事后失败案例诊断，不作为总体估计。截断案例审计明确对应Base+PackMonitor，未泛化至未逐例核验的组合失败案例。
- 更正过时的“下一步smoke/冻结版本”描述，保留原运行日志作为历史记录；已完成小规模名称验证不代表全部设计终点已完成。

## 2026-09-24 03:30 UTC：逐项核对审稿问题与E2证据

- 阅读`icse rebuttal_question.md`的A/B/C全部30项意见，并在`design_and_results.md`新增逐项覆盖矩阵，区分已有证据、部分覆盖、未覆盖及下一步补证。不把其他实验的计划当作已完成结果。
- 复核原生PackMonitor机器可读汇总：Base/BOUND/两种PackMonitor组合分别为45%/29%/4%/4%；强调外部约束有效不等于编辑在已有约束上有增量收益。
- 按分析验证技能收紧A-Q1/C-Q1结论，分别讨论验证有效性、repair调用/残余失败下降、已有PackMonitor上的编辑增量。明确同token上限不等于同延迟/计算预算。
- 记录A-Q2/B-Q3/C-Q4仍缺E2最终回答语义与充分性标签、来源覆盖、执行及原本适合任务子集证据；empty不直接等于拒答，列表成员不等于完整现实PyPI时间有效性。
- 补充缺口优先级、不应使用的结论、部署定位边界和中文rebuttal事实草稿；本次仅修改文档与日志，未启动实验或改动数据、论文及公开artifact。

## 下一步

- 对E2最终输出按E1协议另做充分性/相关性审计，并披露是否使用agent模拟标注。
- 联动E7复核历史标签冲突、补齐model-cutoff与共享评估日期双口径。
- 为三模型四折repair补充配对差异区间；若需要成本或任务成功结论，再补成本拆分与隔离功能测试。
