# E7——实验过程记录

本文件按时间顺序追加，记录 registry snapshot、查询批次、网络异常、schema 变化、人工审核和结果版本。

## 2026-09-23

- 将原互斥标签列表拆为注册表状态、时间状态、名称/映射关系和查询证据四个维度。
- 要求永久保存原始模型输出名，normalization 不得改变模型是否成功的判定。
- 增加原论文 cutoff 与固定评估日期两套主分析。
- 明确 post-cutoff legitimate package 不与始终不存在的名称合并。
- E0 发现 DeepSeekCoder/Llama-3.1 克隆配置 cutoff 冲突，需在查询前解决。

## 下一步

- 冻结三个模型的权威 cutoff 定义和证据来源。
- 确定固定评估日期与 registry snapshot 格式。
- 实现可恢复、可缓存并保留失败状态的查询脚本。
- 生成分层人工审核样本。

