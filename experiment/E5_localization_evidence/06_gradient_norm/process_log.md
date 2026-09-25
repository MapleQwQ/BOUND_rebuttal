# 06 Gradient Norm 过程记录

## 2026-09-25：实验设计和启动

- 用户指定 RQ3 评估设置，并允许 GPU 1、2、3；无须 HumanEval。
- 核对原 `knowledgeEdit/package_edit.py::localize_package_boundary`，唯一评分表达式为 `(weight.grad.detach().float() * weight.detach().float()).abs().mean().item()`；新评分为 `weight.grad.detach().float().abs().mean().item()`。脚本使用原函数源码替换这一个表达式，运行时验证逆替换得到原源码。
- 核对 RQ3 配置构造、原 `select_modules_from_report` 的 `top_k=5/window_family/window=1`、历史 12 折定位报告和最终 adapter 配置。Llama A 最终 adapter 训练 seed 为 43，其余 11 折为 42。
- 建立 `script/run_gradient_norm.py` 与 `script/analyze_gradient_norm.py`，每折先重算原评分报告并核对历史选中模块，再计算 Gradient Norm、训练及评估。分析器按 prompt 配对 bootstrap；核对历史 RQ3 `summary` 后确认 Package-HR 是逐 prompt 比率均值，已依原定义实现，而非全体包数的合并比率。
- 沙箱内不可见 GPU 设备；经授权的沙箱外探测显示 GPU 1、2、3 空闲，因此模型运行采用仅限这些 GPU 的沙箱外命令。DeepSeekCoder A 折已启动。
- 三个模型的队列分别在 GPU 1、2、3 启动；DeepSeekCoder A 的原评分复算已通过历史模块集合核对并进入 RQ3 unseen 评估。各折队列日志保存在 `../results/06_gradient_norm/` 下。
- 首批模块集合核对：DeepSeekCoder A 的最终集合原/新均为7个、交集5个；Qwen3 A均为9个、交集7个；Llama-3.1 A原7个、新8个、交集7个。Llama A的实际LoRA模块预算因此不同，结果解读时须明确；它来自固定的 `window_family` 扩展规则。
- 对12折核对原 BOUND YAML 指向的编辑源文件与 `selected_task_recommend_cases.jsonl`：各文件均为50条，逐行 case ID一致。实验定位使用该同一批 case。
- 为避免 `window_family` 扩展造成的实际模块数差异混淆效果，新建 `script/run_gradient_norm_matched_budget.py`。仅对数量不等的折，在原选中序列上按原 BOUND 模块数截取前 N 个并重做相同编辑/评估；原规则结果仍作为主分析。
- 审核逐条生成发现旧 E5 脚本把“无抽取包”命名为 Empty-Rate，但许多此类输出是非空的 `[ANSWER]None[/ANSWER]`。本实验明确拆分真正空白原始回答率和无抽取包率；主表的 empty-output rate 使用前者。已修正新脚本及分析器，早期已完成折的逐折摘要会在总汇总前统一回填。
- 7/12个主实验单元已完成。GPU 2 的 Qwen3 队列结束后，等待队列将自动在该卡运行需要相同模块预算对照的 Llama 折；开始前仍核对每折定位报告与原模块数量。
- Qwen3 D 折主定位按固定 `window_family` 规则得到7个模块，原 BOUND 为9个，因此相同预算分析还须覆盖该折。已把辅助脚本扩展为：超额时按排名截断，不足时从同投影家族的其余候选中按梯度范数补足；运行后断言LoRA参数总数与原adapter相同。该调整仅属于预算敏感性分析。
