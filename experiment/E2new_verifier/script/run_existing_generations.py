#!/usr/bin/env python3
"""Audit old E2 generations and run the E2new online Base verifier.

Only the verifier calls PyPI. Existing generated text is never regenerated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

MODELS = {"deepseekcoder": 541, "qwen3-release": 409, "llama3.1-release": 934}
FOLDS = "ABCD"
ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
RESULTS = Path(__file__).resolve().parents[1] / "results"
SOURCE_FILE = "blast_50/eval_unseen_prompts.json"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(model: str, fold: str) -> tuple[Path, dict]:
    path = SOURCE / model / f"fold_{fold}" / SOURCE_FILE
    with path.open(encoding="utf-8") as stream:
        return path, json.load(stream)


def trials(row: dict, condition: str) -> list[dict]:
    value = row[condition]["trials"]
    if len(value) != 5 or sorted(t["generation"] for t in value) != list(range(5)):
        raise ValueError(f"invalid trial set: {row['id']} {condition}")
    return value


def signature(trial: dict) -> tuple:
    return trial.get("answer"), tuple(trial.get("packages", []))


def audit() -> dict:
    RESULTS.mkdir(exist_ok=True)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "source_root": str(SOURCE), "models": {}}
    for model, expected in MODELS.items():
        fold_rows = {}
        files = {}
        for fold in FOLDS:
            path, payload = load(model, fold)
            rows = {str(row["id"]): row for row in payload["details"]}
            if len(rows) != len(payload["details"]) or len(rows) != expected:
                raise ValueError(f"row count/id uniqueness failed: {model} {fold}")
            fold_rows[fold] = rows
            files[fold] = {"path": str(path), "sha256": sha256(path)}
        ids = set(fold_rows["A"])
        if any(set(rows) != ids for rows in fold_rows.values()):
            raise ValueError(f"fold task mismatch: {model}")
        prompt_hashes = {}
        base_candidates = 0
        base_unique = set()
        missing_base_time = 0
        for prompt_id in sorted(ids):
            reference = fold_rows["A"][prompt_id]
            prompt = reference["question"]
            prompt_hashes[prompt_id] = hashlib.sha256(prompt.encode()).hexdigest()
            base_ref = trials(reference, "baseline")
            for trial in base_ref:
                packages = set(str(x).strip() for x in trial.get("packages", []) if str(x).strip())
                base_candidates += len(packages)
                base_unique.update(packages)
                if not any(key in trial for key in ("latency_seconds", "generation_seconds", "elapsed_seconds")):
                    missing_base_time += 1
            for fold in FOLDS:
                row = fold_rows[fold][prompt_id]
                if row["question"] != prompt:
                    raise ValueError(f"prompt text mismatch: {model} {prompt_id} {fold}")
                if [signature(t) for t in trials(row, "baseline")] != [signature(t) for t in base_ref]:
                    raise ValueError(f"Base differs across folds: {model} {prompt_id} {fold}")
                trials(row, "edited")
        manifest["models"][model] = {
            "prompt_count": len(ids), "base_trial_count": len(ids) * 5,
            "bound_trial_count": len(ids) * 5 * 4,
            "base_candidate_mentions": base_candidates,
            "unique_base_names": len(base_unique),
            "base_trials_without_generation_time": missing_base_time,
            "prompt_hashes": prompt_hashes, "files": files,
        }
    (RESULTS / "source_audit.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def is_stdlib(name: str) -> bool:
    return name in sys.stdlib_module_names


def query(session: requests.Session, name: str, pause: float) -> dict:
    normalized = normalize(name)
    if is_stdlib(name):
        return {"name": name, "normalized": normalized, "status": "stdlib", "attempts": 0, "seconds": 0.0}
    if not NAME_RE.fullmatch(name):
        return {"name": name, "normalized": normalized, "status": "unknown", "reason": "invalid_name_syntax", "attempts": 0, "seconds": 0.0}
    url = f"https://pypi.org/simple/{quote(normalized, safe='')}/"
    attempts = []
    for attempt in range(2):
        start = time.perf_counter()
        try:
            response = session.head(url, timeout=5, allow_redirects=True)
            elapsed = time.perf_counter() - start
            attempts.append({"http_status": response.status_code, "seconds": elapsed,
                             "date": response.headers.get("Date"),
                             "serial": response.headers.get("X-PyPI-Last-Serial")})
            if response.status_code == 200:
                status = "exists"
            elif response.status_code == 404:
                status = "absent"
            elif response.status_code in (408, 429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1)
                continue
            else:
                status = "unknown"
            break
        except requests.RequestException as exc:
            elapsed = time.perf_counter() - start
            attempts.append({"error": type(exc).__name__, "seconds": elapsed})
            if attempt == 0:
                time.sleep(1)
                continue
            status = "unknown"
    if pause:
        time.sleep(pause)
    return {"name": name, "normalized": normalized, "status": status,
            "attempts": attempts, "seconds": sum(x["seconds"] for x in attempts)
            + (1 if len(attempts) == 2 else 0) + pause}


def replay(limit: int | None, pause: float) -> None:
    if not (RESULTS / "source_audit.json").exists():
        audit()
    output = RESULTS / "online_verifier_answers.jsonl"
    completed = set()
    if output.exists():
        with output.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    key = (record["model"], str(record["prompt_id"]), record["generation"])
                    if key in completed:
                        raise ValueError(f"duplicate output: {key}")
                    completed.add(key)
    session = requests.Session()
    session.headers.update({"User-Agent": "BOUND-E2new-research-verifier/1.0 (PyPI metadata audit)"})
    done = 0
    with output.open("a", encoding="utf-8") as stream:
        for model in MODELS:
            _, payload = load(model, "A")
            for row in payload["details"]:
                for trial in trials(row, "baseline"):
                    key = (model, str(row["id"]), trial["generation"])
                    if key in completed:
                        continue
                    if limit is not None and done >= limit:
                        return
                    parse_start = time.perf_counter()
                    names = sorted({str(p).strip() for p in trial.get("packages", []) if str(p).strip()})
                    parse_seconds = time.perf_counter() - parse_start
                    checks = [query(session, name, pause) for name in names]
                    filter_start = time.perf_counter()
                    retained = [x["name"] for x in checks if x["status"] in ("exists", "stdlib")]
                    filtered_seconds = time.perf_counter() - filter_start
                    record = {"model": model, "prompt_id": row["id"], "generation": trial["generation"],
                              "query_utc": datetime.now(timezone.utc).isoformat(),
                              "answer": trial.get("answer", ""), "source_packages": names,
                              "checks": checks, "retained_packages": retained,
                              "parse_seconds": parse_seconds, "filter_seconds": filtered_seconds,
                              "verify_total_seconds": parse_seconds + filtered_seconds + sum(c["seconds"] for c in checks),
                              "base_generation_seconds": None, "bov_total_seconds": None}
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    done += 1
                    if done % 100 == 0:
                        print(f"{datetime.now(timezone.utc).isoformat()} new={done} total={len(completed) + done} model={model}", flush=True)


def snapshot_index() -> None:
    """Fetch authoritative current project names for independent output labeling."""
    RESULTS.mkdir(exist_ok=True)
    response = requests.get("https://pypi.org/simple/", headers={
        "Accept": "application/vnd.pypi.simple.v1+json",
        "User-Agent": "BOUND-E2new-research-verifier/1.0 (PyPI name snapshot)",
    }, timeout=120)
    response.raise_for_status()
    payload = response.json()
    names = sorted({normalize(row["name"]) for row in payload["projects"]})
    metadata = {"downloaded_utc": datetime.now(timezone.utc).isoformat(),
                "response_date": response.headers.get("Date"),
                "serial": response.headers.get("X-PyPI-Last-Serial"),
                "api_version": payload.get("meta", {}).get("api-version"),
                "raw_sha256": hashlib.sha256(response.content).hexdigest(),
                "project_count": len(names), "url": response.url}
    (RESULTS / "pypi_index_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "pypi_index_names.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("audit", "replay", "snapshot"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--pause", type=float, default=0.0)
    args = parser.parse_args()
    if args.action == "audit":
        print(json.dumps({key: {k: v for k, v in value.items() if k not in ("prompt_hashes", "files")}
                          for key, value in audit()["models"].items()}, indent=2))
    elif args.action == "replay":
        replay(args.limit, args.pause)
    else:
        snapshot_index()


if __name__ == "__main__":
    main()
