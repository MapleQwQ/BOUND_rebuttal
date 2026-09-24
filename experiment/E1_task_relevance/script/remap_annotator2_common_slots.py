#!/usr/bin/env python3
"""将标注者2的独立事实判断映射到共同冻结的 requirement slots。

本脚本只使用匿名回答、共同槽和标注者2自己的原始标签；不读取盲键、
方法映射或另一标注者的回答标签。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# 共同槽相对于标注者2原始细粒度槽的语义对应。一个旧槽可以贡献给多个
# 共同槽，但下方 OVERRIDES 会处理“只覆盖合并槽的一部分”的保守例外。
CROSS = {
    "712": {},
    "4680": {"s1": ["S1"], "s2": ["S1"], "s3": ["S1"], "s4": ["S1"]},
    "3827": {"s1": ["S1"], "s2": ["S2"]},
    "1588": {"s1": ["S1"], "s2": ["S1"], "s3": ["S1"]},
    "4315": {"s1": ["S1"], "s2": ["S1"]},
    "2195": {"s1": ["S1"], "s2": ["S1"], "s3": ["S2"], "s4": ["S2"]},
    "2049": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"], "s4": ["S2"]},
    "2821": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"]},
    "1039": {"s1": ["S1"], "s2": ["S2"]},
    "1281": {"s1": ["S2"], "s2": ["S1"]},
    "2010": {"s1": ["S1"], "s2": ["S1"]},
    "2380": {"s1": ["S1"], "s2": ["S2"]},
    "4868": {},
    "732": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"]},
    "3259": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"], "s4": ["S2"], "s5": ["S2"]},
    "1330": {"s1": ["S1"], "s2": ["S1"], "s3": ["S2"]},
    "4433": {"s1": ["S1"], "s2": ["S1"]},
    "1537": {"s1": ["S1"]},
    "185": {"s1": ["S1"], "s2": ["S1"]},
    "470": {"s1": ["S1", "S2"], "s2": ["S1"], "s3": ["S2"]},
    "3039": {"s1": ["S1"]},
    "3901": {"s1": ["S1"], "s2": ["S1"]},
    "1541": {"s1": ["S1"], "s2": ["S1"], "s3": ["S1"], "s4": ["S2"]},
    "2105": {"s1": ["S1"], "s2": ["S2"]},
    "2743": {"s1": ["S1"], "s2": ["S1"], "s3": ["S1"], "s4": ["S1"]},
    "439": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"], "s4": ["S1"]},
    "394": {"s1": ["S1"], "s2": ["S3"], "s3": ["S2"], "s4": ["S4"], "s5": ["S5"], "s6": ["S6"]},
    "465": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"], "s4": ["S4"]},
    "3825": {"s1": ["S1"], "s2": ["S1"]},
    "4403": {"s1": ["S1"], "s2": ["S2"]},
    "995": {"s1": ["S1"], "s2": ["S1"]},
    "615": {"s1": ["S1"]},
    "4111": {"s1": ["S1"]},
    "3373": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"]},
    "354": {"s1": ["S1"], "s2": ["S3"]},
    "3198": {"s1": ["S1"]},
    "3531": {"s1": ["S1", "S2"], "s2": ["S1"], "s3": ["S2"]},
    "1248": {"s1": ["S1"], "s2": ["S1"]},
    "353": {"s1": ["S1"], "s2": ["S1"]},
    "3022": {"s1": ["S1"], "s2": ["S2"]},
    "3692": {"s1": ["S1"], "s2": ["S1"]},
    "2215": {"s1": ["S1"]},
    "4368": {"s1": ["S1"], "s2": ["S1"]},
    "2836": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"]},
    "1804": {"s2": ["S1"], "s3": ["S2", "S3"], "s4": ["S4"]},
    "1380": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"]},
    "671": {"s1": ["S1"], "s2": ["S1"]},
    "755": {"s1": ["S1"], "s2": ["S1"], "s3": ["S2"]},
    "3963": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"]},
    "323": {"s1": ["S1"], "s2": ["S1"]},
    "934": {"s1": ["S2"], "s2": ["S1"], "s3": ["S1"]},
    "4402": {"s1": ["S2"], "s2": ["S1"], "s3": ["S2"]},
    "4261": {"s1": ["S1"], "s2": ["S2"]},
    "3066": {"s1": ["S1"], "s2": ["S2"], "s3": ["S2"]},
    "647": {"s1": ["S1"], "s2": ["S2"], "s3": ["S1"]},
    "2969": {"s1": ["S1"], "s2": ["S1"]},
    "3560": {},
    "4244": {"s2": ["S1"]},
    "4203": {"s1": ["S1"]},
    "88": {"s1": ["S1"], "s2": ["S2"], "s3": ["S3"]},
}


# 对合并槽和显式生态约束进行包级保守修正。值为该包最终可覆盖的共同槽。
OVERRIDES = {
    "4680": {
        "aws-cdk-lib": ["S1"],
        "aws-cdk-aws-autoscaling": [], "aws-cdk-aws-cloudwatch": [],
        "aws-cdk-aws-ecs": [], "aws-cdk-aws-iam": [], "aws-cdk-aws-logs": [],
    },
    "2195": {"opencv-python": ["S1"], "pillow": ["S1", "S2"]},
    "1039": {"soundfile": [], "torch": [], "transformers": ["S2"]},
    "1541": {
        "nltk": [], "fasttext": [], "pillow": [], "moviepy": [],
        "opencv-python": [], "scikit-learn": ["S2"],
        "keras": ["S1", "S2"], "tensorflow": ["S1", "S2"],
    },
    "4433": {"boto3": []},
    "2743": {
        "alibabacloud-gateway-spi": ["S1"], "flask": [], "fastapi": [],
        "pyjwt": [], "flask-caching": [],
    },
    "439": {"boto3": ["S2"], "cryptography": []},
    "1248": {"opentelemetry-api": [], "opentelemetry-sdk": [], "opentelemetry-instrumentation": []},
    "323": {"mysql-connector-python": []},
    "4402": {"taxjar": ["S2"], "census": ["S2"], "censusdata": ["S2"], "requests": []},
    "3560": {"json": ["S1"]},
    "4203": {"kcachegrind": [], "qcachegrind": []},
}


def remap_slots(task_id, pkg):
    prompt_id = task_id.split(":", 1)[1]
    name = pkg["raw_name"].lower()
    if name in OVERRIDES.get(prompt_id, {}):
        return [f"{prompt_id}-{x}" for x in OVERRIDES[prompt_id][name]]
    mapped = []
    for old_slot in pkg["covered_slots"]:
        old_suffix = old_slot.rsplit("-", 1)[-1]
        for new_suffix in CROSS[prompt_id].get(old_suffix, []):
            new_slot = f"{prompt_id}-{new_suffix}"
            if new_slot not in mapped:
                mapped.append(new_slot)
    return mapped


def main():
    common_rows = load_jsonl(RESULTS / "frozen_requirement_slots.jsonl")
    common = {row["task_id"]: row for row in common_rows}
    source = load_jsonl(RESULTS / "annotator_2_formal_labels.jsonl")
    assert len(common) == 60 and len(source) == 300

    output = []
    for row in source:
        task = common[row["task_id"]]
        needed = [slot["slot_id"] for slot in task["slots"]]
        labels = []
        for old_pkg in row["package_labels"]:
            pkg = dict(old_pkg)
            pkg["covered_slots"] = remap_slots(row["task_id"], old_pkg)
            if pkg["covered_slots"]:
                pkg["task_role"] = "core_function_support"
            elif pkg["task_role"] == "core_function_support":
                # 包只支持共同槽中的局部步骤，不能完整满足该槽，但仍可能是辅助。
                pkg["task_role"] = "optional_support"
            labels.append(pkg)

        covered = []
        for slot in needed:
            if any(slot in pkg["covered_slots"] for pkg in labels):
                covered.append(slot)
        uncovered = [slot for slot in needed if slot not in covered]
        coverage = 1.0 if not needed else len(covered) / len(needed)
        if not uncovered:
            adequacy = "adequate"
        elif covered:
            adequacy = "partially_adequate_with_clear_omission"
        else:
            adequacy = "inadequate"

        result = dict(row)
        result["package_labels"] = labels
        result["covered_slots"] = covered
        result["uncovered_slots"] = uncovered
        result["slot_coverage"] = coverage
        result["adequacy"] = adequacy
        result["cannot_judge"] = False
        if adequacy == "adequate":
            result["rationale"] = "全部共同冻结的必要依赖槽均有实际存在且适用的候选覆盖。"
        elif adequacy == "partially_adequate_with_clear_omission":
            result["rationale"] = "仅部分共同冻结的必要依赖槽有实际存在且适用的候选覆盖。"
        else:
            result["rationale"] = "没有共同冻结的必要依赖槽由实际存在且文档适用的候选完整覆盖。"
        result["label_source"] = "independent_blinded_formal_common_slots"
        output.append(result)

    out_path = RESULTS / "annotator_2_formal_labels_common_slots.jsonl"
    out_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output))
    print(f"wrote {len(output)} rows to {out_path}")


if __name__ == "__main__":
    main()
