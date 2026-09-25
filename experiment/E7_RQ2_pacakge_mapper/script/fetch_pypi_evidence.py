"""Fetch official PyPI metadata/wheel file lists for mechanical mapper candidates.

This is candidate verification, not proof that all providers have been found.
No wheel code is executed. Run with --workers 6 after inventory creation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "results"
CACHE = OUT / "pypi_evidence"
MAX_WHEEL_BYTES = 5_000_000
USER_AGENT = "BOUND-RQ2-import-audit/1.0 (research metadata verification)"


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def request(url: str, limit: int):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > limit:
            raise ValueError("response_too_large")
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("response_too_large")
        return content


def project_evidence(project: str) -> dict:
    source_url = f"https://pypi.org/pypi/{project}/json"
    result = dict(candidate=project, source_url=source_url, status="unknown", canonical_name="",
                  version="", wheel_url="", wheel_sha256="", wheel_size=0, top_level_txt=[],
                  import_paths=[], matched_import_paths=[], error="")
    try:
        meta = json.loads(request(source_url, 12_000_000))
    except urllib.error.HTTPError as exc:
        result["status"] = "pypi_404" if exc.code == 404 else "http_error"
        result["error"] = f"HTTP {exc.code}"
        return result
    except Exception as exc:
        result["status"] = "metadata_error"
        result["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return result
    result["canonical_name"] = meta["info"].get("name") or project
    result["version"] = meta["info"].get("version") or ""
    wheels = [item for item in meta.get("urls", []) if item.get("packagetype") == "bdist_wheel"
              and item.get("size", 10**12) <= MAX_WHEEL_BYTES]
    if not wheels:
        result["status"] = "exists_no_small_wheel"
        return result
    wheel = min(wheels, key=lambda item: (item["size"], item["filename"]))
    result["wheel_url"] = wheel["url"]
    result["wheel_size"] = wheel["size"]
    try:
        payload = request(wheel["url"], MAX_WHEEL_BYTES)
        digest = hashlib.sha256(payload).hexdigest()
        result["wheel_sha256"] = digest
        if digest != wheel["digests"]["sha256"]:
            raise ValueError("wheel_sha256_mismatch")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            paths = archive.namelist()
            top_files = [name for name in paths if name.endswith(".dist-info/top_level.txt")]
            if top_files:
                result["top_level_txt"] = sorted(set(archive.read(top_files[0]).decode("utf-8", "replace").split()))
            modules = set()
            for name in paths:
                if ".dist-info/" in name or ".data/" in name or ".egg-info/" in name:
                    continue
                if name.endswith("/__init__.py"):
                    pieces = name[:-len("/__init__.py")].split("/")
                elif name.endswith((".py", ".so", ".pyd")):
                    pieces = name.split("/")
                    if name.endswith(".py"):
                        pieces[-1] = pieces[-1][:-3]
                    elif ".so" in pieces[-1]:
                        pieces[-1] = pieces[-1].split(".so", 1)[0].split(".", 1)[0]
                    elif ".pyd" in pieces[-1]:
                        pieces[-1] = pieces[-1].split(".pyd", 1)[0].split(".", 1)[0]
                else:
                    continue
                if pieces and all(piece.isidentifier() for piece in pieces):
                    for n in range(1, len(pieces) + 1):
                        modules.add(".".join(pieces[:n]))
            result["import_paths"] = sorted(modules)
        result["status"] = "wheel_verified"
    except Exception as exc:
        result["status"] = "wheel_error"
        result["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-occurrences", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-candidates", type=int, default=0)
    parser.add_argument("--max-wheel-mb", type=int, default=5)
    parser.add_argument("--retry-no-small-wheel", action="store_true")
    args = parser.parse_args()
    global MAX_WHEEL_BYTES
    MAX_WHEEL_BYTES = args.max_wheel_mb * 1_000_000
    CACHE.mkdir(exist_ok=True)
    inventory = list(csv.DictReader((OUT / "unique_import_inventory.csv").open()))
    generation_rows = list(csv.DictReader((OUT / "generations.csv").open()))
    mapper_packages = Counter()
    for row in generation_rows:
        mapper_packages.update(json.loads(row["mapper_output"]))
    # Mapper outputs are search leads only; acceptance later requires independent file metadata.
    candidates = {norm(row["top_level"]) for row in inventory if int(row["answer_occurrences"]) >= args.min_occurrences}
    candidates.update(norm(name) for name, count in mapper_packages.items() if count >= args.min_occurrences)
    candidates.discard("none")
    order = sorted(candidates, key=lambda name: (-mapper_packages[name], name))
    if args.max_candidates:
        order = order[:args.max_candidates]
    pending = []
    for name in order:
        file = CACHE / f"{name}.json"
        if not file.exists():
            pending.append(name)
        elif args.retry_no_small_wheel and json.loads(file.read_text()).get("status") == "exists_no_small_wheel":
            pending.append(name)
    print(f"candidate count={len(order)} cached={len(order)-len(pending)} pending={len(pending)}", flush=True)
    counts = Counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(project_evidence, name): name for name in pending}
        for i, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = dict(candidate=name, status="worker_error", error=f"{type(exc).__name__}: {exc}")
            (CACHE / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
            counts[result["status"]] += 1
            if i % 50 == 0:
                print(f"completed={i}/{len(pending)} status={dict(counts)}", flush=True)
    print(json.dumps(dict(counts), indent=2), flush=True)


if __name__ == "__main__":
    main()
