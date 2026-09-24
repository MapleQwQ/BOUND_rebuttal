# E3 共同 deployment registry snapshot

- 文件：`deployment_registry_packmonitor_8808362.json`
- 来源：PackMonitor 官方仓库 commit `8808362e14891fe692b17b8192ed123dff4d64d2` 随附的 `HFuzzer/valid_packages/pypi_packages.json`
- 冻结复制日期：2026-09-23 UTC
- 条目数：706,618
- SHA-256：`9cc52b886efb9488418f0a5fc2f24484088019111029b5eb9587e3b0e05a315c`
- 规范化规则：比较时对候选和snapshot名称统一小写，并将连续的 `-_.` 归一化为 `-`；Python标准库另行判定。

该文件用于所有模型相同的 deployment-snapshot validity，避免不同模型 cutoff 造成跨模型定义不一致。它是 PackMonitor commit 随附的静态名称表，不含每个包的首次发布日期，也不保证等同于2026-09-23全量PyPI实时索引；因此它不能替代 E7 的时间状态审计。未命中项先标为 `snapshot_not_listed`，不能在缺少额外证据时直接声称截至现实评估日从未存在。
