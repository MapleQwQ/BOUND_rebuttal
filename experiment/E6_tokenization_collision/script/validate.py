#!/usr/bin/env python3
"""Validate all E6 artifacts and record input provenance."""
import hashlib
import csv
import json
from pathlib import Path

import torch
import transformers

HERE = Path(__file__).resolve().parent
E6 = HERE.parent
ROOT = E6.parents[2]
import sys
sys.path.insert(0, str(ROOT))
from knowledgeEdit.package_edit import summarize_eval_pairs
from knowledgeEdit.package_edit_utils import read_eval_questions

SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
MODELS = {"deepseekcoder": 224, "qwen3-release": 252, "llama3.1-release": 224}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    bound_rows = list(csv.DictReader((E6 / "results/full_rank_spearman_bounds.csv").open()))
    bounds = {(r["model"], r["fold"]): r for r in bound_rows}
    assert len(bounds) == 12, "full-rank bounds must cover 12 distinct folds"
    manifest = []
    for model, modules in MODELS.items():
        for fold in "ABCD":
            old = SOURCE / model / f"fold_{fold}" / "blast_50"
            new = E6 / "results" / model / f"fold_{fold}" / "full_sequence"
            snapshot = E6 / "results" / model / f"fold_{fold}" / "first_token"
            for name in ("localization_report.json", "timing.json", "eval_unseen_prompts.json",
                         "blast_delta.pt", "blast_config.json", "experiment_config.json",
                         "selected_task_recommend_cases.jsonl"):
                assert sha(snapshot / name) == sha(old / name), (model, fold, "first-token snapshot", name)
            conf = json.loads((old / "experiment_config.json").read_text())
            edit = json.loads((new / "blast_config.json").read_text())
            actual_old_edit = json.loads((old / "blast_config.json").read_text())
            assert edit["seed"] == actual_old_edit["seed"], (model, fold, "edit seed")
            assert Path(edit["model_path"]) == Path(actual_old_edit["model_path"]), (model, fold, "model")
            loc = json.loads((new / "localization_report.json").read_text())
            assert loc["n_records"] == 50, (model, fold, "localization records")
            ranked = loc["layer_scores"]
            assert len(ranked) == modules and len({r["module"] for r in ranked}) == modules, (model, fold, "module ranking")
            assert all(ranked[i]["score"] >= ranked[i+1]["score"] for i in range(modules-1)), (model, fold, "ranking order")
            bnd = bounds[(model, fold)]
            assert int(bnd["all_modules"]) == modules and int(bnd["legacy_reported_modules"]) == 200
            assert 0 <= float(bnd["full_rank_spearman_lower_bound"]) <= float(bnd["full_rank_spearman_upper_bound"]) <= 1
            assert (new / "blast_delta.pt").exists(), (model, fold, "adapter")
            ev = json.loads((new / "eval_unseen_prompts.json").read_text())
            expected = read_eval_questions(Path(conf["unseen_file"]), 0, conf["eval_unseen_max_samples"])
            details = ev["details"]
            assert len(details) == len(expected) == ev["summary"]["n_prompts"], (model, fold, "unseen count")
            assert all((x["id"], x["question"]) == pair for x, pair in zip(details, expected)), (model, fold, "unseen ids")
            assert all(len(x["edited"]["trials"]) == 5 for x in details), (model, fold, "generations")
            recalc = summarize_eval_pairs(details)
            assert all(abs(float(ev["summary"][k])-float(v)) < 1e-12 for k, v in recalc.items()), (model, fold, "metrics")
            reused = (new / "unseen_reuse_provenance.json").exists()
            if reused:
                assert sha(new / "eval_unseen_prompts.json") == sha(old / "eval_unseen_prompts.json"), (model, fold, "reused unseen")
                a = torch.load(old / "blast_delta.pt", map_location="cpu", weights_only=True)
                b = torch.load(new / "blast_delta.pt", map_location="cpu", weights_only=True)
                assert set(a) == set(b) and all(torch.equal(a[k], b[k]) for k in a), (model, fold, "reused adapter")
            manifest.append({
                "model": model, "fold": fold, "n_edit_records": 50,
                "n_modules": modules, "n_unseen_prompts": len(details),
                "adapter_identical_and_unseen_reused": reused,
                "edit_records_sha256": sha(old / "selected_task_recommend_cases.jsonl"),
                "legacy_localization_report_sha256": sha(old / "localization_report.json"),
                "legacy_unseen_eval_sha256": sha(old / "eval_unseen_prompts.json"),
                "new_localization_report_sha256": sha(new / "localization_report.json"),
                "new_unseen_eval_sha256": sha(new / "eval_unseen_prompts.json"),
                "model_config_sha256": sha(Path(conf["model_path"]) / "config.json"),
                "tokenizer_config_sha256": sha(Path(conf["model_path"]) / "tokenizer_config.json"),
            })
    out = E6 / "results/validation.json"
    out.write_text(json.dumps({"status": "passed", "n_runs": len(manifest),
                               "software": {"torch": torch.__version__, "transformers": transformers.__version__},
                               "runs": manifest}, ensure_ascii=False, indent=2))
    print(f"validated {len(manifest)} runs -> {out}")


if __name__ == "__main__":
    main()
