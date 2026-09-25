"""Inventory every unique retained RQ2 code generation and AST import occurrence.

Run from any directory using Python 3.10: python build_inventory.py
No generated code is executed or imported.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / "results"
SNAP = ROOT / "BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization"
HIST = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611"
MODELS = (("deepseekcoder", "deepseekcoder"), ("qwen3", "qwen3-release"), ("llama3.1", "llama3.1-release"))
METHODS = ("Base", "BOUND", "ROME", "MEMIT", "DINM", "Full-FT")
FOLDS = "ABCD"
ANSWER_RE = re.compile(r"\[ANSWER\](.*?)\[/ANSWER\]", re.I | re.S)
BLOCK_RE = re.compile(r"```([A-Za-z0-9_-]*)\s*(.*?)```", re.I | re.S)
STD = set(sys.stdlib_module_names) | set(sys.builtin_module_names) | {"__future__"}


def rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                datum = json.loads(line)
                yield from datum.get("repeats", [datum])


def source_path(model: str, hist_model: str, method: str, fold: str) -> Path:
    if method == "BOUND":
        return SNAP / model / method / f"fold_{fold}" / "bound/cross_task_case_grouped.jsonl"
    return HIST / hist_model / method / f"fold_{fold}" / "test100_case_repeat5/rq2_details.jsonl"


def archived_code(raw: str) -> str:
    match = ANSWER_RE.search(raw)
    answer = match.group(1).strip() if match else raw.strip()
    blocks = [body.strip() for language, body in BLOCK_RE.findall(answer)
              if language.strip().lower() in {"", "python", "py"} and body.strip()]
    return "\n\n".join(blocks) if blocks else answer


def parse_imports(code: str):
    """AST first; failed parse is a visible status, never a zero-import success."""
    try:
        tree = ast.parse(code, filename="<generated>", mode="exec")
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
        return "parse_failure", type(exc).__name__, []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, alias.name.split(".", 1)[0], "absolute", node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.append(("." * node.level + (node.module or ""), "", "relative_local", node.lineno))
            elif node.module:
                found.append((node.module, node.module.split(".", 1)[0], "absolute", node.lineno))
    return "ast_ok", "", found


def dump_csv(path: Path, data: list[dict], fields: list[str]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(data)


def main():
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"Expected Python 3.10; got {sys.version}")
    OUT.mkdir(exist_ok=True)
    generations, occurrences, manifest = [], [], []
    for model, hist_model in MODELS:
        for method in METHODS:
            for fold in ("A" if method == "Base" else FOLDS):
                path = source_path(model, hist_model, method, fold)
                count = 0
                for row in rows(path):
                    count += 1
                    code_data = row["tasks"]["code"]
                    code = archived_code(code_data["code_generation_raw"])
                    status, error, imports = parse_imports(code)
                    gid = str(row["id"])
                    mapper_input = code_data.get("import_modules") or []
                    mapper_output = code_data.get("packages") or []
                    generation = dict(model=model, method=method, fold=fold, generation_id=gid,
                                      prompt_id=str(row["original_id"]), ast_status=status, ast_error=error,
                                      code_sha256=hashlib.sha256(code.encode()).hexdigest(),
                                      archived_code_block_match=code == code_data.get("code_block", ""),
                                      ast_import_count=len(imports),
                                      mapper_input=json.dumps(mapper_input, ensure_ascii=False),
                                      mapper_output=json.dumps(mapper_output, ensure_ascii=False),
                                      original_valid=json.dumps(code_data.get("valid") or [], ensure_ascii=False),
                                      original_hallucinated=json.dumps(code_data.get("hallucinated") or [], ensure_ascii=False))
                    generations.append(generation)
                    for path_name, top, kind, line in imports:
                        occurrences.append(dict(model=model, method=method, fold=fold, generation_id=gid,
                                                prompt_id=str(row["original_id"]), import_path=path_name,
                                                top_level=top, kind=("standard_library" if top in STD else kind),
                                                line=line))
                if count != 500:
                    raise ValueError(f"Expected 500 unique answers: {path}: {count}")
                manifest.append(dict(model=model, method=method, fold=fold, input_path=str(path.relative_to(ROOT)),
                                     sha256=hashlib.sha256(path.read_bytes()).hexdigest(), n=count))
    if len(generations) != 31500:
        raise ValueError(f"Expected 31500 generations; got {len(generations)}")
    dump_csv(OUT / "generations.csv", generations, list(generations[0]))
    dump_csv(OUT / "ast_import_occurrences.csv", occurrences, list(occurrences[0]))
    by_top = defaultdict(lambda: dict(occurrences=0, answers=set(), paths=Counter(), models=Counter()))
    for occurrence in occurrences:
        if occurrence["kind"] != "absolute":
            continue
        top = occurrence["top_level"]
        item = by_top[top]
        item["occurrences"] += 1
        item["answers"].add((occurrence["model"], occurrence["method"], occurrence["fold"], occurrence["generation_id"]))
        item["paths"][occurrence["import_path"]] += 1
        item["models"][occurrence["model"]] += 1
    inventory = [dict(top_level=top, ast_occurrences=data["occurrences"], answer_occurrences=len(data["answers"]),
                      distinct_paths=len(data["paths"]), top_paths=json.dumps(data["paths"].most_common(15), ensure_ascii=False),
                      model_counts=json.dumps(data["models"], ensure_ascii=False))
                 for top, data in by_top.items()]
    inventory.sort(key=lambda item: (-item["answer_occurrences"], item["top_level"].lower()))
    dump_csv(OUT / "unique_import_inventory.csv", inventory, list(inventory[0]))
    summary = dict(python=sys.version, n_generations=len(generations), n_ast_import_occurrences=len(occurrences),
                   n_unique_ast_top_level=len(inventory), ast_status=dict(Counter(x["ast_status"] for x in generations)),
                   import_kind=dict(Counter(x["kind"] for x in occurrences)),
                   saved_code_block_mismatch=sum(not x["archived_code_block_match"] for x in generations),
                   mapper_input_nonempty=sum(x["mapper_input"] != "[]" for x in generations),
                   mapper_output_nonempty=sum(x["mapper_output"] != "[]" for x in generations),
                   sources=manifest)
    (OUT / "inventory_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "sources"}, indent=2))


if __name__ == "__main__":
    main()
