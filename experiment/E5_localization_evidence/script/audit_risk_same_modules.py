"""Audit whether full-risk and hall-only adapters differ when selected modules coincide."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[4]
E5 = Path(__file__).resolve().parents[1]
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")


def main() -> None:
    rows = []
    for model in MODELS:
        for fold in "ABCD":
            full = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605" / model / f"fold_{fold}/blast_50"
            hall = ROOT / "knowledgeEdit/results/rq3_ablation_20260613" / model / f"fold_{fold}/wo_valid_anchor"
            a_cfg = json.loads((full / "blast_config.json").read_text(encoding="utf-8"))
            b_cfg = json.loads((hall / "blast_config.json").read_text(encoding="utf-8"))
            a_modules = {s.strip() for s in a_cfg["resolved_target_modules"].split(",") if s.strip()}
            b_modules = {s.strip() for s in b_cfg["resolved_target_modules"].split(",") if s.strip()}
            common = len(a_modules & b_modules)
            record = {"model": model, "fold": fold, "same_module_set": int(a_modules == b_modules),
                      "module_jaccard": common / len(a_modules | b_modules),
                      "same_seed": int(a_cfg["seed"] == b_cfg["seed"]),
                      "same_training_hparams": int(all(a_cfg.get(key) == b_cfg.get(key) for key in
                                                        ("rank", "alpha", "dropout", "epochs", "batch_size",
                                                         "lr", "task_weight", "answer_neg_weight", "kl_weight")))}
            if a_modules == b_modules:
                a = torch.load(full / "blast_delta.pt", map_location="cpu", weights_only=True)
                b = torch.load(hall / "blast_delta.pt", map_location="cpu", weights_only=True)
                if set(a) != set(b):
                    raise ValueError(f"Adapter key mismatch: {model}/{fold}")
                numerator = sum(torch.sum((a[key].float() - b[key].float()) ** 2).item() for key in a)
                denominator = sum(torch.sum(a[key].float() ** 2).item() for key in a)
                record["relative_l2_adapter_difference"] = (numerator / denominator) ** 0.5 if denominator else 0.0
                record["adapter_exact_equal"] = int(all(torch.equal(a[key], b[key]) for key in a))
            else:
                record["relative_l2_adapter_difference"] = ""
                record["adapter_exact_equal"] = ""
            rows.append(record)
    output = E5 / "results/02_risk_score/same_module_adapter_audit.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
