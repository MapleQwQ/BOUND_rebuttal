# 来源包关联恢复结果

正式60个任务中，`official_prompt_mapping=0`、`verified_reconstruction=0`、`unavailable=60`。公开Spracklen数据只提供prompt文本；PyPI名称全集不是prompt级标签，本仓库`valid_reference`又来自模型输出，不能反推来源真值。因此本实验没有计算Source-Package Hit或Reference Dependency Recall，只报告人工slot覆盖。逐任务状态见 `prompt_ground_truth_provenance.csv`。
