#!/usr/bin/env python3
"""Integrity checks for the full E2new timed Base and PyPI verifier records."""

import json
import math
from pathlib import Path

from generate_base_timed import generation_seed
from run_existing_generations import MODELS, RESULTS


def read_map(path: Path, model: str):
    records = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            assert record["model"] == model, (path, "wrong model")
            key = str(record["prompt_id"]), int(record["generation"])
            assert key not in records, (path, "duplicate", key)
            records[key] = record
    return records


def main():
    for model, n_prompts in MODELS.items():
        base = read_map(RESULTS / f"base_timed_{model}.jsonl", model)
        verified = read_map(RESULTS / f"base_timed_verified_{model}.jsonl", model)
        assert len(base) == len(verified) == n_prompts * 5
        assert set(base) == set(verified)
        assert len({key[0] for key in base}) == n_prompts
        for key, a in base.items():
            v = verified[key]
            assert a["seed"] == v["seed"] == generation_seed(model, *key)
            assert a["answer"] == v["answer"]
            assert sorted({str(p).strip() for p in a["packages"] if str(p).strip()}) == v["source_packages"]
            assert [c["name"] for c in v["checks"]] == v["source_packages"]
            assert v["retained_packages"] == [c["name"] for c in v["checks"]
                                                if c["status"] in ("exists", "stdlib")]
            assert all(c["status"] in ("exists", "absent", "unknown", "stdlib") for c in v["checks"])
            for field in ("base_generation_seconds", "verify_total_seconds", "bov_total_seconds"):
                assert math.isfinite(float(v[field])) and float(v[field]) >= 0, (model, key, field)
            assert abs(v["bov_total_seconds"] - v["base_generation_seconds"]
                       - v["verify_total_seconds"]) < 1e-8
        print(f"{model}: {n_prompts} prompts, {len(base)} complete paired answers")
    dates = {}
    with (RESULTS / "package_first_release_jsonapi.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            assert row["name"] not in dates
            dates[row["name"]] = row
    assert len(dates) == 6298
    print(f"release-date records: {len(dates)} unique names")


if __name__ == "__main__":
    main()
