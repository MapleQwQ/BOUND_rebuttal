"""Conservatively recover one-line import statements from AST-invalid answers.

Recovery is flagged and cannot establish absence of other imports.
"""
from __future__ import annotations

import ast
import csv
import json
import sys
from collections import Counter

from build_inventory import OUT, STD, METHODS, MODELS, FOLDS, archived_code, rows, source_path


def main():
    if sys.version_info[:2] != (3, 10):
        raise SystemExit("Use Python 3.10")
    failed = {(r["model"], r["method"], r["fold"], r["generation_id"])
              for r in csv.DictReader((OUT / "generations.csv").open()) if r["ast_status"] == "parse_failure"}
    recovered = []
    per_generation = Counter()
    for model, hist_model in MODELS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                for row in rows(source_path(model, hist_model, method, fold)):
                    gid = str(row["id"])
                    if (model, method, fold, gid) not in failed:
                        continue
                    code = archived_code(row["tasks"]["code"]["code_generation_raw"])
                    for lineno, line in enumerate(code.splitlines(), 1):
                        stripped = line.strip()
                        if not (stripped.startswith("import ") or stripped.startswith("from ")):
                            continue
                        try:
                            tree = ast.parse(stripped, mode="exec")
                        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
                            continue
                        for node in tree.body:
                            if isinstance(node, ast.Import):
                                items = [(alias.name, alias.name.split(".", 1)[0], "absolute") for alias in node.names]
                            elif isinstance(node, ast.ImportFrom):
                                items = [("." * node.level + (node.module or ""), "", "relative_local")] if node.level else \
                                    [(node.module, node.module.split(".", 1)[0], "absolute")] if node.module else []
                            else:
                                items = []
                            for path, top, kind in items:
                                rec = dict(model=model, method=method, fold=fold, generation_id=gid,
                                           prompt_id=str(row["original_id"]), import_path=path,
                                           top_level=top, kind="standard_library" if top in STD else kind,
                                           line=lineno, extraction="partial_line_ast")
                                recovered.append(rec)
                                per_generation[(model, method, fold, gid)] += 1
    with (OUT / "partial_ast_import_occurrences.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recovered[0]))
        writer.writeheader()
        writer.writerows(recovered)
    report = dict(failed_generations=len(failed), generations_with_recovered_imports=len(per_generation),
                  recovered_import_occurrences=len(recovered),
                  recovered_kinds=dict(Counter(r["kind"] for r in recovered)),
                  limitation="Line-wise AST can miss multiline statements; zero recovered imports does not prove no imports.")
    (OUT / "partial_ast_recovery_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
