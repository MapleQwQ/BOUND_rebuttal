# E8——实验过程记录

本文件按时间顺序追加，记录项目候选、排除理由、环境构建、执行安全检查、失败归因和结果版本。

## 2026-09-23

- 将 E8 拆为 P1 小规模可复现验证和 P2 扩展验证。
- 将“至少命中一个必要依赖的 task success”更名为 Required-Dependency Hit Rate。
- 将 Task Success 限定为通过任务要求或功能测试。
- 明确整个 manifest 不是唯一依赖真值，必须区分 runtime、optional、dev、transitive 并允许合理替代。
- 新增隔离、无凭据、资源限制和基础设施/模型失败分离要求。

## 下一步

- 并行筛选少量许可证和环境条件合适的任务。
- 定义任务验收条件和 reference dependency 证据。
- 对候选项目做无模型环境复现，确认安装和测试本身稳定。
- 通过安全检查后再运行 Base/BOUND。

