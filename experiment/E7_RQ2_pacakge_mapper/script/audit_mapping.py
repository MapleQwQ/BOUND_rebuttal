"""Resolve retained RQ2 imports against independent metadata and recompute bounds.

The full-corpus result on AST-invalid code is provisional: line-wise AST and the
archived deterministic extractor may miss imports. Unknown mappings are visible.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parents[1] / "results"
SCRIPT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
HIST_CACHE = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611/rq2_pypi_release_cache.json"
CUTOFFS = {"deepseekcoder": "2023-10-29", "qwen3": "2025-04-29", "llama3.1": "2023-12-31"}
METHODS = ("Base", "BOUND", "ROME", "MEMIT", "DINM", "Full-FT")
FOLDS = "ABCD"
STD = set(sys.stdlib_module_names) | set(sys.builtin_module_names) | {"__future__"}


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_occurrences(filename: str):
    by_generation = defaultdict(set)
    for row in csv.DictReader((OUT / filename).open()):
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        by_generation[key].add((row["import_path"], row["top_level"], row["kind"]))
    return by_generation


def provider_index():
    providers = defaultdict(set)
    evidence = defaultdict(set)
    for file in (OUT / "pypi_evidence").glob("*.json"):
        item = json.loads(file.read_text())
        if item.get("status") != "wheel_verified":
            continue
        project = norm(item["canonical_name"])
        for path in item["import_paths"]:
            providers[path].add(project)
            evidence[(path, project)].add(item["wheel_url"] + "#sha256=" + item["wheel_sha256"])
    local = json.loads((OUT / "local_distribution_metadata.json").read_text())
    for project, item in local.items():
        project = norm(project)
        for path in item["import_paths"]:
            providers[path].add(project)
            evidence[(path, project)].update(item["environment_paths"])
    manual = []
    for row in csv.DictReader((SCRIPT / "manual_adjudications.csv").open()):
        row["distribution"] = norm(row["distribution"]) if row["distribution"] else ""
        manual.append(row)
    return providers, evidence, manual


def resolve(path: str, providers, evidence, manual):
    top = path.split(".", 1)[0]
    override = next((row for row in sorted(manual, key=lambda x: -len(x["import_prefix"]))
                     if path == row["import_prefix"] or path.startswith(row["import_prefix"] + ".")), None)
    if override and override["resolution"] == "local":
        return "local", [], override["evidence_url"], "manual"
    if override and override["resolution"] == "distribution":
        return "resolved", [override["distribution"]], override["evidence_url"], "official_docs"
    exact = sorted(providers[path])
    if len(exact) == 1:
        return "resolved", exact, " | ".join(sorted(evidence[(path, exact[0])])), "file_metadata_exact"
    if len(exact) > 1:
        return "ambiguous_namespace", exact, " | ".join(sorted(next(iter(evidence[(path, x)])) for x in exact)), "file_metadata_multiple"
    top_providers = sorted(providers[top])
    if len(top_providers) == 1:
        return "resolved_top_only", top_providers, " | ".join(sorted(evidence[(top, top_providers[0])])), "subpath_unverified"
    if len(top_providers) > 1:
        return "ambiguous_namespace", top_providers, " | ".join(sorted(next(iter(evidence[(top, x)])) for x in top_providers)), "top_level_multiple"
    return "unknown", [], "", "no_independent_evidence"


def package_valid(project: str, model: str, release_cache: dict):
    release = release_cache.get(norm(project))
    if not release:
        return None
    try:
        return dt.datetime.fromisoformat(release.replace("Z", "+00:00").replace("+00:00", "")) <= dt.datetime.fromisoformat(CUTOFFS[model])
    except ValueError:
        return None


def main():
    generations = list(csv.DictReader((OUT / "generations.csv").open()))
    ast_imports = load_occurrences("ast_import_occurrences.csv")
    tolerant_imports = load_occurrences("tokenized_import_occurrences.csv")
    parso_line_verified = load_occurrences("parso_verified_single_line_imports.csv")
    token_checks = {(r["model"], r["method"], r["fold"], r["generation_id"]): r
                    for r in csv.DictReader((OUT / "tokenized_recovery_by_generation.csv").open())}
    providers, evidence, manual = provider_index()
    release_cache = json.loads(HIST_CACHE.read_text())
    all_paths = {path for source in (ast_imports, tolerant_imports, parso_line_verified) for items in source.values()
                 for path, _, kind in items if kind == "absolute"}
    all_paths.update(name for row in generations for name in json.loads(row["mapper_input"]) if name not in STD)
    resolutions = {path: resolve(path, providers, evidence, manual) for path in all_paths}
    mapping_rows = []
    for path in sorted(resolutions):
        status, projects, url, detail = resolutions[path]
        mapping_rows.append(dict(import_path=path, top_level=path.split(".", 1)[0], status=status,
                                 distributions=json.dumps(projects), evidence=url, evidence_type=detail))
    with (OUT / "audited_mapping.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mapping_rows[0]))
        writer.writeheader(); writer.writerows(mapping_rows)
    records = []
    for row in generations:
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        if row["ast_status"] == "ast_ok":
            observed = ast_imports.get(key, set())
            extraction = "full_ast"
        else:
            observed = set(tolerant_imports.get(key, set())) | parso_line_verified.get(key, set())
            observed_tops = {top for _, top, kind in observed if kind == "absolute"}
            for top in json.loads(row["mapper_input"]):
                if top not in observed_tops and top and top not in STD:
                    observed.add((top, top, "absolute"))
            extraction = "tokenize_ast_plus_parso_full_line_ast_plus_archived_fallback"
        paths = sorted({path for path, _, kind in observed if kind == "absolute"})
        local_paths = sorted({path for path in paths if resolutions[path][0] == "local"})
        paths = [path for path in paths if path not in local_paths]
        resolved = {path: resolutions[path][1][0] for path in paths if resolutions[path][0] in {"resolved", "resolved_top_only"}}
        uncertain = {path: resolutions[path][0] for path in paths if resolutions[path][0] not in {"resolved", "resolved_top_only"}}
        labels = {path: package_valid(project, row["model"], release_cache) for path, project in resolved.items()}
        unknown_date = {path for path, value in labels.items() if value is None}
        known_valid = {project for path, project in resolved.items() if labels[path] is True}
        known_hall = {project for path, project in resolved.items() if labels[path] is False}
        unknown_count = len(uncertain) + len(unknown_date)
        old_output = set(map(norm, json.loads(row["mapper_output"])))
        expected = set(resolved.values())
        mapping_known = not uncertain
        mapping_correct = (old_output == expected) if mapping_known else None
        old_valid = set(map(norm, json.loads(row["original_valid"])))
        old_hall = set(map(norm, json.loads(row["original_hallucinated"])))
        label_known = mapping_known and not unknown_date
        label_agree = (old_valid == known_valid and old_hall == known_hall) if label_known else None
        records.append(dict(model=row["model"], method=row["method"], fold=row["fold"],
                            generation_id=row["generation_id"], prompt_id=row["prompt_id"],
                            extraction=extraction, ast_status=row["ast_status"],
                            tokenizer_error=token_checks[key]["token_error"],
                            import_paths=json.dumps(paths, ensure_ascii=False), local_paths=json.dumps(local_paths),
                            resolved_distributions=json.dumps(sorted(expected)),
                            unresolved_imports=json.dumps(uncertain, sort_keys=True),
                            unknown_date_paths=json.dumps(sorted(unknown_date)),
                            original_mapper_output=json.dumps(sorted(old_output)),
                            original_valid=json.dumps(sorted(old_valid)), original_hallucinated=json.dumps(sorted(old_hall)),
                            audited_valid=json.dumps(sorted(known_valid)), audited_hallucinated=json.dumps(sorted(known_hall)),
                            mapping_known=int(mapping_known), mapping_correct="" if mapping_correct is None else int(mapping_correct),
                            label_known=int(label_known), label_agree="" if label_agree is None else int(label_agree),
                            known_valid_count=len(known_valid), known_hall_count=len(known_hall),
                            unknown_count=unknown_count))
    with (OUT / "per_generation_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    summaries = []
    for model in CUTOFFS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                subset = [r for r in records if (r["model"], r["method"], r["fold"]) == (model, method, fold)]
                n = len(subset)
                v = sum(r["known_valid_count"] for r in subset)
                h = sum(r["known_hall_count"] for r in subset)
                u = sum(r["unknown_count"] for r in subset)
                h_answers = sum(r["known_hall_count"] > 0 for r in subset)
                v_answers = sum(r["known_valid_count"] > 0 for r in subset)
                unknown_answers = sum(r["unknown_count"] > 0 for r in subset)
                archive_h_answers = sum(bool(json.loads(r["original_hallucinated"])) for r in subset)
                archive_v_answers = sum(bool(json.loads(r["original_valid"])) for r in subset)
                archive_h = sum(len(json.loads(r["original_hallucinated"])) for r in subset)
                archive_v = sum(len(json.loads(r["original_valid"])) for r in subset)
                summaries.append(dict(model=model, method=method, fold=fold, n=n,
                                      ast_failure=sum(r["ast_status"] != "ast_ok" for r in subset),
                                      tokenizer_error=sum(bool(r["tokenizer_error"]) for r in subset),
                                      ast_failure_no_import_complete_tokenization=sum(
                                          r["ast_status"] != "ast_ok" and not r["tokenizer_error"] and
                                          not json.loads(r["import_paths"]) for r in subset),
                                      mapping_known=sum(r["mapping_known"] for r in subset),
                                      mapping_correct=sum(r["mapping_correct"] == 1 for r in subset),
                                      label_known=sum(r["label_known"] for r in subset),
                                      label_agree=sum(r["label_agree"] == 1 for r in subset),
                                      unknown_answers=unknown_answers, known_valid_packages=v, known_hall_packages=h,
                                      unknown_package_slots=u,
                                      archived_sample_hr=archive_h_answers/n,
                                      archived_package_hr=archive_h/(archive_h+archive_v) if archive_h+archive_v else 0,
                                      archived_valid_rate=archive_v_answers/n,
                                      audited_sample_hr_lower=h_answers/n,
                                      audited_sample_hr_upper=(h_answers+sum(r["known_hall_count"]==0 and
                                          (r["unknown_count"]>0 or r["ast_status"]!="ast_ok") for r in subset))/n,
                                      audited_sample_hr_tokenizer_scenario_upper=(h_answers+sum(r["known_hall_count"]==0 and
                                          (r["unknown_count"]>0 or bool(r["tokenizer_error"])) for r in subset))/n,
                                      audited_package_hr_one_slot_min=h/(h+v+u) if h+v+u else 0,
                                      audited_package_hr_one_slot_max=(h+u)/(h+v+u) if h+v+u else 0,
                                      audited_valid_rate_lower=v_answers/n,
                                      audited_valid_rate_upper=(v_answers+sum(r["known_valid_count"]==0 and
                                          (r["unknown_count"]>0 or r["ast_status"]!="ast_ok") for r in subset))/n,
                                      audited_valid_rate_tokenizer_scenario_upper=(v_answers+sum(r["known_valid_count"]==0 and
                                          (r["unknown_count"]>0 or bool(r["tokenizer_error"])) for r in subset))/n))
    with (OUT / "rq2_metric_bounds_by_fold.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    print(json.dumps({"mapping_status":dict(Counter(r["status"] for r in mapping_rows)),
                      "fully_resolved_answers":sum(r["mapping_known"] for r in records),
                      "label_known_answers":sum(r["label_known"] for r in records),
                      "mapping_exact_answers":sum(r["mapping_correct"]==1 for r in records),
                      "exact_label_agreement_answers":sum(r["label_agree"]==1 for r in records)},indent=2))


if __name__ == "__main__":
    main()
