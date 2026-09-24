# E6——实验过程记录

本文件按时间顺序追加，记录 tokenizer 版本、chat template、上下文、审计脚本、变体配置和结果版本。

## 2026-09-23

- 确认 localization 实际使用 `tokenizer(" " + pkg).input_ids[:1]`。
- 将审计范围从 multi-token 比例扩展到回答前缀、前导空格、special token、chat template 和实际取值位置。
- 新增 valid/hallucinated 首 token 完全相同且 `lambda_a=1` 时 LSE 相消、梯度为零的专项统计。
- 将 full-sequence 设为首要敏感性变体，prefix-trie 变体设为有条件扩展。
- 与 E5 统一为“先离线审计与已有结果，再决定最小新增训练”。

## 下一步

- 冻结三模型 tokenizer 和 chat template 哈希。
- 导出全部 edit case 的上下文相关 tokenization 记录。
- 统计 collision、零梯度和候选去重影响。
- 依据预注册门槛决定是否启动每模型一个 fold 的 full-sequence 对照。

