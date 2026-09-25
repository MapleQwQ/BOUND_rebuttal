"""Audit original RQ2 candidate labels against archived first-release evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
OUT = E5 / "results/04_sequence_margin"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
JSON_CACHES = (
    ROOT / "knowledgeEdit/results/rq2_cross_task_20260611/rq2_pypi_release_cache.json",
    ROOT / "knowledgeEdit/results/ccfa_supplement_20260604_final/pypi_first_release_cache.json",
)
JSONL_CACHES = (
    ROOT / "BOUND_rebuttal/experiment/E3new_unfiltered_prompts/results/release_dates_final.jsonl",
    ROOT / "BOUND_rebuttal/experiment/E2new_verifier/results/package_first_release.jsonl",
    ROOT / "BOUND_rebuttal/experiment/E2new_verifier/results/package_first_release_jsonapi.jsonl",
)


def main() -> None:
    evidence: dict[str, set[date]] = defaultdict(set)
    sources = {}
    cutoff = {}
    for model in MODELS:
        case = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611" / model / "Base/fold_A/test100_case_repeat5/case.json"
        cutoff[model] = date.fromisoformat(json.loads(case.read_text(encoding="utf-8"))["model_cutoff"])
        sources[str(case.relative_to(ROOT))] = hashlib.sha256(case.read_bytes()).hexdigest()
    for path in JSON_CACHES + JSONL_CACHES:
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == ".json":
            items = json.loads(path.read_text(encoding="utf-8")).items()
        else:
            items = ((row["name"], row.get("first_upload_utc")) for row in
                     map(json.loads, path.read_text(encoding="utf-8").splitlines()))
        for name, timestamp in items:
            if timestamp:
                evidence[name].add(date.fromisoformat(str(timestamp)[:10]))
    registry_file = ROOT / "BOUND_rebuttal/experiment/E2new_verifier/results/pypi_index_names.txt"
    registry = set(registry_file.read_text(encoding="utf-8").splitlines())
    sources[str(registry_file.relative_to(ROOT))] = hashlib.sha256(registry_file.read_bytes()).hexdigest()

    original = [json.loads(line) for line in (OUT / "candidate_manifest_preliminary.jsonl").read_text(encoding="utf-8").splitlines()]
    records = []
    counts: dict[str, Counter] = defaultdict(Counter)
    for row in original:
        model = row["model"]
        for label, key in (("valid", "valid_candidates"), ("hallucinated", "hallucinated_candidates")):
            for name in row[key]:
                dated = sorted(evidence.get(name, ()))
                first = dated[0] if dated else None
                present_now = name in registry
                if first is None:
                    status = "unknown_present" if present_now else "unknown_absent"
                else:
                    status = "pre_cutoff" if first < cutoff[model] else "post_cutoff"
                records.append({"model": model, "prompt_id": row["prompt_id"], "label": label,
                                "name": name, "first_release_earliest": first.isoformat() if first else None,
                                "n_distinct_cache_dates": len(dated), "present_2026_index": present_now,
                                "status": status})
                counts[model][f"{label}_{status}"] += 1
    with (OUT / "candidate_date_audit.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    summary = {"cutoffs": {model: value.isoformat() for model, value in cutoff.items()},
               "source_sha256": sources, "counts": {model: dict(counter) for model, counter in counts.items()},
               "rule": "earliest dated release across archived caches; absent current index without release date remains uncertain"}
    (OUT / "candidate_date_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["counts"], indent=2))


if __name__ == "__main__":
    main()
