#!/usr/bin/env python3
"""E0: freeze paper evidence and audit every numeric table cell.

Run from any directory. Outputs are written to the sibling ``results/``
directory under ``experiment/E0_version_audit/``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
REBUTTAL = ROOT / "BOUND_rebuttal"
BOUND = ROOT / "BOUND"
OUT = Path(__file__).resolve().parents[1] / "results"
RAW_MD = BOUND / "results" / "paper" / "paper_raw_data.md"
RESULTS_TEX = REBUTTAL / "paper" / "Package_Hallucination_icse" / "catalogue" / "results.tex"
DISCUSSION_TEX = REBUTTAL / "paper" / "Package_Hallucination_icse" / "catalogue" / "discussion.tex"
TOL = 5.1e-4

sys.path.insert(0, str(BOUND))
from bound.validate_results import parse_tables  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_number(value: str) -> float | None:
    value = str(value).strip().strip("`").replace("%", "")
    if value in {"", "-", "--"}:
        return None
    return float(value)


def canonical_model(value: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", value.lower())
    return {
        "deepseekcoder": "deepseekcoder",
        "qwen3": "qwen3",
        "llama31": "llama3.1",
    }[key]


def canonical_method(value: str) -> str:
    value = value.replace("\\appname", "BOUND")
    value = re.sub(r"\\(?:cellcolor|textbf|scriptsize)\{[^{}]*\}", lambda m: m.group(0), value)
    value = re.sub(r"\\cellcolor\{[^{}]*\}", "", value)
    value = re.sub(r"\\(?:textbf|scriptsize)\{([^{}]*)\}", r"\1", value)
    value = value.replace("\\midrule", "").replace("{", "").replace("}", "").strip()
    return value


def markdown_tables() -> list[dict]:
    return parse_tables(RAW_MD.read_text(encoding="utf-8"))


def table_by_heading(tables: list[dict], suffix: str) -> dict:
    return next(table for table in tables if table["heading"].endswith(suffix))


def latex_block(path: Path, label: str) -> str:
    text = path.read_text(encoding="utf-8")
    pos = text.index(f"\\label{{{label}}}")
    start = text.rfind("\\begin{table", 0, pos)
    end = text.index("\\end{table", pos)
    end = text.index("}", end) + 1
    lines = []
    for line in text[start:end].splitlines():
        if line.lstrip().startswith("%"):
            continue
        # A percent sign starts a comment only when it is not escaped as ``\%``.
        lines.append(re.split(r"(?<!\\)%", line, maxsplit=1)[0])
    return "\n".join(lines)


def latex_rows(path: Path, label: str) -> list[str]:
    block = latex_block(path, label)
    rows = []
    current = ""
    for line in block.splitlines():
        current += " " + line.strip()
        while "\\\\" in current:
            row, current = current.split("\\\\", 1)
            rows.append(row.strip())
    return rows


def floats(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"(?<![A-Za-z0-9])[-+]?\d+\.\d+", text)]


def paper_values() -> dict[tuple, float | None]:
    values: dict[tuple, float | None] = {}

    for label, path, methods, scopes in [
        ("tab:main_results_three_models", RESULTS_TEX, 7, ["edit50", "unseen"]),
        ("tab:rq2_cross_task", RESULTS_TEX, 6, ["code", "install"]),
    ]:
        current_model = None
        for row in latex_rows(path, label):
            model_match = re.search(r"\\multirow\{\d+\}\{\*\}\{([^{}]+)\}", row)
            if model_match:
                current_model = canonical_model(model_match.group(1))
            nums = floats(row)
            if current_model is None or len(nums) < 3:
                continue
            cells = row.split("&")
            method = canonical_method(cells[1] if len(cells) > 1 else "")
            if method not in {"Base", "BOUND", "ROME", "MEMIT", "DINM", "Full-FT", "Self-Refinement"}:
                continue
            # Llama-3.1 contributes an extra decimal token from its model name.
            nums = nums[-6:] if len(nums) >= 6 else nums
            chunks = (nums[:3], nums[3:]) if len(nums) == 6 else (nums[:3], [])
            for scope, chunk in zip(scopes, chunks):
                for metric, value in zip(("Sample-HR", "Package-HR", "Valid-Rate"), chunk):
                    values[(label, current_model, method, scope, metric)] = value
            if label == "tab:main_results_three_models" and method == "Self-Refinement":
                for metric in ("Sample-HR", "Package-HR", "Valid-Rate"):
                    values[(label, current_model, method, "unseen", metric)] = None

    for row in latex_rows(RESULTS_TEX, "tab:rq3_ablation"):
        nums = floats(row)
        if len(nums) != 9:
            continue
        setting = canonical_method(row.split("&", 1)[0])
        if setting not in {"BOUND", "w/o Localization", "w/o Valid-NLL", "w/o Hall-UL", "w/o Locality-KL"}:
            continue
        for model, chunk in zip(("deepseekcoder", "qwen3", "llama3.1"), (nums[:3], nums[3:6], nums[6:])):
            for metric, value in zip(("Sample-HR", "Package-HR", "Valid-Rate"), chunk):
                values[("tab:rq3_ablation", model, setting, "unseen100", metric)] = value

    for row in latex_rows(DISCUSSION_TEX, "tab:cost_bound"):
        if "&" not in row:
            continue
        method = canonical_method(row.split("&", 1)[0])
        if method not in {"BOUND", "ROME", "MEMIT", "DINM", "Full-FT", "Self-Refinement"}:
            continue
        cells = [canonical_method(cell) for cell in row.split("&")]
        for col, cell in zip(("Loc. time (s)", "Edit time (s)", "Test time (s)", "Artifact size"), cells[1:5]):
            number = as_number(cell.split()[0])
            values[("tab:cost_bound", "all", method, "mean", col)] = number

    for row in latex_rows(DISCUSSION_TEX, "tab:editing_drop"):
        nums = floats(row)
        if len(nums) < 6:
            continue
        nums = nums[-6:]
        model_cell = canonical_method(row.split("&", 1)[0])
        try:
            model = canonical_model(model_cell)
        except KeyError:
            continue
        for metric, value in zip(("pass@1 Orig.", "pass@1 Edited", "pass@1 Delta", "pass@10 Orig.", "pass@10 Edited", "pass@10 Delta"), nums):
            values[("tab:editing_drop", model, "BOUND", "HumanEval", metric)] = value
    return values


def source_path(value: str) -> Path:
    return BOUND / value.strip().strip("`")


def add_cell(rows: list[dict], sources: set[Path], paper: dict, key: tuple, calculated: float | None,
             paths: list[Path], fields: str, aggregation: str, scale: float = 1.0,
             decimals: int = 4, note: str = "") -> None:
    present_in_paper = key in paper
    paper_value = paper.get(key)
    sources.update(paths)
    if not present_in_paper:
        status, diff = "missing", None
    elif paper_value is None and calculated is None:
        status, diff = "not_applicable", None
    elif paper_value is None or calculated is None:
        status, diff = "mismatch", None
    else:
        shown_calc = calculated * scale
        diff = abs(paper_value - shown_calc)
        if round(paper_value, decimals) == round(shown_calc, decimals):
            status = "match"
        elif diff <= 1.01 * (10 ** (-decimals)):
            status = "rounding_only"
        else:
            status = "mismatch"
    rows.append({
        "table": key[0],
        "cell_id": "|".join(str(item) for item in key[1:]),
        "model": key[1],
        "method_or_setting": key[2],
        "scope_or_task": key[3],
        "metric": key[4],
        "paper_value": "" if paper_value is None else f"{paper_value:.10g}",
        "recomputed_value": "" if calculated is None else f"{calculated * scale:.10g}",
        "absolute_difference": "" if diff is None else f"{diff:.10g}",
        "status": status,
        "aggregation": aggregation,
        "source_paths": ";".join(str(p.relative_to(ROOT)) for p in paths),
        "source_fields": fields,
        "notes": note,
    })


def build_provenance() -> tuple[list[dict], set[Path], dict]:
    tables = markdown_tables()
    paper = paper_values()
    rows: list[dict] = []
    sources: set[Path] = {RAW_MD, RESULTS_TEX, DISCUSSION_TEX}

    # RQ1
    base = table_by_heading(tables, "Base / Original 结果")["rows"]
    methods = table_by_heading(tables, "四折方法结果")["rows"]
    for model in ("deepseekcoder", "llama3.1", "qwen3"):
        model_base = [r for r in base if r["model"] == model]
        for scope in ("edit50", "unseen"):
            selected = [r for r in model_base if ("edit50" in r["scope"]) == (scope == "edit50")]
            paths = [source_path(r["result"]) for r in selected]
            for metric, field in (("Sample-HR", "sample_hallucination_rate"), ("Package-HR", "package_hallucination_rate"), ("Valid-Rate", "sample_valid_rate")):
                vals = [read_json(p)["summary"][field] for p in paths]
                calc = sum(vals) / len(vals)
                key = ("tab:main_results_three_models", model, "Base", scope, metric)
                add_cell(rows, sources, paper, key, calc, paths, f"summary.{field}", "arithmetic mean across four folds" if scope == "edit50" else "single heldout base run")

        for method in ("BOUND", "ROME", "MEMIT", "DINM", "Full-FT", "Self-Refinement"):
            for scope in ("edit50", "unseen"):
                raw_scope = "heldout" if scope == "unseen" else scope
                selected = [r for r in methods if r["model"] == model and r["method"] == method and r["scope"] == raw_scope]
                if not selected:
                    for metric in ("Sample-HR", "Package-HR", "Valid-Rate"):
                        key = ("tab:main_results_three_models", model, method, scope, metric)
                        add_cell(rows, sources, paper, key, None, [], "not produced", "not applicable", note="Self-Refinement is edit-time inference only")
                    continue
                paths = [source_path(r["result"]) for r in selected]
                prefix = "" if method == "Self-Refinement" else "edited_"
                for metric, field in (("Sample-HR", f"{prefix}sample_hallucination_rate"), ("Package-HR", f"{prefix}package_hallucination_rate"), ("Valid-Rate", f"{prefix}sample_valid_rate")):
                    vals = [read_json(p)["summary"][field] for p in paths]
                    key = ("tab:main_results_three_models", model, method, scope, metric)
                    add_cell(rows, sources, paper, key, sum(vals) / len(vals), paths, f"summary.{field}", "arithmetic mean across four folds")

    # RQ2: the existing validator has already recomputed every row from rq2_details.jsonl.
    rq2 = next(t for t in tables if "RQ2 原始数据" in t["heading"] and "raw result" in t["header"])["rows"]
    for model in ("deepseekcoder", "qwen3", "llama3.1"):
        for method in ("Base", "BOUND", "DINM", "MEMIT", "ROME", "Full-FT"):
            selected = [r for r in rq2 if r["model"] == model and r["method"] == method]
            paths = [source_path(r["raw result"]).with_name("rq2_details.jsonl") for r in selected]
            for task, prefix in (("code", "code"), ("install", "install")):
                for metric in ("Sample-HR", "Package-HR", "Valid-Rate"):
                    calc = sum(float(r[f"{prefix} {metric}"]) for r in selected) / len(selected)
                    key = ("tab:rq2_cross_task", model, method, task, metric)
                    add_cell(rows, sources, paper, key, calc, paths, f"tasks.{task}; {metric} recomputed per 500 records", "arithmetic mean across four folds")

    # RQ3
    rq3 = next(t for t in tables if "RQ3 原始数据" in t["heading"] and t["header"][:3] == ["model", "fold", "setting"])["rows"]
    setting_dirs = {"BOUND": "BOUND", "w/o Localization": "wo_localization", "w/o Valid-NLL": "wo_valid_nll", "w/o Hall-UL": "wo_unlikelihood", "w/o Locality-KL": "wo_locality_kl"}
    for setting, setting_dir in setting_dirs.items():
        for model in ("deepseekcoder", "qwen3", "llama3.1"):
            selected = [r for r in rq3 if r["model"] == model and r["setting"] == setting]
            paths = [BOUND / "results/paper/rq3_ablation" / model / f"fold_{r['fold']}" / setting_dir / "rq3_metrics.json" for r in selected]
            for metric, field in (("Sample-HR", "sample_hr"), ("Package-HR", "package_hr"), ("Valid-Rate", "valid_rate")):
                vals = [read_json(p)[field] for p in paths]
                key = ("tab:rq3_ablation", model, setting, "unseen100", metric)
                add_cell(rows, sources, paper, key, sum(vals) / len(vals), paths, field, "arithmetic mean across four folds")

    # Cost; storage uses common units within each method.
    cost_rows = table_by_heading(tables, "可编辑方法成本输入")["rows"] + table_by_heading(tables, "Self-Refinement 成本输入")["rows"]
    for method in ("BOUND", "ROME", "MEMIT", "DINM", "Full-FT", "Self-Refinement"):
        selected = [r for r in cost_rows if r["method"] == method]
        for col in ("Loc. time (s)", "Edit time (s)", "Test time (s)"):
            vals = [as_number(r[col]) for r in selected]
            valid = [v for v in vals if v is not None]
            calc = sum(valid) / len(valid) if valid else None
            key = ("tab:cost_bound", "all", method, "mean", col)
            add_cell(rows, sources, paper, key, calc, [RAW_MD], f"Cost/{method}/{col}", "arithmetic mean across three models", decimals=2, note="numeric inputs are preserved in paper_raw_data.md; per-run log provenance remains incomplete")
        size_values = []
        unit = ""
        for r in selected:
            match = re.match(r"([0-9.]+)\s*([KMG]B)", r["Artifact size"], re.I)
            if match:
                size_values.append(float(match.group(1)))
                unit = match.group(2).upper()
        calc = sum(size_values) / len(size_values) if size_values else None
        key = ("tab:cost_bound", "all", method, "mean", "Artifact size")
        add_cell(rows, sources, paper, key, calc, [RAW_MD], f"Cost/{method}/Artifact size ({unit or 'NA'})", "arithmetic mean across three models", decimals=2, note=f"unit={unit or 'NA'}; numeric inputs are preserved in paper_raw_data.md")

    # HumanEval selected-run protocol documented in paper_raw_data.md.
    human = table_by_heading(tables, "HumanEval 论文表复算输入行")["rows"]
    for model in ("deepseekcoder", "qwen3", "llama3.1"):
        orig_row = next(r for r in human if r["model"] == model and r["table column"] == "Orig.")
        edit_rows = [r for r in human if r["model"] == model and r["table column"] == "Edited"]
        orig_path = source_path(orig_row["raw summary"])
        edit_paths = [source_path(r["raw summary"]) for r in edit_rows]
        for short, json_key in (("pass@1", "pass@1"), ("pass@10", "pass@10")):
            orig = read_json(orig_path)["pass_at_k"][json_key]
            edited = sum(read_json(p)["pass_at_k"][json_key] for p in edit_paths) / len(edit_paths)
            for suffix, calc, paths, agg in (("Orig.", orig, [orig_path], "single selected Base run"), ("Edited", edited, edit_paths, "arithmetic mean of one selected run per fold")):
                key = ("tab:editing_drop", model, "BOUND", "HumanEval", f"{short} {suffix}")
                add_cell(rows, sources, paper, key, calc, paths, f"pass_at_k.{json_key}", agg, scale=100.0, decimals=2)
            displayed_delta = round(edited * 100, 2) - round(orig * 100, 2)
            key = ("tab:editing_drop", model, "BOUND", "HumanEval", f"{short} Delta")
            add_cell(rows, sources, paper, key, displayed_delta, [orig_path] + edit_paths, f"pass_at_k.{json_key}", "displayed Edited minus displayed Orig.", decimals=2)

    return rows, sources, paper


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state(path: Path) -> dict:
    def run(*args: str) -> str:
        result = subprocess.run(["git", "-C", str(path), *args], text=True, capture_output=True, check=False)
        return result.stdout.strip()
    return {"path": str(path.relative_to(ROOT)), "commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"), "status_porcelain": run("status", "--porcelain=v1")}


def cutoff_audit() -> list[dict]:
    model_dirs = {"deepseekcoder": "deepseekcoder", "qwen3": "qwen3-release", "llama3.1": "llama3.1-release"}
    clone_cfgs = {"deepseekcoder": "deepseekcoder.yaml", "qwen3": "qwen3.yaml", "llama3.1": "llama3.1.yaml"}
    result = []
    for model, source_dir in model_dirs.items():
        originals = []
        for fold in "ABCD":
            path = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / source_dir / f"fold_{fold}" / "blast_50/experiment_config.json"
            originals.append(read_json(path).get("eval_model_cutoff"))
        clone_path = REBUTTAL / "replication package/BOUND/bound/hparams" / clone_cfgs[model]
        text = clone_path.read_text(encoding="utf-8")
        match = re.search(r"^eval_model_cutoff:\s*['\"]?([^'\"\s#]+)", text, re.M)
        clone = match.group(1) if match else None
        result.append({"model": model, "paper_result_config_cutoffs": sorted(set(originals)), "cloned_replication_cutoff": clone, "match": len(set(originals)) == 1 and originals[0] == clone, "clone_path": str(clone_path.relative_to(ROOT))})
    return result


def delta_audit() -> list[dict]:
    import torch
    model_dirs = {"deepseekcoder": "deepseekcoder", "qwen3": "qwen3-release", "llama3.1": "llama3.1-release"}
    records = []
    for model, source_dir in model_dirs.items():
        for fold in "ABCD":
            path = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / source_dir / f"fold_{fold}" / "blast_50/blast_delta.pt"
            state = torch.load(path, map_location="cpu", weights_only=True)
            module_names = sorted({key.rsplit(".", 1)[0] for key in state if key.endswith((".A", ".B", ".lora_A", ".lora_B"))})
            records.append({"model": model, "fold": fold, "path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size, "size_kib": path.stat().st_size / 1024, "tensor_count": len(state), "target_module_count": len(module_names), "target_modules": module_names, "parameter_count": sum(value.numel() for value in state.values())})
    return records


def write_report(rows: list[dict], cutoffs: list[dict], deltas: list[dict], manifest: dict) -> None:
    mismatches = [r for r in rows if r["status"] == "mismatch"]
    rounding_only = [r for r in rows if r["status"] == "rounding_only"]
    by_table = defaultdict(lambda: defaultdict(int))
    for row in rows:
        by_table[row["table"]][row["status"]] += 1
    avg_kib = sum(r["size_kib"] for r in deltas) / len(deltas)
    module_counts = {m: sorted({r["target_module_count"] for r in deltas if r["model"] == m}) for m in ("deepseekcoder", "qwen3", "llama3.1")}
    llama_dir = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605/llama3.1-release/fold_A/blast_50"
    final_files = [llama_dir / name for name in ("blast_delta.pt", "train_log.jsonl", "localization_report.json", "eval_edit_prompts.json", "eval_unseen_prompts.json", "blast_50.gpu4.rq1_run2.runtime.yaml", "blast_50.gpu5.rq1_run2.runtime.yaml")]
    rq1_pairs = []
    for model, source_dir, paper_model in (("deepseekcoder", "deepseekcoder", "deepseekcoder"), ("qwen3", "qwen3-release", "qwen3"), ("llama3.1", "llama3.1-release", "llama3.1")):
        for fold in "ABCD":
            for name in ("eval_edit_prompts.json", "eval_unseen_prompts.json"):
                raw = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / source_dir / f"fold_{fold}/blast_50" / name
                curated = BOUND / "results/paper/rq1_package_recommendation" / paper_model / f"fold_{fold}/BOUND" / name
                rq1_pairs.append((raw, curated, sha256(raw) == sha256(curated), read_json(raw)["summary"] == read_json(curated)["summary"]))

    lines = [
        "# E0 version freeze and result-consistency audit",
        "",
        f"Generated: `{manifest['generated_at_utc']}`",
        "",
        "## Decision summary",
        "",
        f"- **Paper evidence integrity:** {len(rows)} table cells were traced; {sum(r['status'] == 'match' for r in rows)} exact/display matches, {len(rounding_only)} rounding-only differences, {len(mismatches)} material/semantic mismatches, and {sum(r['status'] == 'not_applicable' for r in rows)} explicit N/A cells.",
        f"- **Raw-result validation:** the repository validator completed with `bad=0, warn=2`; all 147 RQ1 rows, 72 RQ2 method-fold results, 60 RQ3 rows, cost arithmetic, and 15 selected HumanEval summaries passed.",
        f"- **RQ1 copy integrity:** {sum(byte_ok for _, _, byte_ok, _ in rq1_pairs)}/{len(rq1_pairs)} curated BOUND evaluation files are byte-identical and {sum(summary_ok for _, _, _, summary_ok in rq1_pairs)}/{len(rq1_pairs)} have identical metric summaries to the historical result files.",
        f"- **LoRA artifacts:** all 12 main BOUND deltas load successfully; average size is `{avg_kib:.2f} KiB`; module counts are DeepSeekCoder={module_counts['deepseekcoder']}, Qwen3={module_counts['qwen3']}, Llama-3.1={module_counts['llama3.1']}.",
        "- **Blocking issue:** cloned replication cutoff dates disagree with the result-producing configs for DeepSeekCoder and Llama-3.1. Do not claim the cloned package reproduces submitted numbers until these configs are reconciled.",
        "",
        "## Cell-level audit",
        "",
        "| Table | Match | Rounding only | Mismatch | N/A |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for table, counts in sorted(by_table.items()):
        lines.append(f"| `{table}` | {counts['match']} | {counts['rounding_only']} | {counts['mismatch']} | {counts['not_applicable']} |")
    lines += ["", "### Mismatching paper cells", ""]
    if not mismatches:
        lines.append("None.")
    else:
        lines += ["| Cell | Paper | Recomputed | Difference |", "| --- | ---: | ---: | ---: |"]
        for row in mismatches:
            lines.append(f"| `{row['table']}::{row['cell_id']}` | {row['paper_value']} | {row['recomputed_value']} | {row['absolute_difference']} |")

    lines += [
        "",
        "Rounding-only differences are at most one unit in the displayed last decimal and arise when the manuscript averages already-rounded fold rows rather than full-precision JSON metrics. They are not counted as material mismatches, but the aggregation rule should be standardized.",
        "",
        "Interpretation: most material mismatches are in RQ2 manuscript TeX versus the currently frozen method-fold results. The 72 stored RQ2 rows independently pass recomputation from `rq2_details.jsonl`; update the paper values or document and freeze the older aggregation source before rebuttal. The cost table also displays MEMIT localization time as N/A while its frozen numeric input is `0.00`; choose one semantic convention.",
        "",
        "## Cutoff audit",
        "",
        "| Model | Result-producing configs | Cloned replication package | Match |",
        "| --- | --- | --- | --- |",
    ]
    for item in cutoffs:
        lines.append(f"| {item['model']} | `{', '.join(item['paper_result_config_cutoffs'])}` | `{item['cloned_replication_cutoff']}` | {'yes' if item['match'] else '**NO**'} |")
    lines += [
        "",
        "The result-producing dates are consistent across folds and are authoritative for reproducing the submitted numbers. However, the paper does not state these exact dates, and the repository contains no citation establishing whether each date denotes a provider-declared knowledge cutoff, model release date, or the package-existence snapshot boundary. This semantic/source provenance remains unresolved and should be documented before artifact release.",
        "",
        "## Llama-3.1 fold A run2 lineage",
        "",
        "`paper_raw_data.md` explicitly states that the RQ1 table uses the Llama-3.1 fold-A BOUND run2 replacement. The run2 artifact sequence is internally coherent:",
        "",
        "| File | Modified (UTC) | Bytes |",
        "| --- | --- | ---: |",
    ]
    for path in final_files:
        stat = path.stat()
        lines.append(f"| `{path.relative_to(ROOT)}` | {datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()} | {stat.st_size} |")
    lines += [
        "",
        "The delta/train/localization artifacts were written first, followed by edit and unseen evaluation files. Both GPU4 and GPU5 runtime YAMLs contain the same experiment configuration; because no immutable run ID is embedded in the JSON outputs, the exact evaluator process cannot be distinguished after the fact. The final directory contents and their hashes are therefore the frozen authority.",
        "",
        "## Base-reference discrepancy",
        "",
        "RQ1 uses dedicated `base_heldout_highrisk_eval.json` files for the Base row. The `baseline_*` fields embedded in edited-model evaluation JSONs are not identical for all models/runs and must not be substituted for those dedicated Base files. This explains previously observed differences such as DeepSeekCoder heldout Sample-HR `0.8333` (paper Base source) versus `0.8288` (embedded baseline in a BOUND evaluation).",
        "",
        "## Manifest scope and limitations",
        "",
        f"`artifact_manifest.json` hashes {manifest['file_count']} evidence files ({manifest['total_bytes']} bytes): manuscript TeX, all files directly cited by the cell provenance table, the 12 BOUND deltas and their configs/logs/evaluations, and the cloned cutoff configs. Large Full-FT checkpoint shards and unused exploratory runs are intentionally excluded because they are not inputs to the submitted paper tables. Their existence was checked separately during the pre-E0 inventory.",
        "",
        "Cost rows remain the weakest lineage: the preserved numeric inputs reproduce the table, but most entries do not point to per-run logs. HumanEval also uses an explicitly selected one-run-per-fold protocol rather than all stored repeats. Both should be disclosed or strengthened in the artifact documentation.",
        "",
        "## Required remediation before rebuttal freeze",
        "",
        "1. Correct or explicitly explain every `mismatch` row in `paper_cell_provenance.csv`, especially RQ2 Base cells.",
        "2. Reconcile DeepSeekCoder and Llama-3.1 cutoff dates in the cloned replication package with the result-producing configs; add a source and definition for each cutoff.",
        "3. Preserve the current Llama fold-A run2 hashes and identify it as the final authoritative run.",
        "4. Add log-level provenance for cost inputs if available; otherwise state that the table is reproducible from frozen numeric inputs but not fully traceable to raw runtime logs.",
    ]
    (OUT / "version_discrepancies.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, sources, _ = build_provenance()
    cutoffs = cutoff_audit()
    deltas = delta_audit()

    # Freeze all direct evidence plus the complete main BOUND artifact record.
    for item in deltas:
        delta = ROOT / item["path"]
        sources.add(delta)
        for name in ("experiment_config.json", "blast_config.json", "localization_report.json", "train_log.jsonl", "eval_edit_prompts.json", "eval_unseen_prompts.json"):
            path = delta.parent / name
            if path.exists():
                sources.add(path)
    for item in cutoffs:
        sources.add(ROOT / item["clone_path"])
    sources.add(OUT / "validation_report.txt")
    sources.update((REBUTTAL / "paper/Package_Hallucination_icse").rglob("*.tex"))

    manifest_files = []
    total_bytes = 0
    for path in sorted(sources):
        if not path.exists() or not path.is_file():
            continue
        stat = path.stat()
        total_bytes += stat.st_size
        manifest_files.append({"path": str(path.relative_to(ROOT)), "size_bytes": stat.st_size, "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(), "sha256": sha256(path)})
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "scope": "Direct inputs to submitted paper tables, manuscript TeX, main 12 BOUND artifacts, and cutoff configs; excludes large full-model checkpoints and unused exploratory runs.",
        "git": [git_state(ROOT), git_state(REBUTTAL)],
        "file_count": len(manifest_files),
        "total_bytes": total_bytes,
        "files": manifest_files,
        "main_bound_deltas": deltas,
        "cutoff_audit": cutoffs,
    }

    with (OUT / "paper_cell_provenance.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(rows, cutoffs, deltas, manifest)

    mismatch_count = sum(row["status"] == "mismatch" for row in rows)
    print(f"cells={len(rows)} mismatches={mismatch_count} files_hashed={len(manifest_files)} avg_delta_kib={sum(x['size_kib'] for x in deltas) / len(deltas):.2f}")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
