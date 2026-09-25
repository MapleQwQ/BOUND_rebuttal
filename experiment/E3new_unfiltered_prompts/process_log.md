# E3new 过程记录

## 2026-09-24：协议冻结与准备

- 用户确定：随机抽取1000条未经模型风险筛选的共同prompt；原始Base五次回答直接复用；DeepSeekCoder、Qwen3、Llama-3.1各运行4个已有BOUND folds，每提示5次；最终与replication package同结构合并并计算论文的Sample-HR、Package-HR、Valid-Rate。
- 用户确定使用GPU2/GPU3；BOUND输出上限128 tokens，与历史Base筛选脚本一致；temperature=0.7、top_k=40、top_p=0.95。已有E3 confirmatory-200 BOUND输出上限64 tokens，故本次不能直接复用；若后续发现其他完全匹配协议的输出，再逐记录核验后复用。
- 原始`LLM_LY.json`复制到本目录，SHA-256=`843fae63874c52b1bfa9b08f833bfea72b2ad5d77575210447d2d2f35e44b733`。4,892条原始记录，去重13条，排除与24份实际编辑记录重合的918条，剩余3,961条。该排除保证共同样本不包含实际编辑提示，但来源任务组、定位/调参/调试提示仍待额外审计。
- 用seed `20260924`从3,961条中简单随机不放回抽取1,000条，manifest SHA-256=`d1b28c3d52fefce0ab2c9d0d465eb6b6be9139bd78f02bb8f032e40f99beceeb`。历史Base定义的clean/low/high数量：DeepSeekCoder 776/159/65；Qwen3 879/69/52；Llama-3.1 627/233/140。样本未按风险比例配额。
- 原始Base与新BOUND的随机数流不同，虽然生成上限和主要解码参数相同，不能称为同seed逐回答配对。统计应按prompt聚类；保留历史Base和BOUND各自的5次回答。该样本仍来自合成benchmark，不代表自然开发请求分布。
- 发现既有通用评估脚本的顶层`edited_*` summary没有从trials正确累计，因此只使用逐prompt `.details.jsonl`；合并脚本将按照replication package的`summary`+`details`结构重新计算论文六项指标，同时单列 pooled、无包率与prompt聚类区间。
- 计划运行12个BOUND条件，共60,000次生成。原始Base共15,000条回答直接复用。旧confirmatory-200与本次随机样本重合58条，但token上限不同，不能使用其BOUND输出。

- 2026-09-24T07:24:16Z UTC: GPU2 START deepseekcoder_foldA; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T07:24:16Z UTC: GPU3 START qwen3_foldC; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

## 2026-09-24：吞吐优化与断点续跑

- 首轮约10分钟后，DeepSeekCoder fold A完成70/1000条、Qwen3 fold C完成123/1000条；在线PyPI JSON首发时间查询与生成串行，影响GPU利用率。暂停队列后将用同一套生成协议和原始逐prompt seed断点续跑；已写入的回答不丢弃或重采样。
- 新E3专用`run_generation.py`预加载E2new于2026-09-24取得的6,071条`dated` PyPI JSON API最早发布日期，以减少重复查询；该文件的日期提取方式与原分类函数一样取`releases[*][0].upload_time`最小值。`no_file_date`和`no_longer_on_index`不预填，仍走原查询。对于缓存未覆盖的包，分类规则与此前相同。此改动只影响包名查询成本，不改prompt、模型、适配器、解码参数或seed。后续将从原始回答重新核查标签一致性。
- 约07:55 UTC两条队列暂停时，DeepSeekCoder fold A已保存173/1000条、Qwen3 fold C已保存296/1000条。随后在GPU2/GPU3重启同名队列，按detail中的prompt ID跳过已完成任务，继续原seed；`e3new_monitor`每10分钟写入总进度。
- 第二轮吞吐观察：DeepSeekCoder fold C约每10分钟增加130–150条，Llama-3.1 fold B出现单条PyPI查询接近30秒，仍有明显串行网络等待。决定再次断点续跑，把尚未生成的回答改为先生成并保存原始文本/包列表、延后集中查询PyPI首发时间；当前`valid/hallucinated`字段在此阶段仅为临时值，**合并脚本必须统一重标全部新BOUND回答**。原始Base回答及其标签仍直接复用。已完成或部分完成的生成均保留，生成seed与协议不变。集中重标使用同一PyPI JSON API、同一首发时间提取规则与模型cutoff；查询未知项单独审计。
- 12:20 UTC左右，7个条件完整，约7,500/12,000条prompt-condition记录。启动CPU上的首轮PyPI日期缓存构建：先复制已落盘raw结果快照到`results/raw_snapshot_for_cache/`，与原始Base候选合并去重，再对既有E2new缓存未覆盖的包并发查询。GPU队列继续生成；12个条件全部完成后对新增候选再补一次查询。缓存只用于最终统一标注，不改生成内容。
- 首轮日期缓存完成：快照加历史Base共7,789个规范化第三方候选，2,524个日期沿用E2new同日JSON API缓存，另并发查询5,265个；得到dated 3,983、not_found 3,736、no_release_date 70、query_unknown 0。当前只是部分BOUND输出对应的缓存；最终仍要覆盖新增回答并重新审计完整名单。

- 2026-09-24T07:47:47Z UTC: progress 351/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=129/1000 qwen3_foldC=222/1000.

- 2026-09-24T07:55:18Z UTC: GPU2 START deepseekcoder_foldA; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T07:55:18Z UTC: GPU3 START qwen3_foldC; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T07:57:47Z UTC: progress 533/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=191/1000 qwen3_foldC=342/1000.

- 2026-09-24T08:07:47Z UTC: progress 714/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=255/1000 qwen3_foldC=459/1000.

- 2026-09-24T08:17:47Z UTC: progress 919/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=328/1000 qwen3_foldC=591/1000.

- 2026-09-24T08:27:47Z UTC: progress 1146/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=397/1000 qwen3_foldC=749/1000.

- 2026-09-24T08:37:47Z UTC: progress 1357/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=477/1000 qwen3_foldC=880/1000.

- 2026-09-24T08:47:47Z UTC: progress 1511/12000 prompt-condition records, 0/12 conditions complete; deepseekcoder_foldA=563/1000 qwen3_foldC=948/1000.

- 2026-09-24T08:51:33Z UTC: GPU3 DONE qwen3_foldC (1000 prompts, 5000 generations).

- 2026-09-24T08:51:33Z UTC: GPU3 START qwen3_foldD; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T08:57:47Z UTC: progress 1721/12000 prompt-condition records, 1/12 conditions complete; deepseekcoder_foldA=646/1000 qwen3_foldD=75/1000.

- 2026-09-24T09:07:47Z UTC: progress 1944/12000 prompt-condition records, 1/12 conditions complete; deepseekcoder_foldA=715/1000 qwen3_foldD=229/1000.

- 2026-09-24T09:17:47Z UTC: progress 2204/12000 prompt-condition records, 1/12 conditions complete; deepseekcoder_foldA=797/1000 qwen3_foldD=407/1000.

- 2026-09-24T09:27:47Z UTC: progress 2410/12000 prompt-condition records, 1/12 conditions complete; deepseekcoder_foldA=875/1000 qwen3_foldD=535/1000.

- 2026-09-24T09:37:47Z UTC: progress 2644/12000 prompt-condition records, 1/12 conditions complete; deepseekcoder_foldA=951/1000 qwen3_foldD=693/1000.

- 2026-09-24T09:43:53Z UTC: GPU2 DONE deepseekcoder_foldA (1000 prompts, 5000 generations).

- 2026-09-24T09:43:53Z UTC: GPU2 START deepseekcoder_foldB; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T09:47:47Z UTC: progress 2885/12000 prompt-condition records, 2/12 conditions complete; deepseekcoder_foldB=46/1000 qwen3_foldD=839/1000.

- 2026-09-24T09:57:47Z UTC: progress 3142/12000 prompt-condition records, 2/12 conditions complete; deepseekcoder_foldB=185/1000 qwen3_foldD=957/1000.

- 2026-09-24T09:59:53Z UTC: GPU3 DONE qwen3_foldD (1000 prompts, 5000 generations).

- 2026-09-24T09:59:53Z UTC: GPU3 START llama31_foldA; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T10:07:47Z UTC: progress 3440/12000 prompt-condition records, 3/12 conditions complete; deepseekcoder_foldB=326/1000 llama31_foldA=114/1000.

- 2026-09-24T10:17:47Z UTC: progress 3737/12000 prompt-condition records, 3/12 conditions complete; deepseekcoder_foldB=459/1000 llama31_foldA=278/1000.

- 2026-09-24T10:27:47Z UTC: progress 4042/12000 prompt-condition records, 3/12 conditions complete; deepseekcoder_foldB=606/1000 llama31_foldA=436/1000.

- 2026-09-24T10:37:47Z UTC: progress 4337/12000 prompt-condition records, 3/12 conditions complete; deepseekcoder_foldB=738/1000 llama31_foldA=599/1000.

- 2026-09-24T10:47:47Z UTC: progress 4644/12000 prompt-condition records, 3/12 conditions complete; deepseekcoder_foldB=876/1000 llama31_foldA=768/1000.

- 2026-09-24T10:57:15Z UTC: GPU2 DONE deepseekcoder_foldB (1000 prompts, 5000 generations).

- 2026-09-24T10:57:15Z UTC: GPU2 START deepseekcoder_foldC; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T10:57:47Z UTC: progress 4922/12000 prompt-condition records, 4/12 conditions complete; deepseekcoder_foldC=5/1000 llama31_foldA=917/1000.

- 2026-09-24T11:04:44Z UTC: GPU3 DONE llama31_foldA (1000 prompts, 5000 generations).

- 2026-09-24T11:04:44Z UTC: GPU3 START llama31_foldB; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T11:07:47Z UTC: progress 5179/12000 prompt-condition records, 5/12 conditions complete; deepseekcoder_foldC=157/1000 llama31_foldB=22/1000.

- 2026-09-24T11:17:47Z UTC: progress 5372/12000 prompt-condition records, 5/12 conditions complete; deepseekcoder_foldC=299/1000 llama31_foldB=73/1000.

- 2026-09-24T11:27:47Z UTC: progress 5600/12000 prompt-condition records, 5/12 conditions complete; deepseekcoder_foldC=441/1000 llama31_foldB=159/1000.

- 2026-09-24T11:31:22Z UTC: GPU2 skip completed deepseekcoder_foldA (1000 prompts).

- 2026-09-24T11:31:22Z UTC: GPU2 skip completed deepseekcoder_foldB (1000 prompts).

- 2026-09-24T11:31:22Z UTC: GPU2 START deepseekcoder_foldC; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T11:31:22Z UTC: GPU3 skip completed qwen3_foldC (1000 prompts).

- 2026-09-24T11:31:22Z UTC: GPU3 skip completed qwen3_foldD (1000 prompts).

- 2026-09-24T11:31:22Z UTC: GPU3 skip completed llama31_foldA (1000 prompts).

- 2026-09-24T11:31:22Z UTC: GPU3 START llama31_foldB; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T11:37:47Z UTC: progress 5948/12000 prompt-condition records, 5/12 conditions complete; deepseekcoder_foldC=612/1000 llama31_foldB=336/1000.

- 2026-09-24T11:47:47Z UTC: progress 6380/12000 prompt-condition records, 5/12 conditions complete; deepseekcoder_foldC=813/1000 llama31_foldB=567/1000.

- 2026-09-24T11:57:31Z UTC: GPU2 DONE deepseekcoder_foldC (1000 prompts, 5000 generations).

- 2026-09-24T11:57:31Z UTC: GPU2 START deepseekcoder_foldD; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T11:57:47Z UTC: progress 6798/12000 prompt-condition records, 6/12 conditions complete; llama31_foldB=798/1000.

- 2026-09-24T12:07:32Z UTC: GPU3 DONE llama31_foldB (1000 prompts, 5000 generations).

- 2026-09-24T12:07:32Z UTC: GPU3 START llama31_foldC; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T12:07:47Z UTC: progress 7083/12000 prompt-condition records, 7/12 conditions complete; deepseekcoder_foldD=83/1000.

- 2026-09-24T12:17:47Z UTC: progress 7429/12000 prompt-condition records, 7/12 conditions complete; deepseekcoder_foldD=166/1000 llama31_foldC=263/1000.

- 2026-09-24T12:27:47Z UTC: progress 7780/12000 prompt-condition records, 7/12 conditions complete; deepseekcoder_foldD=248/1000 llama31_foldC=532/1000.

- 2026-09-24T12:37:47Z UTC: progress 8128/12000 prompt-condition records, 7/12 conditions complete; deepseekcoder_foldD=326/1000 llama31_foldC=802/1000.

- 2026-09-24T12:45:36Z UTC: GPU3 DONE llama31_foldC (1000 prompts, 5000 generations).

- 2026-09-24T12:45:36Z UTC: GPU3 START llama31_foldD; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T12:47:47Z UTC: progress 8454/12000 prompt-condition records, 8/12 conditions complete; deepseekcoder_foldD=403/1000 llama31_foldD=51/1000.

- 2026-09-24T12:57:47Z UTC: progress 8790/12000 prompt-condition records, 8/12 conditions complete; deepseekcoder_foldD=488/1000 llama31_foldD=302/1000.

- 2026-09-24T13:07:47Z UTC: progress 9131/12000 prompt-condition records, 8/12 conditions complete; deepseekcoder_foldD=569/1000 llama31_foldD=562/1000.

- 2026-09-24T13:17:47Z UTC: progress 9476/12000 prompt-condition records, 8/12 conditions complete; deepseekcoder_foldD=655/1000 llama31_foldD=821/1000.

- 2026-09-24T13:25:05Z UTC: GPU3 DONE llama31_foldD (1000 prompts, 5000 generations).

- 2026-09-24T13:25:53Z UTC: GPU3 START extra qwen3_foldB after Llama-3.1 completed.

- 2026-09-24T13:27:48Z UTC: progress 9777/12000 prompt-condition records, 9/12 conditions complete; deepseekcoder_foldD=733/1000 qwen3_foldB=44/1000.

- 2026-09-24T13:37:48Z UTC: progress 10117/12000 prompt-condition records, 9/12 conditions complete; deepseekcoder_foldD=813/1000 qwen3_foldB=304/1000.

- 2026-09-24T13:47:48Z UTC: progress 10463/12000 prompt-condition records, 9/12 conditions complete; deepseekcoder_foldD=893/1000 qwen3_foldB=570/1000.

- 2026-09-24T13:57:48Z UTC: progress 10819/12000 prompt-condition records, 9/12 conditions complete; deepseekcoder_foldD=981/1000 qwen3_foldB=838/1000.

- 2026-09-24T14:00:05Z UTC: GPU2 DONE deepseekcoder_foldD (1000 prompts, 5000 generations).

- 2026-09-24T14:00:05Z UTC: GPU2 START qwen3_foldA; 1000 prompts × 5 generations, max_new_tokens=128, top_p=0.95, seed=20260926.

- 2026-09-24T14:04:03Z UTC: GPU3 DONE extra qwen3_foldB (1000 prompts, 5000 generations).

- 2026-09-24T14:07:48Z UTC: progress 11188/12000 prompt-condition records, 11/12 conditions complete; qwen3_foldA=188/1000.

- 2026-09-24T14:17:48Z UTC: progress 11431/12000 prompt-condition records, 11/12 conditions complete; qwen3_foldA=431/1000.

- 2026-09-24T14:27:48Z UTC: progress 11681/12000 prompt-condition records, 11/12 conditions complete; qwen3_foldA=681/1000.

- 2026-09-24T14:37:48Z UTC: progress 11925/12000 prompt-condition records, 11/12 conditions complete; qwen3_foldA=925/1000.

- 2026-09-24T14:40:56Z UTC: GPU2 DONE qwen3_foldA (1000 prompts, 5000 generations).

- 2026-09-24T14:40:56Z UTC: GPU2 skip completed qwen3_foldB (1000 prompts).

- 2026-09-24T14:47:48Z UTC: progress 12000/12000 prompt-condition records, 12/12 conditions complete;.

## 2026-09-24：最终标注、合并与复核

- 12个条件均达到1000条prompt记录、每条5次生成；GPU2完成DeepSeekCoder A–D和Qwen3 A，GPU3完成Qwen3 B–D及Llama-3.1 A–D。Qwen3 B由GPU3提前完成，GPU2队列识别到完整输出后跳过，没有并发重复生成。
- 先前在沙箱内直接补查最后59个候选时得到`query_unknown`，因此未把这些临时状态当作最终标签；按网络沙箱要求在获准的外部执行环境重试，59项均取得确定状态。最终共9127个规范化第三方候选：dated 4559、not_found 4480、no_release_date 88、query_unknown 0。输出去重为`results/release_dates_final.jsonl`，SHA-256=`b32f413306b4f8c73bbb7d6cb2b74acbf88f22af0aaec452682d672cf4e75715`。
- `merge_and_summarize.py`逐条件核查manifest的1000个ID、原文、5个replicate与BOUND seed；统一重标全部BOUND回答后，按replication package的prompt均值指标生成12份`summary`+`details`，并计算四折及三模型等权汇总。原始Base回答及标签直接复用；同一最终日期缓存的Base重标仅做敏感性检查。临时标签与最终标签不一致的BOUND回答共2774条，证明不能使用原始raw文件的临时`valid/hallucinated`字段计算最终指标。
- 主结果：三模型等权Sample-HR 11.17%→9.33%，差值−1.84 pp，2000次prompt-cluster bootstrap 95% CI约[−2.687,−1.035] pp；Package-HR 5.89%→4.39%；Valid-Rate 79.68%→77.04%；无可抽取包率10.09%→16.94%。DeepSeekCoder的Sample-HR点估计9.70%→9.94%，说明方向不一致。完整分模型、分折与适用范围见`design_and_results.md`，机器可读结果见`results/merged/`。

## 2026-09-25：cutoff校正与新增500条不重叠prompt

- 核对replication package `BOUND/bound/bound.py` 的 `MODEL_CUTOFFS`：DeepSeekCoder=2023-10-29、Qwen3=2025-04-29、Llama-3.1=2023-12-31。此前E3new汇总误用DeepSeekCoder=2024-01-01、Llama-3.1=2024-07-23，原报告数值需替换。已修改合并脚本，对原Base和BOUND的已生成回答统一按论文cutoff重标，无需重生成原1000条。
- 使用同一源文件、同一编辑prompt排除规则，另排除旧1000条ID及规范化问题文本；在剩余2961条中以seed 20260925简单随机抽取500条。新旧ID和规范化文本均不重叠；manifest SHA-256=`44b51129aa02a68c0be052b0fd1ad43131d8d1d86214d32460d172db3da20ccf`。历史Base风险层DeepSeekCoder clean/low/high=363/94/43，Qwen3=448/25/27，Llama-3.1=299/119/82。
- 新增500条使用三模型各四折、每prompt五次、128 tokens、temperature=0.7/top_k=40/top_p=0.95、原有逐条seed协议；GPU1/2/3分别运行DeepSeekCoder/Qwen3/Llama-3.1。原Base生成文本复用，最终同一cutoff重标。

- 2026-09-25T07:30:22Z UTC: GPU1 START supplementary deepseekcoder_foldA; 500 prompts × 5 generations, 128 tokens, cutoff=2023-10-29.

- 2026-09-25T07:30:22Z UTC: GPU2 START supplementary qwen3_foldA; 500 prompts × 5 generations, 128 tokens, cutoff=2025-04-29.

- 2026-09-25T07:30:22Z UTC: GPU3 START supplementary llama31_foldA; 500 prompts × 5 generations, 128 tokens, cutoff=2023-12-31.
- 原1000条校正汇总已完成，输出`results/cutoff_corrected_1000/`，不覆盖原错误口径的`results/merged/`以保留审计链。三模型等权Sample-HR=11.24%→9.37%，差值−1.87 pp，2000次prompt-cluster bootstrap 95% CI [−2.74,−1.09] pp；Package-HR=5.92%→4.41%，Valid-Rate=79.68%→77.04%。新主表已写入`design_and_results.md`。
- 已生成合并用1500条manifest，SHA-256=`e9becca255e5965408454529c72a46fb9f28414f16e1ed8c57a886c4d628f0de`。新增500条完成后，将补查新候选包发布日期，再独立汇总500及合并汇总1500。

- 2026-09-25T07:33:32Z UTC: supplementary generation progress 171/6000 prompt-condition records, 0/12 conditions complete.

- 2026-09-25T07:37:06Z UTC: supplementary generation progress 387/6000 prompt-condition records, 0/12 conditions complete.

- 2026-09-25T07:47:06Z UTC: supplementary generation progress 1009/6000 prompt-condition records, 0/12 conditions complete.

- 2026-09-25T07:48:34Z UTC: GPU3 DONE supplementary llama31_foldA.

- 2026-09-25T07:48:34Z UTC: GPU3 START supplementary llama31_foldB; 500 prompts × 5 generations, 128 tokens, cutoff=2023-12-31.

- 2026-09-25T07:51:22Z UTC: GPU2 DONE supplementary qwen3_foldA.

- 2026-09-25T07:51:22Z UTC: GPU2 START supplementary qwen3_foldB; 500 prompts × 5 generations, 128 tokens, cutoff=2025-04-29.

- 2026-09-25T07:57:06Z UTC: supplementary generation progress 1580/6000 prompt-condition records, 2/12 conditions complete.

- 2026-09-25T08:07:06Z UTC: supplementary generation progress 2173/6000 prompt-condition records, 2/12 conditions complete.

- 2026-09-25T08:10:17Z UTC: GPU3 DONE supplementary llama31_foldB.

- 2026-09-25T08:10:17Z UTC: GPU3 START supplementary llama31_foldC; 500 prompts × 5 generations, 128 tokens, cutoff=2023-12-31.

- 2026-09-25T08:10:45Z UTC: GPU2 DONE supplementary qwen3_foldB.

- 2026-09-25T08:10:45Z UTC: GPU2 START supplementary qwen3_foldC; 500 prompts × 5 generations, 128 tokens, cutoff=2025-04-29.

- 2026-09-25T08:17:06Z UTC: supplementary generation progress 2743/6000 prompt-condition records, 4/12 conditions complete.

- 2026-09-25T08:20:21Z UTC: supplementary generation progress 2943/6000 prompt-condition records, 4/12 conditions complete.

- 2026-09-25T08:23:35Z UTC: GPU1 DONE supplementary deepseekcoder_foldA.

- 2026-09-25T08:23:35Z UTC: GPU1 START supplementary deepseekcoder_foldB; 500 prompts × 5 generations, 128 tokens, cutoff=2023-10-29.

- 2026-09-25T08:29:16Z UTC: GPU3 DONE supplementary llama31_foldC.

- 2026-09-25T08:29:16Z UTC: GPU3 START supplementary llama31_foldD; 500 prompts × 5 generations, 128 tokens, cutoff=2023-12-31.

- 2026-09-25T08:30:21Z UTC: supplementary generation progress 3578/6000 prompt-condition records, 6/12 conditions complete.

- 2026-09-25T08:33:45Z UTC: GPU2 DONE supplementary qwen3_foldC.

- 2026-09-25T08:33:45Z UTC: GPU2 START supplementary qwen3_foldD; 500 prompts × 5 generations, 128 tokens, cutoff=2025-04-29.

- 2026-09-25T08:40:21Z UTC: supplementary generation progress 4221/6000 prompt-condition records, 7/12 conditions complete.

- 2026-09-25T08:49:29Z UTC: GPU3 DONE supplementary llama31_foldD.

- 2026-09-25T08:49:44Z UTC: GPU1 DONE supplementary deepseekcoder_foldB.

- 2026-09-25T08:49:44Z UTC: GPU1 START supplementary deepseekcoder_foldC; 500 prompts × 5 generations, 128 tokens, cutoff=2023-10-29.

- 2026-09-25T08:50:21Z UTC: supplementary generation progress 4849/6000 prompt-condition records, 9/12 conditions complete.

- 2026-09-25T08:57:59Z UTC: GPU2 DONE supplementary qwen3_foldD.

- 2026-09-25T09:00:22Z UTC: supplementary generation progress 5202/6000 prompt-condition records, 10/12 conditions complete.

- 2026-09-25T09:10:22Z UTC: supplementary generation progress 5400/6000 prompt-condition records, 10/12 conditions complete.

- 2026-09-25T09:15:24Z UTC: GPU1 DONE supplementary deepseekcoder_foldC.

- 2026-09-25T09:15:24Z UTC: GPU1 START supplementary deepseekcoder_foldD; 500 prompts × 5 generations, 128 tokens, cutoff=2023-10-29.

- 2026-09-25T09:20:22Z UTC: supplementary generation progress 5532/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T09:30:22Z UTC: supplementary generation progress 5610/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T09:40:22Z UTC: supplementary generation progress 5690/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T09:50:22Z UTC: supplementary generation progress 5762/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T10:00:22Z UTC: supplementary generation progress 5836/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T10:10:22Z UTC: supplementary generation progress 5907/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T10:20:22Z UTC: supplementary generation progress 5980/6000 prompt-condition records, 11/12 conditions complete.

- 2026-09-25T10:22:40Z UTC: GPU1 DONE supplementary deepseekcoder_foldD.

- 2026-09-25T10:30:22Z UTC: supplementary generation progress 6000/6000 prompt-condition records, 12/12 conditions complete.

- 2026-09-25T10:30:22Z UTC: all 12 supplementary conditions complete; building PyPI first-release cache.

- 2026-09-25T10:33:41Z UTC: release-date cache has unresolved lookups; retry 1/3.

- 2026-09-25T10:37:33Z UTC: release-date cache has unresolved lookups; retry 2/3.

- 2026-09-25T10:39:54Z UTC: release-date cache has unresolved lookups; retry 3/3.
- 2026-09-25T12:39Z UTC: 人工复核发现12条件已于10:30完成（6000/6000），自动缓存的最后163个候选仍为`query_unknown`，均系PyPI短暂HTTP 503；单独复查其中候选已返回确定的404。已改用4并发重试，避免将HTTP 503误判为包不存在；合并需等待缓存全部确定。

- 2026-09-25T12:40:52Z UTC: final 500/1500 tables written to design_and_results.md; cache statuses={'dated': 5801, 'no_release_date': 120, 'not_found': 6379}.
- 2026-09-25T12:41Z UTC: 4并发复查剩余163项均得到确定状态（均404）；合并1500条共有12300个候选：dated=5801、not_found=6379、no_release_date=120、query_unknown=0。去重日期缓存SHA-256=`0771ccd78d2be0f222b10c2d13c8727a2f00fd73e17ec0510b58f8caaa34129b`。
- 500条和1500条的12份replication-package格式结果、逐折CSV、四折与三模型宏平均、bootstrap区间均已写出。500条三模型等权Sample-HR=12.20%→9.39%（−2.81 pp，95% CI [−4.24,−1.51]）；1500条=11.56%→9.37%（−2.19 pp，95% CI [−2.88,−1.49]）。相应Package-HR=6.54%→4.54%及6.13%→4.45%；Valid-Rate=78.23%→75.99%及79.20%→76.69%。
- QA通过：500/1500各12条件每个prompt均为五次Base与BOUND回答；每模型四折Base完全一致；模型cutoff匹配replication package；1500条指标与1000、500按样本数加权结果一致；缓存12300项唯一且无未知状态。`design_and_results.md`已更新最终表和解释限制。

- 2026-09-25T12:42:41Z UTC: final 500/1500 tables written to design_and_results.md; cache statuses={'dated': 5801, 'no_release_date': 120, 'not_found': 6379}.
