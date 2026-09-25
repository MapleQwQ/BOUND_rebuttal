#!/usr/bin/env python3
"""Write completed 500/1500 E3 readout from the machine-readable summaries."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "results/sample500"
DOC = ROOT / "design_and_results.md"
LOG = ROOT / "process_log.md"
START = "<!-- supplementary-results-start -->"
END = "<!-- supplementary-results-end -->"


def table(n: int) -> str:
    x = json.loads((SUB / f"merged_{n}/four_fold_macro.json").read_text())
    assert x["n_prompts"] == n
    lines = [f"### {n}条prompt", "", "| 模型 | Sample-HR Base→BOUND | 差值及95% CI | Package-HR Base→BOUND | Valid-Rate Base→BOUND |", "| --- | ---: | ---: | ---: | ---: |"]
    for model, label in (("deepseekcoder", "DeepSeekCoder"), ("qwen3", "Qwen3"), ("llama31", "Llama-3.1")):
        r = x["models"][model]
        metrics = r["metrics"]
        ci = r["delta_sample_hr_ci95"]
        lines.append(f"| {label} | {metrics['sample_hallucination_rate']['base']:.2%}→{metrics['sample_hallucination_rate']['bound_four_fold_macro']:.2%} | {metrics['sample_hallucination_rate']['difference']*100:+.2f} pp [{ci[0]*100:+.2f},{ci[1]*100:+.2f}] | {metrics['package_hallucination_rate']['base']:.2%}→{metrics['package_hallucination_rate']['bound_four_fold_macro']:.2%} | {metrics['sample_valid_rate']['base']:.2%}→{metrics['sample_valid_rate']['bound_four_fold_macro']:.2%} |")
    m = x["three_model_equal_weight_macro"]
    ci = x["three_model_macro_delta_sample_hr_ci95"]
    lines.append(f"| 三模型等权 | {m['sample_hallucination_rate']['base']:.2%}→{m['sample_hallucination_rate']['bound_four_fold_macro']:.2%} | {m['sample_hallucination_rate']['difference']*100:+.2f} pp [{ci[0]*100:+.2f},{ci[1]*100:+.2f}] | {m['package_hallucination_rate']['base']:.2%}→{m['package_hallucination_rate']['bound_four_fold_macro']:.2%} | {m['sample_valid_rate']['base']:.2%}→{m['sample_valid_rate']['bound_four_fold_macro']:.2%} |")
    return "\n".join(lines)


def main() -> None:
    audit = json.loads((SUB / "release_cache_audit.json").read_text())
    assert audit["statuses"].get("query_unknown", 0) == 0
    body = "\n\n".join([
        "## 补充实验最终结果（正确cutoff）",
        "500条prompt与原1000条在ID和规范化文本上均无重叠。每模型四折，每prompt五次生成；原Base回答文本复用。Base与BOUND全部按replication package cutoff统一标注。表内先按prompt求平均，再按四折及模型等权平均；95% CI为2000次prompt cluster bootstrap。",
        table(500),
        table(1500),
        f"PyPI日期缓存涵盖{audit['candidate_names']}个规范化第三方候选，状态分布为{audit['statuses']}；无未知查询。补充样本逐条结果见`results/sample500/merged_500/`，合并结果见`results/sample500/merged_1500/`。原1000条校正结果见`results/cutoff_corrected_1000/`。",
    ])
    existing = DOC.read_text()
    block = START + "\n" + body + "\n" + END
    if START in existing and END in existing:
        existing = existing[:existing.index(START)] + block + existing[existing.index(END) + len(END):]
    else:
        existing = existing.rstrip() + "\n\n" + block + "\n"
    DOC.write_text(existing)
    with LOG.open("a") as handle:
        handle.write(f"\n- {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} UTC: final 500/1500 tables written to design_and_results.md; cache statuses={audit['statuses']}.\n")


if __name__ == "__main__":
    main()
