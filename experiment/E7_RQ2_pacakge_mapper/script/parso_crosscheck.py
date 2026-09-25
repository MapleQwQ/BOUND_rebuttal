"""Cross-check tokenizer recovery on AST-invalid code using Parso error recovery.

Parso is a second parser, not mapping ground truth. Only import nodes whose text
also parses as a Python 3.10 AST import statement are accepted. It never runs
generated code. Install parso==0.8.7 in an isolated environment.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import random
import signal
import sys
from collections import Counter, defaultdict

import parso

from build_inventory import OUT, STD, METHODS, MODELS, FOLDS, archived_code, rows, source_path

GRAMMAR = parso.load_grammar(version="3.10")
SAMPLE_SEED = 20260925
EMPTY_SAMPLE_PER_METHOD = 40


def on_timeout(signum, frame):
    raise TimeoutError("Parso per-answer time limit")


def parse_import_nodes(code):
    module = GRAMMAR.parse(code, error_recovery=True)
    source_lines = code.splitlines()
    stack = [module]
    found = []
    rejected = 0
    boundary_rejected = 0
    while stack:
        node = stack.pop()
        stack.extend(reversed(getattr(node, "children", ())))
        if node.type not in {"import_name", "import_from"}:
            continue
        line_number, column = node.start_pos
        line_prefix = source_lines[line_number - 1][:column].strip() if 0 < line_number <= len(source_lines) else ""
        if line_prefix and not line_prefix.endswith((";", ":")):
            boundary_rejected += 1
            continue
        try:
            statement = ast.parse(node.get_code().strip(), mode="exec")
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            rejected += 1
            continue
        for item in statement.body:
            if isinstance(item, ast.Import):
                parsed = [(alias.name, alias.name.split(".", 1)[0], "absolute") for alias in item.names]
            elif isinstance(item, ast.ImportFrom):
                parsed = [("." * item.level + (item.module or ""), "", "relative_local")] if item.level else \
                    [(item.module, item.module.split(".", 1)[0], "absolute")] if item.module else []
            else:
                parsed = []
            for path, top, kind in parsed:
                found.append(dict(import_path=path, top_level=top,
                                  kind="standard_library" if top in STD else kind,
                                  line=node.start_pos[0], source="parso_node_ast"))
    return found, rejected, boundary_rejected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-failed", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=0.1)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 10):
        raise SystemExit("Use Python 3.10 and parso==0.8.7")
    generation_info = {(r["model"], r["method"], r["fold"], r["generation_id"]): r
                       for r in csv.DictReader((OUT / "generations.csv").open())}
    tokenized = defaultdict(set)
    for row in csv.DictReader((OUT / "tokenized_import_occurrences.csv").open()):
        key = (row["model"], row["method"], row["fold"], row["generation_id"])
        tokenized[key].add((row["import_path"], row["top_level"], row["kind"]))
    missing_archived = set()
    empty_pool = defaultdict(list)
    for key, info in generation_info.items():
        if info["ast_status"] != "parse_failure":
            continue
        old = set(json.loads(info["mapper_input"]))
        extracted = {top for _, top, _ in tokenized[key]}
        if old - extracted:
            missing_archived.add(key)
        elif not old and not extracted:
            empty_pool[info["method"]].append(key)
    rng = random.Random(SAMPLE_SEED)
    sampled_empty = {key for method, keys in empty_pool.items()
                     for key in rng.sample(keys, min(EMPTY_SAMPLE_PER_METHOD, len(keys)))}
    selected = ({key for key, info in generation_info.items() if info["ast_status"] == "parse_failure"}
                if args.all_failed else missing_archived | sampled_empty)
    signal.signal(signal.SIGALRM, on_timeout)
    recovered, checks = [], []
    processed = 0
    for model, hist_model in MODELS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                for row in rows(source_path(model, hist_model, method, fold)):
                    key = (model, method, fold, str(row["id"]))
                    if key not in selected:
                        continue
                    processed += 1
                    if processed % 500 == 0:
                        print(f"processed={processed}/{len(selected)} {model}/{method}/{fold}", flush=True)
                    code = archived_code(row["tasks"]["code"]["code_generation_raw"])
                    try:
                        signal.setitimer(signal.ITIMER_REAL, args.timeout_seconds)
                        found, rejected, boundary_rejected = parse_import_nodes(code)
                        error = ""
                    except (ValueError, TypeError, MemoryError, RecursionError, TimeoutError) as exc:
                        found, rejected, boundary_rejected, error = [], 0, 0, f"{type(exc).__name__}: {exc}"[:200]
                    finally:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                    current = {(item["import_path"], item["top_level"], item["kind"]) for item in found}
                    extra = current - tokenized[key]
                    missing = tokenized[key] - current
                    for item in found:
                        recovered.append(dict(model=model, method=method, fold=fold, generation_id=str(row["id"]),
                                              prompt_id=str(row["original_id"]), **item))
                    checks.append(dict(model=model, method=method, fold=fold, generation_id=str(row["id"]),
                                       parso_count=len(current), tokenizer_count=len(tokenized[key]),
                                       extra_vs_tokenizer=json.dumps(sorted(extra)),
                                       missing_vs_tokenizer=json.dumps(sorted(missing)),
                                       rejected_import_nodes=rejected, boundary_rejected_nodes=boundary_rejected,
                                       parser_error=error))
    with (OUT / "parso_import_occurrences_failed.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recovered[0]))
        writer.writeheader(); writer.writerows(recovered)
    with (OUT / "parso_crosscheck_by_generation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
        writer.writeheader(); writer.writerows(checks)
    summary = dict(n_failed_total=sum(r["ast_status"]=="parse_failure" for r in generation_info.values()),
                   n_selected=len(checks), archived_discrepancy_cases=len(missing_archived),
                   sampled_empty_cases=len(sampled_empty), empty_sample_seed=SAMPLE_SEED,
                   all_failed=args.all_failed, per_answer_timeout_seconds=args.timeout_seconds,
                   parso_has_import=sum(r["parso_count"]>0 for r in checks),
                   tokenizer_has_import=sum(r["tokenizer_count"]>0 for r in checks),
                   parso_extra_answers=sum(r["extra_vs_tokenizer"]!="[]" for r in checks),
                   tokenizer_extra_answers=sum(r["missing_vs_tokenizer"]!="[]" for r in checks),
                   parso_only_import_slots=sum(len(json.loads(r["extra_vs_tokenizer"])) for r in checks),
                   parser_errors=sum(bool(r["parser_error"]) for r in checks),
                   rejected_import_nodes=sum(r["rejected_import_nodes"] for r in checks),
                   boundary_rejected_nodes=sum(r["boundary_rejected_nodes"] for r in checks))
    (OUT / "parso_crosscheck_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
