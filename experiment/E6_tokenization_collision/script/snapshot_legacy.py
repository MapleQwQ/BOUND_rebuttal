#!/usr/bin/env python3
"""Copy the reused first-token result artifacts into the self-contained E6 tree."""
import hashlib
import json
import shutil
from pathlib import Path

E6 = Path(__file__).resolve().parent.parent
ROOT = E6.parents[2]
SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
FILES = (
    "localization_report.json", "timing.json", "eval_unseen_prompts.json",
    "blast_delta.pt", "blast_config.json", "experiment_config.json",
    "selected_task_recommend_cases.jsonl",
)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = []
    for model in ("deepseekcoder", "qwen3-release", "llama3.1-release"):
        for fold in "ABCD":
            source = SOURCE / model / f"fold_{fold}" / "blast_50"
            target = E6 / "results" / model / f"fold_{fold}" / "first_token"
            target.mkdir(parents=True, exist_ok=True)
            hashes = {}
            for name in FILES:
                shutil.copy2(source / name, target / name)
                digest = sha(source / name)
                assert sha(target / name) == digest
                hashes[name] = digest
            manifest.append({"model": model, "fold": fold, "source": str(source), "files_sha256": hashes})
    out = E6 / "results/first_token_snapshot_manifest.json"
    out.write_text(json.dumps({"n_folds": len(manifest), "runs": manifest}, ensure_ascii=False, indent=2))
    print(f"snapshotted {len(manifest)} first-token runs -> {out}")


if __name__ == "__main__":
    main()
