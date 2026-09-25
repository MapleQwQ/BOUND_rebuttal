#!/usr/bin/env python3
"""Fetch first release dates using the replication package's JSON API rule."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

from run_existing_generations import FOLDS, MODELS, RESULTS, load, normalize, trials

LOCAL = threading.local()


def names_to_audit() -> list[str]:
    index = set((RESULTS / "pypi_index_names.txt").read_text(encoding="utf-8").splitlines())
    names = set()
    for model in MODELS:
        timed_base = RESULTS / f"base_timed_{model}.jsonl"
        if timed_base.exists():
            with timed_base.open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        trial = json.loads(line)
                        names.update(normalize(str(p)) for p in trial.get("packages", [])
                                     if str(p).strip() and str(p) not in sys.stdlib_module_names)
        for fold in FOLDS:
            _, data = load(model, fold)
            for row in data["details"]:
                conditions = ("baseline", "edited") if fold == "A" else ("edited",)
                for condition in conditions:
                    for trial in trials(row, condition):
                        names.update(normalize(str(p)) for p in trial.get("packages", [])
                                     if str(p).strip() and str(p) not in sys.stdlib_module_names)
    return sorted(names & index)


def thread_session() -> requests.Session:
    session = getattr(LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"Accept": "application/json",
                                "User-Agent": "BOUND-E2new-research-verifier/1.0 (release date audit)"})
        LOCAL.session = session
    return session


def fetch(name: str) -> dict:
    session = thread_session()
    url = f"https://pypi.org/pypi/{quote(name, safe='')}/json"
    attempts = []
    response = None
    for attempt in range(2):
        start = time.perf_counter()
        try:
            response = session.get(url, timeout=12)
            attempts.append({"status": response.status_code, "seconds": time.perf_counter() - start})
            if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1)
                continue
            break
        except requests.RequestException as exc:
            attempts.append({"error": type(exc).__name__, "seconds": time.perf_counter() - start})
            response = None
            if attempt == 0:
                time.sleep(1)
    first = None
    status = "unknown"
    content_hash = None
    if response is not None:
        content_hash = hashlib.sha256(response.content).hexdigest()
        if response.status_code == 200:
            try:
                payload = response.json()
                # Match bound.py: first file from each nonempty release.
                dates = [details[0].get("upload_time") for details in payload.get("releases", {}).values()
                         if details and details[0].get("upload_time")]
                first = min(dates) if dates else None
                status = "dated" if first else "no_file_date"
            except (ValueError, TypeError):
                status = "bad_json"
        elif response.status_code == 404:
            # Project JSON can be 404 while Simple still lists a project with no files.
            status = "json_404_no_release_metadata"
    time.sleep(0.1)
    return {"name": name, "first_upload_utc": first, "status": status,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "http_attempts": attempts, "content_sha256": content_hash,
            "url": url}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1, choices=range(1, 5))
    args = parser.parse_args()
    names = names_to_audit()
    output = RESULTS / "package_first_release_jsonapi.jsonl"
    done = set()
    if output.exists():
        with output.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    name = json.loads(line)["name"]
                    if name in done:
                        raise ValueError(f"duplicate release record: {name}")
                    done.add(name)
    missing = [name for name in names if name not in done]
    print(f"target={len(names)} completed={len(done)} workers={args.workers}", flush=True)
    added = 0
    with output.open("a", encoding="utf-8") as stream:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(fetch, name): name for name in missing}
            for future in as_completed(pending):
                record = future.result()
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                added += 1
                if added % 100 == 0:
                    print(f"{datetime.now(timezone.utc).isoformat()} added={added} completed={len(done) + added}/{len(names)}", flush=True)


if __name__ == "__main__":
    main()
