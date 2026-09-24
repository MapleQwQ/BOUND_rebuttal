# E3——实验过程记录

本文件按时间顺序追加，记录数据恢复、排除、去重、样本量冻结、生成批次、失败和结果版本。

## 2026-09-23

- 将实验从“自然 prompt 分布”更名为“未按风险筛选的共同提示集”。
- 明确该集合仍是合成 benchmark，不能代表真实部署分布。
- 新增跨模型、跨 fold 编辑/定位/调参 prompts 的并集排除和近重复审计。
- 新增被编辑模型 × 风险集合来源的交叉评测矩阵。
- 将“至少 1,000 prompts”硬门槛改为基于 CI 精度与预算的预注册样本量。
- 将存在性正确与任务适配充分分成两个回归层次，并记录使用同批输出分层时的选择偏差。
- 第二轮设计将主测试集严格限定为 leakage exclusion 后 eligible pool 的一次不放回简单随机样本；禁止按 risk、popularity、token length 或显式包名设置主样本配额。
- 将风险、流行度和 token length 降为主随机样本的事后 secondary analysis；长尾 oversampling 只能建立独立 secondary sample，并用 inclusion-probability weights 恢复总体估计。
- 将 risk strata 的来源冻结为 E3 之前已有的历史 5 次 screening generations；E3 fresh Base/BOUND 5 次 generations 只用于最终指标，禁止同批定义“原本正确”再比较。
- 将“原本正确”操作化拆为 historical registry-clean 和 E1/可信 reference 支持的 task-appropriate；E3 只在 nested subset 复用 E1 人工协议。
- Primary endpoint 收敛为 unfiltered shared set 上 Base→BOUND Sample-HR 绝对差；Package-HR 降为重要 secondary。
- 区分 `hallucination-containing responses per 1,000 generations` 与 `hallucinated package mentions per 1,000 generations`，不再使用含糊的 hallucinated events。
- 新增 historically clean prompts 上的 Induced Hallucination Rate、fresh Base 对照和同 seed 的 clean→hallucinated transition。
- 样本量由历史 prevalence、prompt-level variance、目标 CI 半宽及预算在 generation 前冻结；禁止根据 E3 效果方向连续扩样。
- 写入优先配置：200–300 shared prompts × 3 models × Base+4 folds × 5 generations；预算不足时优先保留 prompt coverage，改为预先指定单 fold，并在较小固定子集跑四折 sensitivity。
- 冻结 common-random-number seed schedule：同一 `(prompt_id, replicate_id)` 的 Base 和所有 BOUND folds 共用 seed；异常 seed 不得按结果重采样。
- 将 generation 与 validity labeling 解耦，E7 不阻塞生成；每条输出后续同时保存 model-cutoff validity 和共同 frozen PyPI snapshot validity。
- Cross-model risk matrix 降为 Secondary/P1；每个来源风险集目标 100 prompts，算力不足优先 6 个 off-diagonal cells。
- 近重复审计改为确定性优先；embedding 默认仅补充审计，不自动删除，若启用必须冻结模型、阈值和人工复核规则。
- 明确全量 E3 只需自动指标；Recommendation Adequacy、Task-Relevant Precision 和 slot coverage 仅用于预注册的 E1 nested subset，不阻塞主实验。
- 用户要求 E1/E2/E3 同时启动，并为 E3 分配 GPU3；GPU 检查显示 GPU2、GPU3 均为空闲，其他 GPU 已被外部进程占用。
- 从 Spracklen 官方仓库下载 `Data/Python/LLM_LY.json` 到临时目录，SHA-256 为 `843fae63874c52b1bfa9b08f833bfea72b2ad5d77575210447d2d2f35e44b733`，共恢复 4,892 条 prompts。
- 新增 `script/prepare_small_unfiltered_manifest.py` 并以 seed `20260923` 生成 100-prompt 小规模简单随机 manifest。当前 preliminary exclusion 汇总 17,719 个 normalized keys，排除原池 exact/normalized overlap 1,844 条、池内 exact duplicate 4 条，剩余 eligible 3,044 条后抽取 100 条。
- 当前小规模 manifest 仅完成 exact/normalized-exact leakage exclusion；source-group 和 lexical near-duplicate 尚未完成，因此明确标记为 preliminary，不作为最终确认性 E3 主集合。
- 已在 tmux 会话 `e3_gpu3_small100` 启动 DeepSeekCoder + fold-A BOUND 的 100 prompts × 5 generations preliminary run，固定使用 GPU3，输出为 `results/deepseekcoder_foldA_bound_small100.json`，逐 prompt 可恢复详情写入同名 `.details.jsonl`，运行日志为 `results/e3_gpu3_small100.log`。启动后已确认模型进程占用约 13 GiB 显存并正在加载 checkpoint；后续采用较长检查间隔。
- 运行开始后发现通用评估脚本未在“模型加载完成后”显式重置随机 seed，首个 BOUND run 因此保留为吞吐/稳定性 preliminary，不进入 common-random-number 配对主结果。已扩展 `scripts/eval_recommendation_nonedit_highrisk.py`，新增 `base` 条件和 `--seed`，并在模型加载后调用统一 `set_seed`。
- 为避免 GPU3 在首轮结束后闲置，启动 tmux 会话 `e3_gpu3_queue`：每 60 秒仅在本机检查首轮最终文件；完成后自动顺序运行 fresh Base seed-42 和 fold-A BOUND seed-42，二者使用同一 100-prompt manifest、相同 5 generations 和 decoding 配置。对应日志为 `results/e3_gpu3_base_seed42.log` 与 `results/e3_gpu3_bound_seed42.log`。
- 在队列进入 Base/配对 BOUND 前进一步实现逐 generation common seeds：`seed = SHA256(global_seed | prompt_id | generation_id)` 的前 32 bits；每条 trial 保存实际 seed。已对修改后的评估脚本和两个 manifest 脚本做无字节码 AST 语法检查并通过。首轮已启动进程仍不含此补丁，因此继续只作 preliminary；队列中的 Base/BOUND 将使用新规则。
- GPU3 preliminary fold-A 已完成 100/100 prompts 并自动切换至 fresh Base seed-42 配对任务；该 Base 运行已确认写入逐 generation seeds。
- E2 GPU2 repair100 完成并释放显卡后，立即启动 E3 tmux `e3_gpu2_folds_bcd`，顺序运行 DeepSeekCoder B/C/D 三个 folds 的同一 100-prompt、5-generation、seed-42 配置；GPU3 队列负责 Base 与 fold-A。这样可在小规模阶段形成一个模型的完整四折 common-seed sensitivity，同时持续占用 GPU2/3。日志分别为 `e3_gpu2_foldB_seed42.log`、`foldC` 和 `foldD`。
- 检查首个 preliminary JSON 时发现通用评估脚本的顶层 `edited_*` summary 没有从已保存 trials 正确累计，出现 `edited_sample_valid_rate=0`，但 `.details.jsonl` 中逐条答案、packages、valid/hallucinated 均完整。禁止使用该顶层 summary。
- 新增 `script/summarize_small_e3.py`：全部条件从 `.details.jsonl` 重新累计 Sample-HR、Package-HR、per-1000、Empty、Avg/Distinct packages 和 concentration；验证逐 generation seed 对齐，并以 prompt 为 cluster 对四折 macro Sample-HR 绝对差做 bootstrap。该脚本将在 Base+A/B/C/D 全部完成后运行。
- 低频监督确认 GPU3 的 DeepSeekCoder fresh Base 与 fold-A seed-42 均已100/100自然完成；GPU2 的 fold-B 已完成，fold-C 进行到81/100，之后自动进入 fold-D。
- GPU3 释放后立即启动 tmux `e3_gpu3_qwen3_base_a`，在同一 preliminary small100 manifest 上顺序运行 Qwen3 fresh Base 与 fold-A BOUND（各5 generations、相同逐 generation seed schedule）。这样在等待 DeepSeekCoder fold-D 时继续补充第二模型，不让 GPU3 空置。
- 15:19 UTC 将 GPU2/GPU3 队列监督移交为低频检查。接管快照：GPU3 fresh Base seed-42 已完成 85/100 prompts，随后将自动运行 fold-A seed-42；GPU2 fold-B seed-42 已完成 32/100，随后按 B→C→D 自动串行。两个 tmux 会话均存活，details 持续增长，暂未发现异常退出。后续检查间隔设为至少 5 分钟，只在条件切换、异常或完成时追加记录。
- 15:26 UTC 状态切换：GPU3 fresh Base seed-42 已完成 100/100，并自动进入 fold-A seed-42；fold-A 当前 27/100。GPU2 fold-B 为 82/100，尚未切换。两个队列进程持续运行。Base 顶层 JSON 仍显示已知的错误 `edited_sample_valid_rate=0`，后续只从 100 行 details 重算。
- 15:33 UTC 状态切换：GPU2 fold-B seed-42 已完成 100/100，并自动进入 fold-C（当前 29/100）；GPU3 fold-A 为 63/100。B 的顶层 summary 同样保留已知累计错误，details 行数完整。两个队列继续运行，无需恢复。
- 15:38 UTC 状态切换：GPU3 fold-A seed-42 已完成 100/100，`e3_gpu3_queue` 自然退出，GPU3 可释放；Base/A details 均完整。GPU2 fold-C 为 81/100，队列仍存活，完成后将自动进入 fold-D。
- 15:39 UTC GPU3 随即启动 Qwen3 Base→fold-A 的 seed-42 串行队列 `e3_gpu3_qwen3_base_a`；接管时 Base 为 2/100。它使用与 DeepSeekCoder 相同的 preliminary 100-prompt manifest 和 common-seed schedule。GPU2 DeepSeekCoder fold-C 已到 98/100，即将切换 fold-D。DeepSeek四折完成后立即单独汇总，不等待 Qwen3。
- 15:40 UTC 状态切换：DeepSeekCoder fold-C 已完成 100/100，GPU2 自动进入 fold-D（当前 6/100）。另启动等待型 tmux `e3_gpu2_qwen3_queue`：检测到 DeepSeek fold-D 最终 JSON 后，才会在 GPU2 顺序运行 Qwen3 folds B/C/D，避免抢卡。GPU3 Qwen3 Base 当前 23/100。
- 15:51 UTC 状态切换：Qwen3 Base seed-42 已完成 100/100，GPU3 自动进入 Qwen3 fold-A（当前 54/100）。DeepSeekCoder fold-D 为 63/100；Qwen3 GPU2 B/C/D 等待队列尚未触发，未发生 GPU 争用。
- 15:58 UTC DeepSeekCoder fold-D 完成 100/100，至此 fresh Base 与 A/B/C/D 五个 seed-42 conditions 均有完整 100 prompts × 5 trials；GPU2 DeepSeek 队列自然退出，Qwen3 B/C/D 等待队列将按分钟检查后接管 GPU2。Qwen3 Base/A 也已完成，GPU3 随即启动 Llama-3.1 Base→A 队列 `e3_gpu3_llama_base_a`；另预置 Llama B/C/D 等待队列，在 Qwen3 D 最终文件出现后再接管 GPU2。
- 已立即对 DeepSeekCoder 运行 `summarize_small_e3.py --bootstrap 2000 --seed 20260923`。QA：100 个共同 prompt、每条件 500 trials、common-seed mismatch=0。结果为 Base Sample-HR 0.030；BOUND A/B/C/D 分别 0.034/0.060/0.030/0.106，四折 macro 0.0575；主差值 `BOUND-Base=+0.0275`，prompt-bootstrap 95% CI `[+0.0010,+0.0525]`。即该 preliminary unfiltered sample 上 BOUND 平均增加而非降低 Sample-HR；不得隐瞒或反向解释。
- 同时观察到 fold-A empty rate 0.272（Base 0.060），折间异质性明显。当前 manifest 仅完成 exact/normalized leakage exclusion，validity 仍为 model-cutoff 在线查询口径，故该负结果定位为需要严肃报告的 preliminary evidence；必须完成 near-duplicate audit 和共同 deployment snapshot 后再决定确认性结论，不能根据该结果更换 seed、fold 或扩样。
- 16:03 UTC 多模型队列状态：Qwen3 Base/A 均为 100/100；GPU2 已进入 Qwen3 fold-B 并到 99/100，后续自动 C/D。GPU3 Llama-3.1 Base 为 51/100，后续自动 fold-A。Llama B/C/D 等待队列 `e3_gpu2_llama_queue` 已建立，仅在 Qwen3 fold-D 最终 JSON 出现后触发。
- 16:10 UTC 状态切换：Qwen3 fold-B 完成 100/100，GPU2 已进入 fold-C（51/100）；Llama-3.1 Base 完成 100/100，GPU3 已加载 fold-A 并开始生成。两个下游队列均按计划运行。
- 16:15 UTC 状态切换：Qwen3 fold-C 完成 100/100，GPU2 已进入 fold-D（14/100）；Llama-3.1 fold-A 为 35/100。Qwen3 D 完成后将立即汇总五条件，并由等待队列接续 Llama B/C/D。
- 16:25 UTC Qwen3 fold-D 与 Llama-3.1 fold-A 均完成 100/100。GPU2 Qwen 队列自然退出，Llama 等待队列已进入 fold-B（14/100）；GPU3 Llama Base/A 队列自然退出。
- 已扩展汇总脚本的 `--model-name` 元数据参数，避免 Qwen/Llama 输出被错误标成 DeepSeekCoder；统计实现与 DeepSeek 完全相同。Qwen3 2,000 次 bootstrap 汇总完成：Base Sample-HR 0.022；A/B/C/D 为 0.002/0.002/0.012/0.010，四折 macro 0.0065；差值 `-0.0155`，95% CI `[-0.039,+0.002]`，seed mismatch=0。方向上下降，但区间跨 0，不能声称已证明改善。
- Qwen3 utility guardrail 有明显风险：Base empty rate 0.228，fold B/C/D 分别 0.538/0.370/0.282；必须与 E1 Adequacy 及任务槽覆盖共同解释，不能只报告低 Sample-HR。
- 16:43 UTC 状态切换：Llama-3.1 fold-B 完成 100/100，GPU2 自动进入 fold-C（15/100）；Base/A/B 已完整。GPU3 无后续 E3 任务，GPU2 队列继续 C→D。
- 16:54 UTC 状态切换：Llama-3.1 fold-C 完成 100/100，GPU2 自动进入最后的 fold-D（7/100）。队列存活且 details 正常增长；下一次采用较长间隔检查，D 完成后立即汇总并释放 GPU2。
- 17:04 UTC Llama-3.1 fold-D 完成 100/100，GPU2 队列自然退出，GPU2/GPU3 的 E3 生成任务均已释放。至此三个模型的 Base+A/B/C/D 共 15 个条件全部完成；逐文件 QA 显示每个条件恰有 100 个 manifest prompt、每个 prompt 恰有 5 个 trials，合计 7,500 次生成，未发现缺失 ID、重复 ID 或缺失 seed。
- 已对 Llama-3.1 运行与前两模型相同的 `summarize_small_e3.py --bootstrap 2000 --seed 20260923`。Base Sample-HR 为 0.088；BOUND A/B/C/D 为 0.090/0.156/0.118/0.088，四折 macro 为 0.113；差值 `+0.025`，95% CI `[-0.0095,+0.0615]`，common-seed mismatch=0。点估计方向为退化，但区间跨 0，不能声称已确定存在损伤；fold-B empty rate 0.228（Base 0.032）仍是需要结合 E1 检查的 guardrail 信号。
- 三模型单独汇总均已完成。当前点估计为 DeepSeekCoder `+0.0275`、Qwen3 `-0.0155`、Llama-3.1 `+0.0250`；两模型方向为增加 Sample-HR，仅 Qwen3 方向为降低。下一步使用同一组重采样 prompt 索引计算三模型等权 macro 的配对 bootstrap，避免把三个模型或五次生成当成独立样本。
- 新增 `script/summarize_multi_model_e3.py` 并通过语法检查。该脚本要求 15 个条件的 prompt ID 集完全一致；每次 bootstrap 对三个模型、Base、四折共同使用同一组 prompt 重采样索引。2,000 次联合 bootstrap 得到三模型等权 macro：Base Sample-HR 0.0467，BOUND 0.0590，差值 `+0.0123`，95% CI `[-0.0045,+0.0270]`；Package-HR 差值 `+0.0089`；Empty rate 从 0.1067 升至 0.1835（差值 `+0.0768`）。联合区间跨 0，证据不确定，但点估计不能支持“未筛选共同集上总体改善”。综合结果写入 `results/all_models_small100_metrics.json` 与 `results/summary.md`。
## 下一步

- 恢复完整 Spracklen 数据池及稳定 prompt ID。
- 汇总所有编辑、定位、调参和调试 prompt 的排除并集。
- 生成逐步 exclusion audit，记录每一步输入、删除、剩余和原因，检查是否改变 benchmark 组成。
- 冻结 normalized exact-text、lexical candidate 和人工复核规则；暂不把 embedding 用作自动排除器。
- 仅使用历史 screening 估计 Base prevalence/variance，完成 Sample-HR 差异 CI 半宽与成本表，冻结具体 `N`。
- 冻结 sampling seed、共同 generation seed schedule、完整四折或降级单折配置和基础设施失败补跑规则。
- 冻结共同 deployment PyPI snapshot 的日期、构建方法与哈希；该步骤可与 generation 并行，不阻塞生成。
- Primary generations 启动后不得根据中间效果扩大样本或更换 fold。

## 2026-09-23：完成性审计与确认性重建

- 复核发现 preliminary small100 脚本把 `LLM_LY_edits_train/valid/test` 全部排除，其中 `test`/`valid` 包含未用于参数编辑的高风险任务；这会把“未按风险筛选”重新变成风险相关筛选。三模型7,500次结果仍保留并明确降格为 preliminary，不再作为确认性 unfiltered 主结果。
- 新增 `script/prepare_confirmatory_manifest.py`，排除范围改为仓库全部 `knowledgeEdit/results/**/edit_records.jsonl` 的实际编辑并集，覆盖24个文件、918个唯一编辑 prompts；不再排除仅属于 high-risk heldout 集但未被编辑的任务。
- 冻结 token 3-gram Jaccard 近重复规则：0.80进入候选、0.90自动排除；本次没有非exact候选达到0.80。官方数据缺少 source task/package 映射，source-group 排除不可执行并显式保留为限制；embedding不启用。
- 审计结果：原池4,892条，exact编辑重叠918条，规范化池内重复13条，eligible 3,961条；以 seed `20260926` 简单随机冻结200条到 `results/shared_prompt_manifest_confirmatory200.jsonl`。
- 写入 `results/deduplication_rule_freeze.md` 与 `results/sample_size_plan.md`；确认性配置固定为200 prompts×3模型×5条件×5次生成=15,000次，不按后续效果继续扩样或更换fold。
- 新增 `script/run_confirmatory_queue.sh` 并通过 `bash -n`。17:36 UTC 启动两条持续GPU队列：GPU2负责 DeepSeekCoder Base+A/B/C/D 后接 Qwen3 Base/A；GPU3负责 Qwen3 B/C/D 后接 Llama-3.1 Base+A/B/C/D。首批 DeepSeekCoder Base 与 Qwen3 fold-B 均已产生首条details，确认队列实际运行；后续采用至少5分钟低频检查。
- 17:57 UTC 低频检查：GPU2 的 DeepSeekCoder Base 已完整200/200并自动进入 fold-A；GPU3 的 Qwen3 fold-B 已完整200/200并进入 fold-C（检查时99/200）。两条队列均自然切换，无缺失prompt或人工重启。
- 18:07 UTC GPU3 的 Qwen3 fold-C 完整200/200并自动进入 fold-D；随后低频检查为97/200。GPU2 DeepSeekCoder fold-A为152/200。所有已完成条件均恰200行，无重复或漏行。
- 18:21 UTC GPU2 的 DeepSeekCoder fold-A 完整200/200并自动进入 fold-B；GPU3 Qwen3 fold-D 检查时162/200。队列仍按冻结顺序运行。
- 18:24 UTC GPU3 的 Qwen3 fold-D 完整200/200，至此Qwen3的B/C/D分区完成并自动切换到 Llama-3.1 Base；后续检查时Llama Base为78/200。GPU2 DeepSeekCoder fold-B同期为106/200。
- 18:42 UTC GPU2 DeepSeekCoder fold-B完成200/200并进入fold-C；18:45 UTC GPU3 Llama-3.1 Base完成200/200并进入fold-A。检查时fold-C/fold-A分别71/47，连续队列无空档。
- 19:03 UTC GPU2 DeepSeekCoder fold-C完成200/200并进入fold-D；19:05 UTC GPU3 Llama-3.1 fold-A完成200/200并进入fold-B。检查时两项分别39/26。
- 19:35 UTC DeepSeekCoder fold-D完成200/200，GPU2至此完成DeepSeekCoder五条件并切换Qwen3 Base；19:37 UTC Llama-3.1 fold-B完成并进入fold-C。检查时Qwen Base/Llama fold-C分别37/9。
- 20:04 UTC GPU2 Qwen3 Base与fold-A均完成200/200，GPU2确认性队列自然结束；DeepSeekCoder与Qwen3五条件已齐。GPU3 Llama-3.1 fold-C于19:57完成并进入最后的fold-D（检查时59/200）。
- 20:12 UTC 低频检查：Llama-3.1 fold-D 已完成123/200，GPU3 队列继续运行且 details 持续增长；其余14个确认性条件均为200/200。GPU2 同期用于 E2 原生 PackMonitor 100-task 扩展，不处于空闲状态。
- 20:22 UTC Llama-3.1 fold-D 达到200/200且最终JSON写出，GPU3队列记录`DONE`后自然退出。确认性E3的3模型×(Base+4 folds)×200 prompts×5 generations共15,000条生成全部完成；没有按中间效果更换seed、fold或扩样。随即进入双registry重标、共享prompt bootstrap和完整性QA。
- 双registry重标完成：15个输入文件、15,000条trials均写入`deployment_snapshot_labels.jsonl`与`model_cutoff_labels.jsonl`；共同snapshot SHA-256为`9cc52b886efb9488418f0a5fc2f24484088019111029b5eb9587e3b0e05a315c`，706,618个规范化名称。共同snapshot未列名回答1,380条，model-cutoff hallucination回答1,545条；未列名不自动解释为从未存在。
- 2,000次共享prompt bootstrap汇总完成。三模型等权Base/BOUND Sample-HR为0.1050/0.1025，差值-0.0025，95% CI [-0.0202,+0.0148]；Package-HR为0.0607/0.0630；Empty为0.1133/0.1828。模型差值为DeepSeekCoder -0.0035、Qwen3 -0.0185、Llama-3.1 +0.0145，方向不一致，不能支持未筛选集合上的稳定总体改善。
- historical-clean回归已按旧screening独立定义：clean提示数为149/177/122，BOUND四折macro induced hallucination为0.0641/0.0246/0.0906，clean→hallucinated transition为0.0611/0.0232/0.0844（依次为DeepSeekCoder/Qwen3/Llama-3.1）。所有15个details文件均恰200行，双标签文件均15,000行，common-seed mismatch=0。
- 最终QA通过：confirmatory manifest恰200行，15个condition details各200行，双registry标签各15,000行，指标声明的总generation数为15,000且seed mismatch为0；全部E3 Python脚本通过`py_compile`。确认性结果、限制和未运行的secondary cross-risk/E1 nested子集均已写入设计文档，未将其伪装为已完成。
