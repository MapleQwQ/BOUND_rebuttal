"""Audit retained RQ2 code generations without executing generated code.

Run with the project's Python 3.10 interpreter from the repository root.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / "results"
SNAP = ROOT / "BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization"
HIST = ROOT / "knowledgeEdit/results/rq2_cross_task_20260611"
MODELS = (("deepseekcoder", "deepseekcoder"), ("qwen3", "qwen3-release"), ("llama3.1", "llama3.1-release"))
FOLDS = "ABCD"
N_PROMPTS = 100
N_REPEATS = 5
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20260924
CODE_BLOCK_RE = re.compile(r"```([A-Za-z0-9_-]*)\s*(.*?)```", re.DOTALL | re.IGNORECASE)
ANSWER_RE = re.compile(r"\[ANSWER\](.*?)\[/ANSWER\]", re.DOTALL | re.IGNORECASE)
OPEN_FENCE_RE = re.compile(r"(?m)^[ \t]*```([A-Za-z0-9_-]*)[ \t]*(?:\r?\n|$)")
CLOSE_FENCE_RE = re.compile(r"(?m)^[ \t]*```[ \t]*(?:\r?\n|$)")
CODE_LINE_RE = re.compile(r"^\s*(?:import\s|from\s|def\s|class\s|async\s|if\s|for\s|while\s|with\s|try\s*:|except\s|finally\s*:|return\b|raise\b|@|#|[A-Za-z_][\w.]*\s*=|print\s*\()")
STANDARD = set(sys.stdlib_module_names) | set(sys.builtin_module_names)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def archived_code_block(raw: str) -> str:
    """Reproduce the submitted RQ2 extractor for a sensitivity check."""
    match = ANSWER_RE.search(raw)
    answer = match.group(1).strip() if match else raw.strip()
    blocks = [block.strip() for language, block in CODE_BLOCK_RE.findall(answer)
              if language.strip().lower() in {"", "python", "py"} and block.strip()]
    return "\n\n".join(blocks) if blocks else answer.strip()


def extracted_code(raw: str) -> tuple[str, str]:
    """Take Python fences, including an unclosed final fence, from the answer."""
    opened = re.search(r"\[ANSWER\]", raw, flags=re.IGNORECASE)
    answer = raw[opened.end():] if opened else raw
    closed = re.search(r"\[/ANSWER\]", answer, flags=re.IGNORECASE)
    if closed:
        answer = answer[:closed.start()]
    answer = answer.strip()
    blocks = []
    unclosed = False
    pos = 0
    while True:
        opening = OPEN_FENCE_RE.search(answer, pos)
        if not opening:
            break
        closing = CLOSE_FENCE_RE.search(answer, opening.end())
        block = answer[opening.end():closing.start() if closing else len(answer)].strip()
        if opening.group(1).lower() in {"", "python", "py"} and block:
            blocks.append(block)
            if not closing:
                unclosed = True
        if not closing:
            break
        pos = closing.end()
    if blocks:
        return "\n\n".join(blocks), "unclosed_python_fence" if unclosed else "python_fence"
    return answer, "answer_fallback"


def examine(code: str, route: str) -> dict:
    stripped = code.strip()
    if stripped.lower() in {"", "none", "no code", "n/a", "not applicable"}:
        return dict(status="no_code", parse_ok=False, compile_ok=False, third_party_import=False,
                    import_modules=[], error_type="", error_message="")
    if route == "answer_fallback" and not any(CODE_LINE_RE.match(line) for line in code.splitlines()):
        return dict(status="no_code", parse_ok=False, compile_ok=False, third_party_import=False,
                    import_modules=[], error_type="", error_message="")
    try:
        tree = ast.parse(code, filename="<generated>", mode="exec")
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
        return dict(status="parse_failure", parse_ok=False, compile_ok=False, third_party_import=False,
                    import_modules=[], error_type=type(exc).__name__, error_message=str(exc))
    # A comment-only answer or a bare value/name is not a Python program for this task.
    if not tree.body or (len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr)
                         and isinstance(tree.body[0].value, (ast.Constant, ast.Name))):
        return dict(status="no_code", parse_ok=False, compile_ok=False, third_party_import=False,
                    import_modules=[], error_type="", error_message="")
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module.split(".", 1)[0])
    third_party = any(name not in STANDARD and name != "__future__" for name in imports)
    try:
        compile(code, "<generated>", "exec", dont_inherit=True)
    except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError) as exc:
        return dict(status="compile_failure", parse_ok=True, compile_ok=False, third_party_import=third_party,
                    import_modules=sorted(imports), error_type=type(exc).__name__, error_message=str(exc))
    return dict(status="syntax_valid", parse_ok=True, compile_ok=True, third_party_import=third_party,
                import_modules=sorted(imports), error_type="", error_message="")


def percentile(xs: list[float], p: float) -> float:
    ys = sorted(xs)
    pos = (len(ys) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (pos - lo)


def rate(rows: list[dict], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows)


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    counts = Counter(row["status"] for row in rows)
    return {
        "n": n,
        "syntax_valid_rate": rate(rows, "parse_ok"),
        "no_code_rate": counts["no_code"] / n,
        "parse_failure_rate": counts["parse_failure"] / n,
        "compile_failure_rate": counts["compile_failure"] / n,
        "compile_valid_rate": rate(rows, "compile_ok"),
        "syntax_valid_third_party_import_rate": sum(row["parse_ok"] and row["third_party_import"] for row in rows) / n,
        "status_counts": dict(counts),
        "extraction_route_counts": dict(Counter(row["extraction_route"] for row in rows)),
    }


def main() -> None:
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"Expected Python 3.10, got {sys.version}")
    import random
    OUT.mkdir(exist_ok=True)
    records = []
    inventory = []
    base_fold_copy_inputs = []
    base_fold_copy_differences = []
    selected_base_folds = {}
    base_fold_syntax_rates = {}
    for model, historical_model in MODELS:
        base_files = [HIST / historical_model / "Base" / f"fold_{fold}" / "test100_case_repeat5/rq2_details.jsonl" for fold in FOLDS]
        base_copies = {fold: read_jsonl(path) for fold, path in zip(FOLDS, base_files)}
        reference_by_id = {str(row["id"]): row for row in base_copies["A"]}
        if len(base_copies["A"]) != N_PROMPTS * N_REPEATS or len(reference_by_id) != len(base_copies["A"]):
            raise ValueError(f"Duplicate Base IDs for {model}")
        base_fold_syntax_rates[model] = {}
        for fold, path in zip(FOLDS, base_files):
            copy = base_copies[fold]
            copy_by_id = {str(row["id"]): row for row in copy}
            if len(copy) != N_PROMPTS * N_REPEATS or len(copy_by_id) != len(copy) or set(copy_by_id) != set(reference_by_id):
                raise ValueError(f"Base fold copy ID mismatch: {path}")
            if any(row["question"] != reference_by_id[rid]["question"] for rid, row in copy_by_id.items()):
                raise ValueError(f"Base fold copy question mismatch: {path}")
            valid = 0
            for row in copy:
                code, route = extracted_code(row["tasks"]["code"]["code_generation_raw"])
                valid += examine(code, route)["parse_ok"]
            base_fold_syntax_rates[model][fold] = valid / len(copy)
            base_fold_copy_inputs.append(dict(model=model, fold=fold, path=str(path.relative_to(ROOT)), sha256=sha256(path), n=len(copy)))
            if fold != "A":
                for rid, row in copy_by_id.items():
                    reference = reference_by_id[rid]
                    c, rc = row["tasks"]["code"], reference["tasks"]["code"]
                    if c["code_generation_raw"] != rc["code_generation_raw"] or c["code_block"] != rc["code_block"]:
                        base_fold_copy_differences.append(dict(model=model, fold=fold, generation_id=rid,
                            raw_differs=c["code_generation_raw"] != rc["code_generation_raw"],
                            archived_code_block_differs=c["code_block"] != rc["code_block"]))
        selected_fold = min(FOLDS, key=lambda fold: base_fold_syntax_rates[model][fold])
        selected_base_folds[model] = selected_fold
        base_path = base_files[FOLDS.index(selected_fold)]
        base = base_copies[selected_fold]
        base_by_id = {str(row["id"]): row for row in base}
        inventory.append(dict(model=model, method="Base", path=str(base_path.relative_to(ROOT)), sha256=sha256(base_path), n=len(base)))
        conditions = [("Base", "", base, base_path)]
        for fold in FOLDS:
            path = SNAP / model / "BOUND" / f"fold_{fold}" / "bound/cross_task_case_grouped.jsonl"
            grouped = read_jsonl(path)
            if len(grouped) != N_PROMPTS or any(len(group["repeats"]) != N_REPEATS for group in grouped):
                raise ValueError(f"Wrong BOUND shape: {path}")
            flat = [repeat for group in grouped for repeat in group["repeats"]]
            ids = {str(row["id"]) for row in flat}
            if len(ids) != len(flat) or ids != set(base_by_id):
                raise ValueError(f"BOUND/Base ID mismatch: {path}")
            if any(row["question"] != base_by_id[str(row["id"])]["question"] for row in flat):
                raise ValueError(f"BOUND/Base question mismatch: {path}")
            conditions.append(("BOUND", fold, flat, path))
            inventory.append(dict(model=model, method="BOUND", fold=fold, path=str(path.relative_to(ROOT)), sha256=sha256(path), n=len(flat)))
        for method, fold, rows, path in conditions:
            for row in rows:
                code_data = row["tasks"]["code"]
                raw = code_data["code_generation_raw"]
                code, route = extracted_code(raw)
                saved_block_matches_original_extractor = archived_code_block(raw) == code_data["code_block"]
                if method == "BOUND" and not saved_block_matches_original_extractor:
                    raise ValueError(f"Cannot reproduce archived code_block: {path} id={row['id']}")
                result = examine(code, route)
                archived_route = "python_fence" if CODE_BLOCK_RE.search(raw) else "answer_fallback"
                archived_result = examine(code_data["code_block"], archived_route)
                records.append({
                    "model": model, "method": method, "fold": fold, "generation_id": str(row["id"]),
                    "prompt_id": str(row["original_id"]), "question_sha256": hashlib.sha256(row["question"].encode()).hexdigest(),
                    "source_path": str(path.relative_to(ROOT)), "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    "code_chars": len(code), "extraction_route": route,
                    "differs_from_archived_code_block": code != code_data["code_block"],
                    "saved_block_matches_original_extractor": saved_block_matches_original_extractor,
                    "archived_parse_ok": archived_result["parse_ok"],
                    "archived_status": archived_result["status"],
                    **result,
                })
    if len(records) != 7_500:
        raise ValueError(f"Expected 7,500 records, found {len(records)}")
    with (OUT / "per_generation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), extrasaction="raise")
        writer.writeheader()
        for row in records:
            writer.writerow({**row, "import_modules": json.dumps(row["import_modules"], ensure_ascii=False)})
    (OUT / "input_manifest.json").write_text(json.dumps({"python": sys.version, "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "base_selection_rule": "post hoc lowest syntax_valid_rate among archived A-D per model; earliest fold breaks ties",
        "selected_base_folds": selected_base_folds, "base_fold_syntax_rates": base_fold_syntax_rates,
        "inputs": inventory,
        "base_fold_copy_inputs": base_fold_copy_inputs,
        "base_fold_copy_differences": base_fold_copy_differences}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    by_condition = {}
    by_prompt = {}
    for model, _ in MODELS:
        by_condition[model] = {}
        for method, fold in [("Base", "")] + [("BOUND", f) for f in FOLDS]:
            selected = [row for row in records if row["model"] == model and row["method"] == method and row["fold"] == fold]
            if len(selected) != 500:
                raise ValueError((model, method, fold, len(selected)))
            by_condition[model][method if method == "Base" else f"BOUND_{fold}"] = summarize(selected)
            by_prompt[(model, method, fold)] = {pid: [row for row in selected if row["prompt_id"] == pid] for pid in {r["prompt_id"] for r in selected}}
            if len(by_prompt[(model, method, fold)]) != N_PROMPTS or any(len(v) != N_REPEATS for v in by_prompt[(model, method, fold)].values()):
                raise ValueError(f"Prompt repeat mismatch: {model}/{method}/{fold}")

    metrics = ("syntax_valid_rate", "no_code_rate", "parse_failure_rate", "compile_failure_rate",
               "compile_valid_rate", "syntax_valid_third_party_import_rate")
    model_summaries = {}
    for model, _ in MODELS:
        base = by_condition[model]["Base"]
        bound = {metric: sum(by_condition[model][f"BOUND_{f}"][metric] for f in FOLDS) / 4 for metric in metrics}
        model_summaries[model] = {"Base": base, "BOUND_macro": bound,
                                  "BOUND_minus_Base": {metric: bound[metric] - base[metric] for metric in metrics}}
    pooled = {method: {metric: sum(model_summaries[m][method][metric] for m, _ in MODELS) / 3 for metric in metrics}
              for method in ("Base", "BOUND_macro", "BOUND_minus_Base")}
    archived_sensitivity = {}
    for model, _ in MODELS:
        archived_sensitivity[model] = {}
        for method, fold in [("Base", "")] + [("BOUND", f) for f in FOLDS]:
            selected = [row for row in records if row["model"] == model and row["method"] == method and row["fold"] == fold]
            archived_sensitivity[model][method if method == "Base" else f"BOUND_{fold}"] = {
                "archived_parse_rate": sum(row["archived_parse_ok"] for row in selected) / len(selected),
                "changed_extraction_count": sum(row["differs_from_archived_code_block"] for row in selected),
            }

    # Resample prompt IDs once within each model; all trials and folds for a prompt stay together.
    rng = random.Random(BOOTSTRAP_SEED)
    draws = {model: {metric: [] for metric in metrics} for model, _ in MODELS}
    draws["three_model_macro"] = {metric: [] for metric in metrics}
    prompts = {model: sorted(by_prompt[(model, "Base", "")]) for model, _ in MODELS}
    # Prompt-level means are sufficient because each prompt has exactly five generations.
    prompt_rates = {}
    for model, _ in MODELS:
        for method, fold in [("Base", "")] + [("BOUND", f) for f in FOLDS]:
            prompt_rates[(model, method, fold)] = {}
            for pid, rows in by_prompt[(model, method, fold)].items():
                one = summarize(rows)
                prompt_rates[(model, method, fold)][pid] = {metric: one[metric] for metric in metrics}
    for _ in range(BOOTSTRAP_REPS):
        macro_draw = {metric: 0.0 for metric in metrics}
        for model, _ in MODELS:
            sampled = rng.choices(prompts[model], k=N_PROMPTS)
            for metric in metrics:
                base_value = sum(prompt_rates[(model, "Base", "")][pid][metric] for pid in sampled) / N_PROMPTS
                bound_value = sum(sum(prompt_rates[(model, "BOUND", fold)][pid][metric] for pid in sampled) / N_PROMPTS for fold in FOLDS) / 4
                diff = bound_value - base_value
                draws[model][metric].append(diff)
                macro_draw[metric] += diff / 3
        for metric in metrics:
            draws["three_model_macro"][metric].append(macro_draw[metric])
    intervals = {model: {metric: [percentile(values, .025), percentile(values, .975)] for metric, values in metrics_map.items()}
                 for model, metrics_map in draws.items()}

    result = {"definitions": {"syntax_valid_rate": "AST parse succeeds, excluding no_code; denominator all generations",
        "no_code_rate": "empty/None/no-code answer, unfenced response without Python code lines, comment-only, or single bare Name/Constant AST; denominator all generations",
        "parse_failure_rate": "code candidate fails ast.parse; denominator all generations",
        "compile_failure_rate": "AST-valid code fails compile(..., exec); denominator all generations",
        "compile_valid_rate": "non-no-code and compile succeeds; denominator all generations",
        "syntax_valid_third_party_import_rate": "AST-valid code imports at least one top-level module absent from Python 3.10 stdlib/builtins; denominator all generations"},
        "by_condition": by_condition, "by_model": model_summaries, "three_model_macro": pooled,
        "archived_extraction_sensitivity": archived_sensitivity,
        "bound_minus_base_95pct_prompt_bootstrap_ci": intervals}
    (OUT / "syntax_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"by_model": model_summaries, "three_model_macro": pooled,
                      "syntax_valid_ci": {m: v["syntax_valid_rate"] for m, v in intervals.items()}}, indent=2))


if __name__ == "__main__":
    main()
