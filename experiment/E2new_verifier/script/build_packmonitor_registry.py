#!/usr/bin/env python3
"""Freeze the E2new PyPI evaluation-name snapshot in PackMonitor's JSON format."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
source = RESULTS / "pypi_index_names.txt"
names = source.read_text(encoding="utf-8").splitlines()
if len(names) != len(set(names)) or not names:
    raise ValueError("source index must be nonempty and unique")
output = RESULTS / "pypi_index_packmonitor_registry.json"
output.write_text(json.dumps(names, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
metadata = {"source": str(source), "output": str(output), "count": len(names),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "purpose": "same frozen 2026-09-24 current PyPI name set for PackMonitor constraint and independent evaluation"}
(RESULTS / "pypi_index_packmonitor_registry_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False))
