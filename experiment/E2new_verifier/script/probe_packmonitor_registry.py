#!/usr/bin/env python3
"""CPU-only probe of PackMonitor grammar against the frozen E2new name list."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from llguidance import hf
from transformers import AutoTokenizer

from packmonitor_generate import PackMonitor


class TypoPatchedPackMonitor(PackMonitor):
    def make_grammar(self, package_list):
        return super().make_grammar(package_list).replace("NATATURAL_LANG", "NATURAL_LANG")


ROOT = Path(__file__).resolve().parents[4]
RESULTS = Path(__file__).resolve().parents[1] / "results"
parser = argparse.ArgumentParser()
parser.add_argument("--model", choices=("deepseekcoder", "qwen3-release", "llama3.1-release"), default="deepseekcoder")
args = parser.parse_args()
model_paths = {"deepseekcoder": "/data0/shuhanliu/models/deepseekcoder",
               "qwen3-release": "/data0/shuhanliu/models/qwen3-8B",
               "llama3.1-release": "/data0/shuhanliu/models/llama3.1"}
registry = RESULTS / "pypi_index_packmonitor_registry.json"
names = json.loads(registry.read_text(encoding="utf-8"))
tokenizer = AutoTokenizer.from_pretrained(model_paths[args.model], local_files_only=True)
probe = object.__new__(TypoPatchedPackMonitor)
probe.ll_tokenizer = hf.from_tokenizer(tokenizer, n_vocab=len(tokenizer))
probe.matcher_cache = {}
start = time.perf_counter()
matcher, _ = probe.get_cached_matcher(names)
elapsed = time.perf_counter() - start
result = {"checked_utc": datetime.now(timezone.utc).isoformat(), "registry": str(registry),
          "n_names": len(names), "model_tokenizer": model_paths[args.model],
          "matcher_build_seconds": elapsed, "matcher_is_none": matcher is None,
          "matcher_error": matcher.get_error() if matcher is not None and matcher.is_error() else None,
          "scope": "CPU grammar/tokenizer compilation only; not a generation or GPU compatibility test"}
(RESULTS / f"packmonitor_registry_cpu_probe_{args.model}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
if args.model == "deepseekcoder":
    (RESULTS / "packmonitor_registry_cpu_probe.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
if matcher is None or matcher.is_error():
    raise SystemExit(1)
