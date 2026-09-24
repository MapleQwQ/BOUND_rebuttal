# PackMonitor 兼容性审计（2026-09-23）

## 审计对象

- 官方仓库：`https://github.com/THU-Agent/PackMonitor`
- 冻结 commit：`8808362e14891fe692b17b8192ed123dff4d64d2`
- 论文/仓库声称的核心实现：`HFuzzer/Framework/packmonitor_generate.py`
- 本次只做代码、环境和输入协议兼容性审计；没有用后处理过滤冒充 PackMonitor。

## 结论

当前不能在 BOUND 的纯包名列表协议上直接、公平运行官方 PackMonitor。官方实现只在 Markdown `bash` code block 中的 `pip install ...` 区域施加约束，而 BOUND 当前输出为 `[ANSWER]` 中的逗号分隔包名。直接喂入现有 prompt 会使 monitor 不触发，不能据此评价方法无效。

可以继续做的公平适配是：冻结共同的安装命令输出协议，让 Base 与 BOUND 都重新生成 `pip install ...`；PackMonitor 分支必须使用官方约束解码重新生成，而不是处理旧回答。

## 已验证事实

1. 官方类通过 Hugging Face `AutoTokenizer`/`AutoModelForCausalLM` 从本地路径加载模型，理论上可加载 DeepSeekCoder 一类标准 checkpoint。
2. 官方构造函数没有 BOUND/PEFT/LoRA adapter 参数；`BOUND + PackMonitor` 需要最小适配，在加载模型后注入并恢复现有 BOUND delta，不能把 Base+PackMonitor 结果冒充组合方法。
3. 官方 registry 文件 `HFuzzer/valid_packages/pypi_packages.json` 含 706,618 个字符串，但仓库未随文件提供快照日期或首发时间，不能直接替代论文的 model-cutoff validity。
4. 当前 EasyEdit 环境缺少 `llguidance` 与 `guidance-stitch`；官方 requirements 固定 `llguidance==1.1.0`、`guidance-stitch==0.1.5`、`transformers==4.52.1`，当前环境为 `transformers==4.57.1`。本轮没有擅自安装/降级依赖，以免破坏正在运行的其他实验。
5. 官方 runner 的 `list_attack_name` 为空，模型字典仍为占位路径；不是可直接执行的预配置复现实验。
6. 静态检查发现 grammar 中声明 `NATURAL_LANG`，但 `start` 使用 `NATATURAL_LANG`。必须在隔离环境实际编译 grammar 并记录是否为真实阻塞，不能静默修正后声称复现了原版。

## 下一步

- 在隔离环境安装官方固定依赖，先仅编译 grammar；保留原版失败日志。
- 若原版因明确 typo 失败，以单独 patch 文件记录最小修复，并同时报告 unpatched/patched 两个状态。
- 建立 5--10 个 `pip install` 共同协议 prompts 做触发 smoke，记录约束触发率、grammar build time、生成延迟与显存。
- smoke 通过后再冻结最多 100 prompts 的 Base、BOUND、PackMonitor、BOUND+PackMonitor 比较。

