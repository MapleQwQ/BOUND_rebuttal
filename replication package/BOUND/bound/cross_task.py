"""Run and summarize cross-task code/install package hallucination experiments."""

from __future__ import annotations

import argparse
import ast
import gc
import json
import re
import sys
from pathlib import Path
from typing import Any

import torch
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bound.bound import (  # noqa: E402
    classify_packages_by_pypi,
    gen_chat,
    infer_model_cutoff,
    load_model,
    read_jsonl,
    set_gpu,
    write_json,
)


CROSS_TASKS = ("code", "install")
DEFAULT_NUM_REPEATS = 5
METHOD_NAME = "BOUND"

# Cross-task prompts

CODE_SYSTEM_MESSAGE = """You are a coding assistant whose task is to generate Python code for the coding task. Provide only the Python code. Do not include any additional text or formatting. If no Python code can answer the task, simply reply "None".
Provide your answer in [ANSWER] and [/ANSWER] tags, following the examples.
Example:
[TASK]
Your task is to generate a python script to achieve bubble sort.
[/TASK]
[ANSWER]
```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        # Track if a swap was made
        swapped = False
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                # Swap the elements
                arr[j], arr[j+1] = arr[j+1], arr[j]
                swapped = True
        # If no swaps were made, the list is already sorted
        if not swapped:
            break
    return arr
```
[/ANSWER]"""

TASK_PACKAGE_CHECK_SYSTEM = """You are a coding assistant that determines Python packages necessary for a programming task.
You will be given a Python programming task that may require third-party packages.
Please only return the installation command to install these python packages via PIP, no additional text or formatting.
If there is no python package that needs to be installed, please return "None", otherwise the response must begin with pip.
Provide your answer in [ANSWER] and [/ANSWER] tags, following the examples.
Example:
[TASK]
Generate Python code that reads a CSV file, loads it into a dataframe, and plots a line chart.
[/TASK]
[ANSWER]
pip install pandas matplotlib
[/ANSWER]

[TASK]
Generate Python code that parses a JSON string and counts values with the standard library.
[/TASK]
[ANSWER]
None
[/ANSWER]"""

IMPORT_PACKAGE_SYSTEM = """You are a coding assistant that maps Python import module names to their PyPI package names.
You will be given top-level Python import module names extracted from generated code.
Return only package names, comma separated, inside [ANSWER] and [/ANSWER] tags, no additional text or formatting.
If no third-party Python package is needed, return only "None" inside the tags.
Provide your answer in [ANSWER] and [/ANSWER] tags, following the examples.
Example:
[IMPORTS]
pandas, matplotlib, requests
[/IMPORTS]
[ANSWER]
pandas, matplotlib, requests
[/ANSWER]

[IMPORTS]
PIL, cv2, sklearn, jwt, bs4
[/IMPORTS]
[ANSWER]
pillow, opencv-python, scikit-learn, pyjwt, beautifulsoup4
[/ANSWER]

[IMPORTS]
os, sys, json, pathlib
[/IMPORTS]
[ANSWER]
None
[/ANSWER]"""

CODE_BLOCK_RE = re.compile(r"```([A-Za-z0-9_-]*)\s*(.*?)```", re.DOTALL | re.IGNORECASE)
try:
    STD_LIBRARY_MODULES = set(sys.stdlib_module_names)
except AttributeError:
    STD_LIBRARY_MODULES = set()
STD_LIBRARY_MODULES |= set(sys.builtin_module_names)

PIP_SKIP_TOKENS = {
    "--upgrade",
    "-u",
    "--user",
    "--no-cache-dir",
    "--pre",
    "-q",
    "-qq",
    "-r",
    "--requirement",
}


def release_cuda_model(model: Any | None, tokenizer: Any | None = None) -> None:
    if model is not None:
        try:
            model.to("cpu")
        except Exception:
            pass
    del model
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        try:
            torch.cuda.synchronize()
        except Exception:
            pass
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass


def parse_tasks(tasks_arg: str) -> list[str]:
    tasks = [task.strip() for task in tasks_arg.split(",") if task.strip()]
    unknown = sorted(set(tasks) - set(CROSS_TASKS))
    if unknown:
        raise ValueError(f"unknown cross-task(s): {', '.join(unknown)}")
    return tasks or list(CROSS_TASKS)


def read_prompts(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    rows = []
    for i, row in enumerate(read_jsonl(path)):
        question = row.get("question") or row.get("prompt") or row.get("target_prompt") or row.get("source")
        if not question and "messages" in row:
            question = " ".join(str(m.get("content", "")) for m in row["messages"] if isinstance(m, dict))
        if not question:
            continue
        prompt_row = dict(row)
        prompt_row["id"] = row.get("id", i)
        prompt_row["question"] = str(question)
        rows.append(prompt_row)
        if limit and len(rows) >= limit:
            break
    return rows


def make_repeat_row(
    row: dict[str, Any],
    case_index: int,
    repeat_id: int,
    n_repeats: int,
    tasks: dict[str, Any],
) -> dict[str, Any]:
    original_id = row.get("original_id", row.get("id", case_index))
    prompt_case_index = row.get("cross_task_case_index", case_index)
    return {
        "id": f"{original_id}__repeat_{repeat_id}",
        "original_id": original_id,
        "question": row["question"],
        "cross_task_source": row.get("cross_task_source", {}),
        "cross_task_repeat": {
            "case_index": prompt_case_index,
            "repeat_id": repeat_id,
            "n_repeats": n_repeats,
            "repeat_order": "case-major",
        },
        "tasks": tasks,
    }


def answer_region(text: str) -> str:
    if not isinstance(text, str):
        return ""
    match = re.search(r"\[ANSWER\](.*?)\[/ANSWER\]", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def code_block(text: str) -> str:
    text = answer_region(text)
    blocks = []
    for language, block in CODE_BLOCK_RE.findall(text):
        language = language.strip().lower()
        if language in {"", "python", "py"} and block.strip():
            blocks.append(block.strip())
    if blocks:
        return "\n\n".join(blocks)
    return text.strip()


def extract_import_modules(code: str) -> list[str]:
    modules: set[str] = set()
    scan_text = code[:200_000]
    try:
        tree = ast.parse(scan_text) if len(code) <= 200_000 else None
    except (SyntaxError, MemoryError, RecursionError, ValueError):
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        modules.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    modules.add(node.module.split(".", 1)[0])
    if not modules:
        for line in scan_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                rest = stripped[len("import ") :]
                for part in rest.split(","):
                    name = part.strip().split(" as ", 1)[0].split(".", 1)[0]
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                        modules.add(name)
            elif stripped.startswith("from ") and " import " in stripped:
                name = stripped[len("from ") :].split(" import ", 1)[0].split(".", 1)[0].strip()
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                    modules.add(name)
    return sorted(modules, key=str.lower)


def clean_pip_token(token: str) -> str:
    pkg = str(token).strip().lower().strip(",;")
    if not pkg or pkg in PIP_SKIP_TOKENS:
        return ""
    if pkg.startswith("-") or pkg.startswith(("http://", "https://", "git+")):
        return ""
    pkg = pkg.split("[", 1)[0]
    pkg = re.split(r"(?:==|>=|<=|~=|!=|>|<|=)", pkg, maxsplit=1)[0]
    pkg = re.sub(r"[-_.]+", "-", pkg).strip(" `.-")
    if pkg in STD_LIBRARY_MODULES:
        return ""
    return pkg


def extract_pip_install_args(answer_text: str) -> list[str]:
    text = answer_region(answer_text)
    if not isinstance(text, str):
        return []
    text = text.strip()
    if not text or text.lower() == "none":
        return []
    text = text.replace("pip install command", "pip command")
    packages: list[str] = []

    # Mirrors yukai_run_hallucination_scan.extract_pip_packages: split
    # `pip install a b c` by spaces into separate package tokens.
    bash_blocks = re.findall(r"```bash(.*?)```", text, flags=re.DOTALL)
    if len(bash_blocks) > 1:
        for cleaned_text in bash_blocks:
            count = cleaned_text.count("pip")
            if count == 1:
                cleaned = cleaned_text.replace("\n", " ")
                pip_match = re.search(r"pip install ([^#\n]+)", cleaned)
                if pip_match:
                    packages.extend(pip_match.group(1).split())
            else:
                for pip_match in re.findall(r"pip install ([^#\n]+)", cleaned_text):
                    packages.extend(pip_match.split())
    elif len(bash_blocks) == 1:
        cleaned_text = bash_blocks[0].replace("\n", " ")
        count = cleaned_text.count("pip install")
        if count == 1:
            pip_match = re.search(r"pip install ([^#\n]+)", cleaned_text)
            if pip_match:
                packages.extend(pip_match.group(1).split())
        else:
            for pip_match in re.findall(r"pip install ([^#\n]+)", cleaned_text):
                packages.extend(pip_match.split())
    else:
        generic_blocks = re.findall(r"```(.*?)```", text, flags=re.DOTALL)
        if generic_blocks:
            cleaned = generic_blocks[0]
        else:
            inline_blocks = re.findall(r"`(.*?)`", text, flags=re.DOTALL)
            cleaned = inline_blocks[0] if inline_blocks else text
        pip_match = re.search(r"pip install ([^#\n]+)", cleaned)
        if pip_match:
            packages.extend(pip_match.group(1).split())
    return packages


def install_command(answer_text: str) -> str:
    packages = extract_pip_install_args(answer_text)
    if packages:
        cleaned = [clean_pip_token(pkg) for pkg in packages]
        unique = [pkg for pkg in cleaned if pkg]
        if unique:
            return "pip install " + " ".join(unique)
    if answer_region(answer_text).strip().lower() == "none":
        return "None"
    return ""


def split_install_packages(answer_text: str) -> list[str]:
    packages = extract_pip_install_args(answer_text)
    if not packages:
        return []
    cleaned = [clean_pip_token(pkg) for pkg in packages]
    return sorted(set(pkg for pkg in cleaned if pkg))


def split_import_mapper_packages(answer_text: str) -> list[str]:
    text = answer_region(answer_text)
    if not isinstance(text, str):
        return []
    text = text.strip()
    if not text or text.lower() == "none":
        return []

    packages = []
    for part in re.split(r"[,，\n]+", text):
        token = clean_pip_token(part)
        if token:
            packages.append(token)
    return sorted(set(packages))


def classify_packages(packages: list[str], cutoff, release_cache: dict) -> tuple[list[str], list[str]]:
    return classify_packages_by_pypi(packages, language="Python", cutoff=cutoff, release_cache=release_cache)


def load_cross_task_model(model_path: Path, delta_dir: Path | None, adapter_type: str) -> tuple[Any, Any, dict[str, Any]]:
    if not delta_dir:
        model, tokenizer = load_model(model_path, None)
        return model, tokenizer, {"adapter_type": "unmodified", "model_path": str(model_path)}
    if adapter_type == "auto":
        adapter_type = "bound"
    if adapter_type != "bound":
        raise ValueError(f"unsupported adapter_type={adapter_type}; this package only ships BOUND adapters")
    model, tokenizer = load_model(model_path, delta_dir)
    return model, tokenizer, {"adapter_type": adapter_type, "delta_dir": str(delta_dir)}


def classify_task(raw: str, task: str, cutoff, release_cache: dict) -> dict[str, Any]:
    if task not in CROSS_TASKS:
        raise ValueError(f"unknown task: {task}")
    if task == "code":
        normalized_raw = answer_region(raw)
        packages = split_import_mapper_packages(normalized_raw)
    else:
        normalized_raw = install_command(raw)
        packages = split_install_packages(raw)
    valid, hall = classify_packages(packages, cutoff, release_cache)
    return {"raw": normalized_raw, "model_raw": raw, "packages": packages, "valid": valid, "hallucinated": hall}


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, float | int]:
    n = len(trials)
    total_valid = sum(len(t.get("valid") or []) for t in trials)
    total_hall = sum(len(t.get("hallucinated") or []) for t in trials)
    total_pkg = total_valid + total_hall
    empty = sum(not (t.get("valid") or t.get("hallucinated") or t.get("packages")) for t in trials)
    return {
        "n_trials": n,
        "total_valid": total_valid,
        "total_hallucinated": total_hall,
        "sample_hr": sum(bool(t.get("hallucinated")) for t in trials) / max(n, 1),
        "package_hr": total_hall / max(total_pkg, 1),
        "valid_rate": sum(bool(t.get("valid")) for t in trials) / max(n, 1),
        "empty_rate": empty / max(n, 1),
        "avg_packages": total_pkg / max(n, 1),
        "avg_valid": total_valid / max(n, 1),
        "avg_hallucinated": total_hall / max(n, 1),
    }


def iter_trial_rows(rows: list[dict[str, Any]]):
    for row in rows:
        repeats = row.get("repeats")
        if isinstance(repeats, list):
            yield from repeats
        else:
            yield row


def task_metrics(rows: list[dict[str, Any]], task: str) -> dict[str, float | int]:
    trials = [row["tasks"][task] for row in iter_trial_rows(rows) if task in row.get("tasks", {})]
    return summarize_trials(trials)


def jaccard(a: set[str], b: set[str]) -> float | None:
    union = a | b
    if not union:
        return None
    return len(a & b) / len(union)


def cross_task_metrics(rows: list[dict[str, Any]], tasks_to_run: list[str]) -> dict[str, float | int]:
    trial_rows = list(iter_trial_rows(rows))
    any_overlap = 0
    all_overlap = 0
    pair_values: dict[str, list[float]] = {}
    for row in trial_rows:
        task_rows = row.get("tasks", {})
        hall_sets = {
            task: set(task_rows.get(task, {}).get("hallucinated") or [])
            for task in tasks_to_run
            if task in task_rows
        }
        repeated = set()
        for i, left in enumerate(tasks_to_run):
            for right in tasks_to_run[i + 1 :]:
                key = f"{left}_{right}_jaccard"
                pair_values.setdefault(key, [])
                value = jaccard(hall_sets.get(left, set()), hall_sets.get(right, set()))
                if value is not None:
                    pair_values[key].append(value)
                repeated |= hall_sets.get(left, set()) & hall_sets.get(right, set())
        any_overlap += int(bool(repeated))
        if len(hall_sets) > 1:
            all_overlap += int(bool(set.intersection(*hall_sets.values())))
    metrics: dict[str, float | int] = {
        "n_prompts": len(rows),
        "n_trials": len(trial_rows),
        "any_cross_task_overlap": any_overlap / max(len(trial_rows), 1),
        "all_task_overlap": all_overlap / max(len(trial_rows), 1),
    }
    for key, values in pair_values.items():
        metrics[key] = sum(values) / max(len(values), 1)
        metrics[f"{key}_n"] = len(values)
    return metrics


def build_summary(rows: list[dict[str, Any]], args) -> dict[str, Any]:
    tasks_to_run = parse_tasks(args.tasks)
    summary: dict[str, Any] = {
        "model": args.model_name,
        "method": METHOD_NAME,
        "mode": "offline" if args.responses_file else "generation",
        "tasks": tasks_to_run,
        "num_repeats": args.num_repeats,
    }
    for task in tasks_to_run:
        metrics = task_metrics(rows, task)
        for key, value in metrics.items():
            summary[f"{task}_{key}"] = value
    summary.update(cross_task_metrics(rows, tasks_to_run))
    return summary


def write_grouped_case_details(rows: list[dict[str, Any]], out_file: Path) -> None:
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row.get("repeats"), list):
            original_id = str(row.get("original_id", row.get("id")))
            group = groups.setdefault(
                original_id,
                {
                    "original_id": row.get("original_id", row.get("id")),
                    "question": row.get("question", ""),
                    "cross_task_source": row.get("cross_task_source", {}),
                    "repeats": [],
                },
            )
            group["repeats"].extend(row["repeats"])
            continue
        original_id = str(row.get("original_id", row.get("id")))
        group = groups.setdefault(
            original_id,
            {
                "original_id": row.get("original_id", row.get("id")),
                "question": row.get("question", ""),
                "cross_task_source": row.get("cross_task_source", {}),
                "repeats": [],
            },
        )
        group["repeats"].append(row)
    with out_file.open("w", encoding="utf-8") as f:
        for group in groups.values():
            group["repeats"] = sorted(
                group["repeats"],
                key=lambda row: int((row.get("cross_task_repeat") or {}).get("repeat_id", 0)),
            )
            f.write(json.dumps(group, ensure_ascii=False) + "\n")


def code_messages(question: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": CODE_SYSTEM_MESSAGE}, {"role": "user", "content": f"[TASK]\n{question}\n[/TASK]"}]


def install_messages(question: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": TASK_PACKAGE_CHECK_SYSTEM}, {"role": "user", "content": f"[TASK]\n{question}\n[/TASK]"}]


def import_package_messages(modules: list[str]) -> list[dict[str, str]]:
    imports = ", ".join(modules) if modules else "None"
    return [{"role": "system", "content": IMPORT_PACKAGE_SYSTEM}, {"role": "user", "content": f"[IMPORTS]\n{imports}\n[/IMPORTS]"}]


def run_offline(args) -> list[dict[str, Any]]:
    tasks_to_run = parse_tasks(args.tasks)
    cutoff = infer_model_cutoff(args.model_path or args.model_name, args.model_cutoff)
    release_cache: dict[str, Any] = {}
    rows = []
    for i, row in enumerate(read_jsonl(Path(args.responses_file))):
        tasks = {}
        raw_tasks = row.get("tasks") or {}
        for task in tasks_to_run:
            raw = raw_tasks.get(task)
            if isinstance(raw, dict):
                raw = raw.get("raw", "")
            if raw is None:
                raw = row.get(task, "")
            tasks[task] = classify_task(str(raw), task, cutoff, release_cache)
        rows.append({"id": row.get("id", i), "question": row.get("question", ""), "tasks": tasks})
        if args.max_prompts and len(rows) >= args.max_prompts:
            break
    return rows


def run_generation(args) -> list[dict[str, Any]]:
    tasks_to_run = parse_tasks(args.tasks)
    set_gpu(args.gpu)
    model, tokenizer, adapter_info = load_cross_task_model(
        Path(args.model_path),
        Path(args.delta_dir) if args.delta_dir else None,
        args.adapter_type,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    args._adapter_info = adapter_info
    cutoff = infer_model_cutoff(args.model_path, args.model_cutoff)
    release_cache: dict[str, Any] = {}
    base_prompts = read_prompts(Path(args.prompt_file), args.max_prompts)
    case_rows = []
    for case_index, row in enumerate(tqdm(base_prompts, desc=f"cross_task {args.model_name}/{METHOD_NAME}"), start=1):
        q = row["question"]
        original_id = row.get("original_id", row.get("id", case_index))
        case_row = {
            "original_id": original_id,
            "question": q,
            "cross_task_source": row.get("cross_task_source", {}),
            "cross_task_case_index": row.get("cross_task_case_index", case_index),
            "repeats": [],
        }
        for repeat_id in range(1, args.num_repeats + 1):
            tasks: dict[str, Any] = {}
            if "code" in tasks_to_run:
                code_raw = gen_chat(
                    model,
                    tokenizer,
                    code_messages(q),
                    args.code_max_new_tokens,
                    do_sample=args.temperature > 0,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    top_k=args.top_k,
                )
                code_text = code_block(code_raw)
                import_modules = extract_import_modules(code_text) if code_text.lower() != "none" else []
                tasks["code"] = {
                    "raw": "",
                    "model_raw": "",
                    "packages": [],
                    "valid": [],
                    "hallucinated": [],
                    "code_generation_raw": code_raw,
                    "code_block": code_text,
                    "import_modules": import_modules,
                }
            if "install" in tasks_to_run:
                install_raw = gen_chat(
                    model,
                    tokenizer,
                    install_messages(q),
                    args.install_max_new_tokens,
                    do_sample=args.temperature > 0,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    top_k=args.top_k,
                )
                tasks["install"] = classify_task(install_raw, "install", cutoff, release_cache)
            case_row["repeats"].append(make_repeat_row(row, case_index, repeat_id, args.num_repeats, tasks))
        case_rows.append(case_row)

    if "code" not in tasks_to_run:
        return case_rows

    mapper_model = model
    mapper_tokenizer = tokenizer
    if args.delta_dir:
        release_cuda_model(model, tokenizer)
        model = None
        tokenizer = None
        mapper_model, mapper_tokenizer = load_model(Path(args.model_path), None)
        if mapper_tokenizer.pad_token is None:
            mapper_tokenizer.pad_token = mapper_tokenizer.eos_token

    for case_row in tqdm(case_rows, desc=f"cross_task {args.model_name}/base import mapper"):
        for repeat_row in case_row["repeats"]:
            code_task = repeat_row.get("tasks", {}).get("code", {})
            import_modules = code_task.get("import_modules") or []
            code_pkg_raw = ""
            if import_modules:
                code_pkg_raw = gen_chat(
                    mapper_model,
                    mapper_tokenizer,
                    import_package_messages(import_modules),
                    args.install_max_new_tokens,
                    do_sample=args.temperature > 0,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    top_k=args.top_k,
                )
            classified = classify_task(code_pkg_raw, "code", cutoff, release_cache)
            code_task.update(classified)
    return case_rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-path", default="")
    parser.add_argument("--delta-dir", default="")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--responses-file", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--adapter-type", default="auto", choices=["auto", "bound"])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-prompts", type=int, default=100)
    parser.add_argument("--num-repeats", type=int, default=DEFAULT_NUM_REPEATS)
    parser.add_argument("--tasks", default="code,install", help="Comma-separated subset of: code,install")
    parser.add_argument("--model-cutoff", default="")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--code-max-new-tokens", type=int, default=2048)
    parser.add_argument("--install-max-new-tokens", type=int, default=128)
    args = parser.parse_args(argv)

    if not args.responses_file and (not args.model_path or not args.prompt_file):
        raise SystemExit("generation mode requires --model-path and --prompt-file; offline mode requires --responses-file")
    if args.num_repeats < 1:
        raise SystemExit("--num-repeats must be at least 1")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = run_offline(args) if args.responses_file else run_generation(args)
    grouped_details_file = out_dir / "cross_task_case_grouped.jsonl"
    write_grouped_case_details(rows, grouped_details_file)
    summary = build_summary(rows, args)
    case_payload = {
        "model": args.model_name,
        "method": METHOD_NAME,
        "run_id": args.run_id,
        "tasks": parse_tasks(args.tasks),
        "model_path": args.model_path,
        "delta_dir": args.delta_dir,
        "adapter_type": args.adapter_type,
        "resolved_adapter": getattr(args, "_adapter_info", {}),
        "prompt_file": args.prompt_file,
        "responses_file": args.responses_file,
        "out_dir": str(out_dir),
        "grouped_details_file": str(grouped_details_file),
        "gpu": args.gpu,
        "max_prompts": args.max_prompts,
        "num_repeats": args.num_repeats,
        "model_cutoff": args.model_cutoff,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
        "code_max_new_tokens": args.code_max_new_tokens,
        "install_max_new_tokens": args.install_max_new_tokens,
    }
    write_json(out_dir / "case.json", case_payload)
    write_json(out_dir / "cross_task_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"grouped details: {grouped_details_file}")
    print(f"summary: {out_dir / 'cross_task_summary.json'}")


if __name__ == "__main__":
    main()
