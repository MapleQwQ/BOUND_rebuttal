# 实验2过程记录

## 2026-09-24：已有hallucination-only消融核查

- 阅读`package_edit.py`确认定位分数实际为hallucinated token LSE减`anchor_penalty`倍valid token LSE；`wo_valid_anchor`只将定位`anchor_penalty`改为0，并重新定位、训练。
- 在`rq3_ablation_20260613`找到三模型×四折全部12个报告和结果。只读脚本对比主要训练超参数，并输出`../results/02_risk_score/existing_runs.csv`。Full与Hall-only的最终模块集合有10/12折完全相同；这限制了现有证据能支持的“风险项独立贡献”表述。
- 未做新的训练或GPU推理；后续如需同seed重跑，只用GPU 2、3。

## 2026-09-24：同100提示配对统计

- `../script/analyze_rq3_pairs.py`读取RQ3目录中每fold的`BOUND`和`wo_valid_anchor`逐提示结果，确认各自100个prompt ID一致，按prompt成组、四fold等权bootstrap 10,000次。CSV与JSON结果写入`../results/02_risk_score/`。
- Llama-3.1的Hall-only−Full risk Sample-HR为+6.70百分点[4.05,9.40]、Valid-Rate为−5.30百分点[-8.05,-2.85]；DeepSeekCoder Package-HR也偏高，Qwen3区间大多跨0。多数最终模块相同，因此仍需避免过度因果归因。

## 2026-09-24：adapter与训练seed审计后修正解释

- 新增`../script/audit_risk_same_modules.py`，逐折比较真实模块集合、训练seed/超参数和LoRA全部tensor，结果写入`../results/02_risk_score/same_module_adapter_audit.csv`。10个相同模块折中9折adapter逐tensor完全相同；Llama-3.1 fold A训练seed分别为43和42、adapter不同。仅DeepSeekCoder B、D选择了不同模块。
- 因此上一步逐提示bootstrap CI只能描述不同历史生成样本的差异，不能证明风险项贡献；尤其Llama-3.1的表面改善发生在相同adapter或不匹配seed条件下。设计结果文档已更正为保守解释。下一步若量化因果质量贡献，针对DeepSeekCoder B、D同seed训练并在相同generation seed下评估。

## 2026-09-24：真正改变模块折的共同随机数评估启动

- `../script/evaluate_risk_common_seeds.py`仅针对DeepSeekCoder B、D：这两折Full与Hall-only原adapter训练seed及超参数相同、但定位选中模块不同。保持原RQ3同一100条unseen prompt、5次采样、64新token、temperature 0.7、top-k 40、top-p 0.95；对同prompt和generation设相同SHA-256派生seed。
- 在GPU 3成功完成fold B/full-risk的1提示smoke后启动四个fold×condition单元；逐提示输出、adapter/input哈希和PyPI首发缓存新增项写在`../results/02_risk_score/common_seed_eval/`。`../script/analyze_risk_common_seeds.py`将核对种子并计算配对区间。本条仅记录启动，尚未作结果结论。

## 2026-09-25：共同随机数评估完成

- GPU 3的DeepSeekCoder B、D两折×Full/Hall-only四个单元均完成100提示×5次采样，队列正常退出。分析脚本核对输入哈希、cutoff及每条prompt/generation seed完全配对，按prompt bootstrap 10,000次。
- 两折等权Hall-only−Full Sample-HR为0.00百分点，95% CI [-2.70,+2.60]；Package-HR约-0.01百分点、Valid-Rate约-0.20百分点，区间均跨0。结果写入设计结果表；不能据此宣称valid anchor带来稳定质量收益。

## 2026-09-25：定位排名复核

- 新增`../script/analyze_risk_rankings.py`，比较每折Full与Hall-only定位报告中共同的top-200模块排名，输出逐折CSV和四折均值。三模型共同模块Spearman均值为0.999/0.996/0.997，top-5 Jaccard为0.833/1/1；这进一步限制了valid anchor的独立定位贡献。
