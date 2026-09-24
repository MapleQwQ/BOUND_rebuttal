#!/usr/bin/env python3
"""为 E3 outputs 同时导出 model-cutoff 与共同 deployment snapshot 标签。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from getHallucinationPackage.build_edit_examples import check_std_package


def norm(value: str) -> str:
    return re.sub(r"[-_.]+", "-", str(value).strip().lower())


def dump(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--pattern", default="confirm200_*_seed20260926.details.jsonl")
    args = parser.parse_args()

    raw_registry = json.loads(args.registry.read_text(encoding="utf-8"))
    registry = {norm(value) for value in raw_registry}
    snapshot_sha = hashlib.sha256(args.registry.read_bytes()).hexdigest()
    deployment_rows = []
    cutoff_rows = []
    files = sorted(args.result_dir.glob(args.pattern))
    for path in files:
        condition = path.name.removesuffix(".details.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for trial in row["edited"]["trials"]:
                packages = sorted({str(value).strip() for value in trial.get("packages", []) if str(value).strip()})
                stdlib = sorted(value for value in packages if check_std_package(value))
                listed = sorted(value for value in packages if value not in stdlib and norm(value) in registry)
                not_listed = sorted(value for value in packages if value not in stdlib and norm(value) not in registry)
                common = {
                    "condition": condition,
                    "prompt_id": row["id"],
                    "generation": trial.get("generation"),
                    "seed": trial.get("seed"),
                    "packages": packages,
                }
                deployment_rows.append(
                    {
                        **common,
                        "snapshot_listed": listed,
                        "stdlib": stdlib,
                        "snapshot_not_listed": not_listed,
                        "contains_snapshot_not_listed": bool(not_listed),
                        "snapshot_sha256": snapshot_sha,
                        "interpretation": "not_listed is not automatically never-existing",
                    }
                )
                cutoff_rows.append(
                    {
                        **common,
                        "model_cutoff_valid": sorted(set(trial.get("valid", []))),
                        "model_cutoff_hallucinated": sorted(set(trial.get("hallucinated", []))),
                        "contains_model_cutoff_hallucination": bool(trial.get("hallucinated", [])),
                    }
                )
    dump(args.result_dir / "deployment_snapshot_labels.jsonl", deployment_rows)
    dump(args.result_dir / "model_cutoff_labels.jsonl", cutoff_rows)
    summary = {
        "input_files": len(files),
        "trials": len(deployment_rows),
        "snapshot_size_raw": len(raw_registry),
        "snapshot_size_normalized": len(registry),
        "snapshot_sha256": snapshot_sha,
        "deployment_responses_with_not_listed": sum(row["contains_snapshot_not_listed"] for row in deployment_rows),
        "model_cutoff_responses_with_hallucination": sum(row["contains_model_cutoff_hallucination"] for row in cutoff_rows),
    }
    (args.result_dir / "dual_registry_label_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
