#!/usr/bin/env python3
"""Load one frozen BOUND adapter and generate one recommendation.

This is only an infrastructure smoke test.  It intentionally performs no
registry query and must not be included in E2 metric estimates.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch

from knowledgeEdit.package_edit import gen_chat, load_model
from knowledgeEdit.package_edit_utils import recommendation_messages, split_recommendation_packages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--source-eval", type=Path, required=True)
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.source_eval.read_text(encoding="utf-8"))
    row = next((item for item in payload["details"] if str(item["id"]) == str(args.prompt_id)), None)
    if row is None:
        raise SystemExit(f"prompt {args.prompt_id} not found")

    started = datetime.now(timezone.utc).isoformat()
    model, tokenizer = load_model(args.model_path, args.adapter_dir)
    answer = gen_chat(
        model,
        tokenizer,
        recommendation_messages("Python", row["question"]),
        max_new_tokens=64,
        do_sample=False,
    )
    result = {
        "status": "completed",
        "scope": "adapter-load-and-generation-smoke-only",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "cuda_device": torch.cuda.current_device() if torch.cuda.is_available() else None,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model_path": str(args.model_path),
        "adapter_dir": str(args.adapter_dir),
        "prompt_id": row["id"],
        "question": row["question"],
        "answer": answer,
        "packages": split_recommendation_packages(answer, "Python"),
        "registry_validation": "not_run",
        "included_in_metrics": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
