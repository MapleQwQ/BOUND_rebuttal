# 实验3过程记录

## 2026-09-24：RQ4资产核对

- 找到`rq4_localization_analysis_20260615`逐提示全模块分数、top-1/top-5结果、层/投影家族频率与fold overlap。600个编辑提示、3000个top-5命中；统计单位是提示，不是top-5行。
- 用`../script/reanalyse_existing.py`从CSV复算占比最高家族、top-5层频率和六个fold对的平均模块Jaccard，写入`../results/03_localization_stability/existing_summary.json`。
- 记录解释边界：现有RQ4表明给定风险函数下的集中性与fold重复性，未有无关目标的负对照，故不能凭热图断言包幻觉特异性。只读重分析未使用GPU。

## 2026-09-24：同提示valid-only定位负对照启动

- 新增`../script/run_valid_only_localization.py`，保持原RQ4的模型、四折编辑提示、七类linear候选模块、首token约定和`mean(abs(gradient*weight))`评分，仅将定位目标改为`LSE(valid first tokens)`。逐提示保存全部模块排名；脚本只接受GPU 2或3，支持按完成提示续跑。
- GPU 2启动DeepSeekCoder，GPU 3启动Qwen3；后续Llama-3.1仍只使用这两张卡。新增`../script/analyze_valid_only_control.py`用于对同提示full-risk与valid-only排名做top-1/top-5及全排名比较。本条仅记录启动，结论待结果核查。

## 2026-09-24：负对照完成与解释修正

- 首次运行遇到没有valid reference的编辑提示而停止；修正脚本后将这类提示逐条保存并续跑。三模型各200条提示处理完毕，其中可定义valid-only目标的提示为190/163/188，其余10/37/12条按`no_valid_reference`单列，不进入配对分母。
- GPU 2完成DeepSeekCoder和Llama-3.1，GPU 3完成Qwen3；均有完整metadata且正常退出。`../script/analyze_valid_only_control.py`核对同提示候选模块集合，重算top-1、top-5 Jaccard与全排名Spearman，按提示bootstrap 10,000次；详见设计结果表。
- valid-only与full-risk的top-5 Jaccard为0.719/0.686/0.863，全模块Spearman均大于0.95。结论因此收窄为“热点集中且稳定，但不专属于hallucination-risk目标”。
