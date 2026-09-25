"""CPU-only inventory for the four E5 experiment designs.

Reads historical files without modifying them. Run from anywhere with Python 3.10+.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
HIST = ROOT / "knowledgeEdit/results"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = "ABCD"
METRICS = ("sample_hr", "package_hr", "valid_rate", "empty_rate")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, data: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(name: str):
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def metrics(model: str, fold: str, setting: str):
    return read(HIST / "rq3_ablation_20260613" / model / f"fold_{fold}" / setting / "rq3_metrics.json")


def delta_stats(path: Path):
    # Tensor-only loading; no generated code or model is executed.
    import torch

    state = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not all(isinstance(value, torch.Tensor) for value in state.values()):
        raise ValueError(f"Unexpected adapter state: {path}")
    return sum(value.numel() for value in state.values()), path.stat().st_size


def all_module_inventory():
    out = []
    for model in MODELS:
        for fold in FOLDS:
            base = HIST / "robust_nonedit_highrisk_20260605" / model / f"fold_{fold}" / "blast_50"
            broad = HIST / "rq3_ablation_20260613" / model / f"fold_{fold}" / "wo_localization_all_lora"
            for condition, directory in (("BOUND", base), ("All-module LoRA", broad)):
                cfg = read(directory / "blast_config.json")
                n_params, n_bytes = delta_stats(directory / "blast_delta.pt")
                timing = read(directory / "timing.json")
                result = metrics(model, fold, "BOUND" if condition == "BOUND" else "wo_localization_all_lora")
                out.append({"model": model, "fold": fold, "condition": condition,
                            "source_dir": str(directory.relative_to(ROOT)),
                            "config_sha256": digest(directory / "blast_config.json"),
                            "adapter_sha256": digest(directory / "blast_delta.pt"),
                            "edit_cases": str(cfg["edits_file"]),
                            "rank": cfg["rank"], "alpha": cfg["alpha"], "dropout": cfg["dropout"],
                            "n_edited_modules": int(cfg["n_edited_modules"]),
                            "trainable_parameters": n_params, "adapter_bytes": n_bytes,
                            "localization_seconds": timing.get("localization", {}).get("elapsed_sec", 0),
                            "edit_seconds": timing.get("edit_sec", timing.get("update", {}).get("elapsed_sec", "")),
                            "evaluation_seconds": timing.get("eval_sec", timing.get("inference", {}).get("heldout_total_sec", "")),
                            **{key: result[key] for key in METRICS}})
    write_csv(E5 / "results/01_all_module_lora/existing_runs.csv", out)
    return out


def risk_inventory():
    out = []
    for model in MODELS:
        for fold in FOLDS:
            full_dir = HIST / "robust_nonedit_highrisk_20260605" / model / f"fold_{fold}" / "blast_50"
            hall_dir = HIST / "rq3_ablation_20260613" / model / f"fold_{fold}" / "wo_valid_anchor"
            full_cfg, hall_cfg = read(full_dir / "blast_config.json"), read(hall_dir / "blast_config.json")
            full_report, hall_report = read(full_dir / "localization_report.json"), read(hall_dir / "localization_report.json")
            full_modules, hall_modules = set(full_cfg["edited_modules"]), set(hall_cfg["edited_modules"])
            full_result, hall_result = metrics(model, fold, "BOUND"), metrics(model, fold, "wo_valid_anchor")
            # The edit objective and optimizer must remain fixed when isolating localization risk.
            fields = ("rank", "alpha", "dropout", "max_edits", "epochs", "batch_size", "lr",
                      "task_weight", "answer_neg_weight", "kl_weight", "max_task_packages")
            if any(full_cfg.get(key) != hall_cfg.get(key) for key in fields):
                raise ValueError(f"Training mismatch in {model}/{fold}")
            if float(full_report["anchor_penalty"]) != 0.5 or float(hall_report["anchor_penalty"]) != 0.0:
                raise ValueError(f"Risk-score mismatch in {model}/{fold}")
            out.append({"model": model, "fold": fold,
                        "full_report": str((full_dir / "localization_report.json").relative_to(ROOT)),
                        "hall_only_report": str((hall_dir / "localization_report.json").relative_to(ROOT)),
                        "full_report_sha256": digest(full_dir / "localization_report.json"),
                        "hall_only_report_sha256": digest(hall_dir / "localization_report.json"),
                        "full_modules": len(full_modules), "hall_only_modules": len(hall_modules),
                        "module_jaccard": len(full_modules & hall_modules) / len(full_modules | hall_modules),
                        **{f"full_{key}": full_result[key] for key in METRICS},
                        **{f"hall_only_{key}": hall_result[key] for key in METRICS}})
    write_csv(E5 / "results/02_risk_score/existing_runs.csv", out)
    return out


def localization_inventory():
    source = HIST / "rq4_localization_analysis_20260615"
    family = list(csv.DictReader((source / "rq4_top5_module_family_frequency.csv").open(encoding="utf-8")))
    layers = list(csv.DictReader((source / "rq4_top5_layer_frequency.csv").open(encoding="utf-8")))
    overlap = list(csv.DictReader((source / "rq4_fold_overlap.csv").open(encoding="utf-8")))
    result = {}
    for model in MODELS:
        frows = [r for r in family if r["model"] == model and r["fold"] == "ALL"]
        lrows = [r for r in layers if r["model"] == model and r["fold"] == "ALL"]
        pairs = [r for r in overlap if r["model"] == model and r["fold_a"] < r["fold_b"]]
        if not frows or not lrows or len(pairs) != 6:
            raise ValueError(f"Incomplete RQ4 data: {model}")
        result[model] = {"top_family": max(frows, key=lambda row: float(row["topk_frequency"])),
                         "top5_layer_frequency_sum": sum(float(row["topk_frequency"]) for row in sorted(lrows, key=lambda row: float(row["topk_frequency"]), reverse=True)[:5]),
                         "mean_fold_top5_module_jaccard": statistics.mean(float(row["top5_module_jaccard"]) for row in pairs),
                         "source": str(source.relative_to(ROOT)),
                         "source_sha256": {name: digest(source / name) for name in
                             ("rq4_top5_module_family_frequency.csv", "rq4_top5_layer_frequency.csv", "rq4_fold_overlap.csv")}}
    write_json(E5 / "results/03_localization_stability/existing_summary.json", result)
    return result


def candidate_inventory():
    manifest = []
    source_files = []
    counts = {}
    for model in MODELS:
        test_file = HIST / "rq2_cross_task_20260611" / model / "test100/rq2_test100.jsonl"
        test = rows(test_file)
        source_files.append({"path": str(test_file.relative_to(ROOT)), "sha256": digest(test_file)})
        edit_names = set()
        edit_prompts = []
        for fold in FOLDS:
            edit_file = HIST / "robust_nonedit_highrisk_20260605" / model / f"fold_{fold}" / "blast_50/selected_task_recommend_cases.jsonl"
            source_files.append({"path": str(edit_file.relative_to(ROOT)), "sha256": digest(edit_file)})
            for row in rows(edit_file):
                edit_prompts.append(row["prompt"])
                edit_names.update(norm(p) for p in row.get("valid_reference", []) + row.get("hallucinated", []))
        n_pairs = 0
        n_complete = 0
        for row in test:
            if any(row["question"].strip() in prompt for prompt in edit_prompts):
                raise ValueError(f"Edit/unseen prompt ID overlap: {model}/{row['id']}")
            valid = sorted({norm(x) for x in row.get("valid", [])} - edit_names)
            hall = sorted({norm(x) for x in row.get("hallucinated", [])} - edit_names)
            if set(valid) & set(hall):
                raise ValueError(f"Conflicting labels: {model}/{row['id']}")
            n_pairs += len(valid) * len(hall)
            n_complete += bool(valid and hall)
            manifest.append({"model": model, "prompt_id": str(row["id"]), "question": row["question"],
                             "valid_candidates": valid, "hallucinated_candidates": hall,
                             "n_pairs": len(valid) * len(hall), "labels": "historical, registry verification pending"})
        counts[model] = {"prompts": len(test), "prompts_with_both_classes": n_complete,
                         "valid_candidates": sum(len(r["valid_candidates"]) for r in manifest if r["model"] == model),
                         "hallucinated_candidates": sum(len(r["hallucinated_candidates"]) for r in manifest if r["model"] == model),
                         "pairs": n_pairs}
    out = E5 / "results/04_sequence_margin"
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate_manifest_preliminary.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    write_json(out / "candidate_inventory.json", {"counts": counts, "sources": source_files,
               "rule": "Exclude any package appearing in any fold's edit valid_reference or hallucinated set; historical labels require independent registry verification."})
    registry = ROOT / "BOUND_rebuttal/experiment/E2new_verifier/results/pypi_index_names.txt"
    projects = set(registry.read_text(encoding="utf-8").splitlines())
    screened = []
    screened_counts = {}
    for row in manifest:
        entry = {**row, "valid_candidates": [name for name in row["valid_candidates"] if name in projects],
                 "hallucinated_candidates": [name for name in row["hallucinated_candidates"] if name not in projects],
                 "labels": "historical and 2026-09-24 PyPI-index screened; release-date verification pending"}
        entry["n_pairs"] = len(entry["valid_candidates"]) * len(entry["hallucinated_candidates"])
        screened.append(entry)
    for model in MODELS:
        subset = [row for row in screened if row["model"] == model]
        screened_counts[model] = {"prompts": len(subset),
                                  "prompts_with_both_classes": sum(bool(row["n_pairs"]) for row in subset),
                                  "valid_candidates": sum(len(row["valid_candidates"]) for row in subset),
                                  "hallucinated_candidates": sum(len(row["hallucinated_candidates"]) for row in subset),
                                  "pairs": sum(row["n_pairs"] for row in subset)}
    (out / "candidate_manifest_registry_screened.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in screened), encoding="utf-8")
    write_json(out / "registry_screening.json", {"counts": screened_counts,
        "registry_path": str(registry.relative_to(ROOT)), "registry_sha256": digest(registry),
        "rule": "Keep historically valid names present in the 2026-09-24 PyPI index and historically hallucinated names absent from it. Current existence does not establish model-cutoff validity; project deletion is possible."})
    return counts


def main():
    broad = all_module_inventory()
    risk = risk_inventory()
    stable = localization_inventory()
    candidates = candidate_inventory()
    print(json.dumps({"all_module_rows": len(broad), "risk_rows": len(risk),
                      "localization_models": list(stable), "candidate_counts": candidates}, indent=2))


if __name__ == "__main__":
    main()
