"""Reject Parso recovery artifacts unless the original physical line parses.

This intentionally misses multiline imports; it is a high-specificity
cross-check, not a replacement for the tokenizer-based primary extractor.
"""
from __future__ import annotations

import ast
import csv
import json
import textwrap
from collections import Counter, defaultdict

from build_inventory import OUT, METHODS, MODELS, FOLDS, archived_code, rows, source_path


def import_triples(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update((a.name, a.name.split(".", 1)[0]) for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add((node.module, node.module.split(".", 1)[0]))
        elif isinstance(node, ast.ImportFrom) and node.level:
            found.add(("." * node.level + (node.module or ""), ""))
    return found


def main():
    candidates = defaultdict(list)
    for row in csv.DictReader((OUT / "parso_import_occurrences_failed.csv").open()):
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        candidates[key].append(row)
    tokenized = defaultdict(set)
    for row in csv.DictReader((OUT / "tokenized_import_occurrences.csv").open()):
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        tokenized[key].add((row["import_path"], row["top_level"], row["kind"]))
    accepted, rejected = [], []
    for model, hist_model in MODELS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                for answer in rows(source_path(model, hist_model, method, fold)):
                    key = (model, method, fold, str(answer["id"]))
                    if key not in candidates:
                        continue
                    lines = archived_code(answer["tasks"]["code"]["code_generation_raw"]).splitlines()
                    cache = {}
                    for row in candidates[key]:
                        line_no = int(row["line"])
                        if line_no not in cache:
                            if not 0 < line_no <= len(lines):
                                cache[line_no] = set()
                            else:
                                try:
                                    tree = ast.parse(textwrap.dedent(lines[line_no-1]).strip(), mode="exec")
                                    cache[line_no] = import_triples(tree)
                                except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
                                    cache[line_no] = set()
                        outcome = (row["import_path"], row["top_level"]) in cache[line_no]
                        result = dict(row, accepted_by_full_line_ast=int(outcome),
                                      parso_only=int((row["import_path"],row["top_level"],row["kind"]) not in tokenized[key]))
                        (accepted if outcome else rejected).append(result)
    fields = list(accepted[0])
    for filename, data in (("parso_verified_single_line_imports.csv", accepted),
                           ("parso_rejected_import_artifacts.csv", rejected)):
        with (OUT / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerows(data)
    summary = dict(candidate_occurrences=len(accepted)+len(rejected), accepted_occurrences=len(accepted),
                   rejected_occurrences=len(rejected), accepted_parso_only_occurrences=sum(int(r["parso_only"]) for r in accepted),
                   accepted_parso_only_answers=len({(r["model"],r["method"],r["fold"],r["generation_id"])
                                                   for r in accepted if int(r["parso_only"])}),
                   rejected_import_name_top=Counter(r["import_path"] for r in rejected).most_common(15))
    (OUT / "parso_physical_line_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
