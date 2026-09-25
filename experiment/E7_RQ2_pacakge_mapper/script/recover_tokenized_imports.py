"""Recover Python import statements in malformed answers via tokenize + AST.

Python 3.10 standard library only; never executes generated code.  Tokenization
allows multiline imports and ignores import-looking strings/comments.  Accepted
statements are independently validated with ast.parse.  A tokenizer error is
retained as a quality flag, not interpreted as absence of imports.
"""
from __future__ import annotations

import ast
import csv
import io
import json
import sys
import tokenize
from collections import Counter, defaultdict

from build_inventory import OUT, STD, METHODS, MODELS, FOLDS, archived_code, rows, source_path


def parse_statement(tokens, first_line):
    snippet = tokenize.untokenize([(tok.type, tok.string) for tok in tokens]).strip()
    try:
        tree = ast.parse(snippet, mode="exec")
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
        return [], False
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            parsed = [(alias.name, alias.name.split(".", 1)[0], "absolute") for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            parsed = [("." * node.level + (node.module or ""), "", "relative_local")] if node.level else \
                [(node.module, node.module.split(".", 1)[0], "absolute")] if node.module else []
        else:
            parsed = []
        for path, top, kind in parsed:
            imports.append(dict(import_path=path, top_level=top,
                                kind="standard_library" if top in STD else kind,
                                line=first_line, source="tokenized_statement_ast"))
    return imports, True


def recover(code):
    imports = []
    candidates = 0
    rejected = 0
    token_error = ""
    try:
        stream = tokenize.generate_tokens(io.StringIO(code).readline)
        tokens = []
        in_import = False
        start_allowed = True
        depth = 0
        first_line = 0
        for tok in stream:
            typ, value = tok.type, tok.string
            if typ == tokenize.ENDMARKER:
                if in_import and tokens:
                    found, valid = parse_statement(tokens, first_line)
                    imports.extend(found); rejected += not valid
                break
            if in_import:
                if typ == tokenize.OP and value in "([{":
                    depth += 1
                elif typ == tokenize.OP and value in ")]}":
                    depth = max(depth - 1, 0)
                if (typ == tokenize.NEWLINE or (typ == tokenize.OP and value == ";" and depth == 0)):
                    found, valid = parse_statement(tokens, first_line)
                    imports.extend(found); rejected += not valid
                    in_import = False
                    tokens = []
                    start_allowed = True
                    continue
                tokens.append(tok)
                continue
            if typ in {tokenize.NL, tokenize.COMMENT, tokenize.ENCODING}:
                continue
            if typ in {tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}:
                start_allowed = True
                continue
            if typ == tokenize.OP and value in {";", ":"}:
                start_allowed = True
                continue
            if typ == tokenize.NAME and value in {"import", "from"} and start_allowed:
                candidates += 1
                in_import = True
                tokens = [tok]
                first_line = tok.start[0]
                depth = 0
                start_allowed = False
                continue
            start_allowed = False
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        token_error = f"{type(exc).__name__}: {exc}"[:200]
        if in_import and tokens:
            found, valid = parse_statement(tokens, first_line)
            imports.extend(found); rejected += not valid
    return imports, candidates, rejected, token_error


def main():
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"Expected Python 3.10, got {sys.version}")
    prior = {}
    for row in csv.DictReader((OUT / "generations.csv").open()):
        prior[(row["model"], row["method"], row["fold"], row["generation_id"])] = row
    ast_expected = defaultdict(set)
    for row in csv.DictReader((OUT / "ast_import_occurrences.csv").open()):
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        ast_expected[key].add((row["import_path"], row["top_level"], row["kind"]))
    occurrences, checks = [], []
    for model, hist_model in MODELS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                for row in rows(source_path(model, hist_model, method, fold)):
                    key = (model, method, fold, str(row["id"]))
                    code = archived_code(row["tasks"]["code"]["code_generation_raw"])
                    found, candidates, rejected, error = recover(code)
                    for import_row in found:
                        occurrences.append(dict(model=model, method=method, fold=fold, generation_id=str(row["id"]),
                                                prompt_id=str(row["original_id"]), **import_row))
                    current = {(item["import_path"], item["top_level"], item["kind"]) for item in found}
                    expected = ast_expected[key] if prior[key]["ast_status"] == "ast_ok" else None
                    checks.append(dict(model=model, method=method, fold=fold, generation_id=str(row["id"]),
                                       ast_status=prior[key]["ast_status"], token_error=error,
                                       import_candidates=candidates, rejected_import_statements=rejected,
                                       import_count=len(current),
                                       ast_set_equal="" if expected is None else int(current == expected),
                                       ast_missing="" if expected is None else json.dumps(sorted(expected-current)),
                                       ast_extra="" if expected is None else json.dumps(sorted(current-expected))))
    with (OUT / "tokenized_import_occurrences.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(occurrences[0]))
        writer.writeheader(); writer.writerows(occurrences)
    with (OUT / "tokenized_recovery_by_generation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
        writer.writeheader(); writer.writerows(checks)
    parsed = [r for r in checks if r["ast_status"] == "ast_ok"]
    failed = [r for r in checks if r["ast_status"] == "parse_failure"]
    summary = dict(n=len(checks), n_ast_ok=len(parsed), n_ast_failed=len(failed),
                   exact_ast_agreement=sum(r["ast_set_equal"] == 1 for r in parsed),
                   missing_ast_import_answers=sum(r["ast_missing"] != "[]" for r in parsed),
                   extra_ast_import_answers=sum(r["ast_extra"] != "[]" for r in parsed),
                   recovered_failed_answers=sum(r["import_count"] > 0 for r in failed),
                   failed_answers_no_recovery=sum(r["import_count"] == 0 for r in failed),
                   recovered_distinct_imports_failed=sum(int(r["import_count"]) for r in failed),
                   tokenizer_error_answers=sum(bool(r["token_error"]) for r in checks),
                   rejected_import_statements=sum(int(r["rejected_import_statements"]) for r in checks),
                   status_by_method={method:dict(n_failed=sum(r["ast_status"] == "parse_failure" and r["method"] == method for r in checks),
                                                 failed_recovered=sum(r["ast_status"] == "parse_failure" and r["method"] == method and r["import_count"] > 0 for r in checks))
                                     for method in METHODS})
    (OUT / "tokenized_recovery_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
