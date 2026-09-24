# E8——真实项目依赖与分阶段端到端验证

## 实验目标

提供比合成 prompt、source-package hit 和语法检查更接近真实任务的严格证据。人工相关性审计和 AST 检查只能回答一部分适配性问题，不能写成已经满足真实项目、安装、导入或端到端要求。

## 阶段一：P1 小规模可复现验证

与 P0 实验并行检查少量真实任务及环境是否可用，不等待所有 P0 完成后才启动。

- 选择少量许可证清晰、可固定 commit、无凭据、可在资源受限隔离环境执行的 Python 项目/任务。
- 从 README、issue 或功能描述构造不泄露依赖名的任务 prompt。
- 人工定义任务 requirement 和经证据支持的 reference dependencies，区分 runtime/core、optional、dev、transitive 和与任务无关项。
- Base/BOUND 使用相同任务和协议生成包建议及代码。
- 将基础设施失败、安装源失败、测试环境失败与模型输出失败分开记录。

## 阶段二：P2 扩展验证

若阶段一流程稳定且时间/资源允许，再扩展至约 30–50 个项目和更多执行维度；样本量、停止规则和项目排除在查看方法差异前冻结。

## 指标命名与判定

- Task-required dependency precision/recall；
- **Required-Dependency Hit Rate**：至少命中一个必要依赖；不得称为 task success；
- Recommendation Adequacy Rate；
- clean-environment install success；
- import success；
- AST/compile success；
- **Task Success Rate**：只有满足预定义功能测试或任务验收条件才使用该名称；
- test success、基础设施失败率和模型导致失败率。

完整 manifest 不是唯一正确答案，不能直接作为任务依赖真值。允许合理替代，并保存人工判断和文档证据。

## 执行安全与复现

- 固定项目 commit、Python/OS/包索引快照、资源限制和网络策略。
- 使用隔离、无凭据、最小权限环境；不执行不可信安装脚本前先做静态检查。
- 保存构建/安装/导入/测试日志及退出状态，不把 timeout 或基础设施错误算成模型失败。

## 输出

- `results/task_manifest.jsonl`
- `results/reference_dependency_evidence.csv`
- `results/environment_manifest.json`
- `results/generations.jsonl`
- `results/execution_outcomes.csv`
- `results/failure_attribution.csv`
- `results/summary.md`

## 实验结果

状态：阶段一提升为 P1，尚未选择项目或验证环境；阶段二保持 P2。

