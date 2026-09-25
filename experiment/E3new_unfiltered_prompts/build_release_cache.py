#!/usr/bin/env python3
"""Fetch one PyPI JSON first-release record per distinct candidate, outside GPU generation."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from getHallucinationPackage.build_edit_examples import check_std_package, clean_extracted_package_name, normalize  # noqa: E402


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def canonical(raw: str) -> str:
    return clean_extracted_package_name(normalize(raw, "Python"))


def fetch(name: str) -> dict:
    url = f"https://pypi.org/pypi/{name}/json"
    attempts = []
    for _ in range(3):
        try:
            response = requests.get(url, timeout=10)
            attempts.append(response.status_code)
        except requests.RequestException:
            attempts.append("network_error")
            continue
        if response.status_code == 404:
            return {"name": name, "first_upload_utc": None, "status": "not_found", "attempts": attempts}
        if response.status_code != 200:
            continue
        try:
            data = response.json()
        except ValueError:
            return {"name": name, "first_upload_utc": None, "status": "invalid_json", "attempts": attempts}
        times = []
        for releases in data.get("releases", {}).values():
            if not releases:
                continue
            raw = releases[0].get("upload_time")
            if raw:
                try:
                    times.append(dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None))
                except ValueError:
                    pass
        return {
            "name": name,
            "first_upload_utc": min(times).isoformat() if times else None,
            "status": "dated" if times else "no_release_date",
            "attempts": attempts,
        }
    return {"name": name, "first_upload_utc": None, "status": "query_unknown", "attempts": attempts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--seed-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    manifest = {int(row["id"]) for row in read_jsonl(args.manifest)}
    names: set[str] = set()
    for source in args.raw_dir.glob("*.details.jsonl"):
        for row in read_jsonl(source):
            for trial in row["edited"]["trials"]:
                names.update(canonical(raw) for raw in trial.get("packages", []))
    base_paths = (
        REPO / "getHallucinationPackage/result/deepseekcoder/LLM_LY_response.jsonl",
        REPO / "getHallucinationPackage/result/qwen3_release_cutoff/LLM_LY_response.jsonl",
        REPO / "getHallucinationPackage/result/llama3.1_release_cutoff/LLM_LY_response.jsonl",
    )
    for path in base_paths:
        for row in read_jsonl(path):
            if int(row["id"]) in manifest:
                names.update(canonical(raw) for raw in row.get("packages", []))
    names = {name for name in names if name and not check_std_package(name)}

    known = {}
    for row in read_jsonl(args.seed_cache):
        if row.get("status") == "dated" and row.get("first_upload_utc") and row["name"] in names:
            known[row["name"]] = {"name": row["name"], "first_upload_utc": row["first_upload_utc"], "status": "dated", "source": "E2new_JSONAPI_cache"}
    existing_names = set()
    if args.output.exists():
        for row in read_jsonl(args.output):
            if row["name"] in names:
                if row.get("status") != "query_unknown":
                    known[row["name"]] = row
                    existing_names.add(row["name"])
    pending = sorted(names - known.keys())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as handle:
        for name in sorted(names & known.keys()):
            if name not in existing_names and known[name].get("source") == "E2new_JSONAPI_cache":
                handle.write(json.dumps(known[name], ensure_ascii=False) + "\n")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch, name): name for name in pending}
            for future in as_completed(futures):
                row = future.result()
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                known[row["name"]] = row
    missing = names - known.keys()
    if missing:
        raise RuntimeError(f"release cache incomplete: {len(missing)} missing names")
    final_path = args.output.with_name("release_dates_final.jsonl")
    final_path.write_text(
        "".join(json.dumps(known[name], ensure_ascii=False) + "\n" for name in sorted(names)),
        encoding="utf-8",
    )
    report = {
        "candidate_names": len(names),
        "reused_dated": sum(row.get("source") == "E2new_JSONAPI_cache" for row in known.values()),
        "fetched": len(pending),
        "statuses": {status: sum(row["status"] == status for row in known.values()) for status in sorted({row["status"] for row in known.values()})},
        "output": str(args.output),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "deduplicated_final": str(final_path),
        "deduplicated_final_sha256": hashlib.sha256(final_path.read_bytes()).hexdigest(),
    }
    (args.output.parent / "release_cache_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
