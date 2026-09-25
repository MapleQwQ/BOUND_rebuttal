#!/usr/bin/env python3
"""Paired first-token/full-sequence BOUND localization, editing and unseen evaluation."""
from __future__ import annotations

import argparse
import csv
import fcntl
import gc
import json
import os
import random
import shutil
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E6 = HERE.parent
ROOT = E6.parents[2]
sys.path.insert(0, str(ROOT))

import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer

from knowledgeEdit.package_edit import (
    baseline_for_prompt, edit_package_boundary, generate_recommendation_trials,
    load_baseline_response_index, load_model, summarize_eval_pairs, summarize_trials,
)
from knowledgeEdit.package_edit_utils import (
    BoundaryEditConfig, EditConfig, apply_chat_template, chat_message_ids,
    family_piece_ids, infer_model_cutoff, read_eval_questions, read_jsonl, recommendation_messages,
    select_modules_from_report, task_question_from_prompt, to_edit_config,
    write_json,
)

SOURCE = ROOT / "knowledgeEdit/results/robust_nonedit_highrisk_20260605"
MODELS = ("deepseekcoder", "qwen3-release", "llama3.1-release")
FOLDS = ("A", "B", "C", "D")
VARIANTS = ("first_token", "full_sequence")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log(message: str) -> None:
    line = f"- {stamp()} | {message}"
    with (E6 / "process_log.md").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def paths(model: str, fold: str, variant: str) -> tuple[Path, Path, Path]:
    old = SOURCE / model / f"fold_{fold}" / "blast_50"
    out = old if variant == "first_token" else E6 / "results" / model / f"fold_{fold}" / variant
    return old, out, out / "localization_report.json"


def make_config(model: str, fold: str, variant: str, gpu: int) -> BoundaryEditConfig:
    old, out, report = paths(model, fold, variant)
    src = json.loads((old / "experiment_config.json").read_text())
    fields = BoundaryEditConfig.__dataclass_fields__
    d = {k: v for k, v in src.items() if k in fields}
    d.update(
        edits_file=old / "selected_task_recommend_cases.jsonl",
        output_dir=out,
        experiment_dir=out,
        localization_report=str(report),
        gpu=str(gpu),
    )
    for k in ("model_path", "edits_file", "output_dir", "experiment_dir", "baseline_response_file", "unseen_file"):
        if d.get(k):
            d[k] = Path(d[k])
    return BoundaryEditConfig(**d)


def candidate_score(model, prefix: torch.Tensor, suffix: list[int]) -> torch.Tensor:
    """Mean conditional log P of every suffix token given the same chat prefix."""
    tail = torch.tensor(suffix, device=prefix.device, dtype=prefix.dtype).unsqueeze(0)
    ids = torch.cat((prefix, tail), dim=1)
    logits = model(input_ids=ids, use_cache=False).logits
    positions = logits[:, prefix.shape[1] - 1:-1, :].float()
    return positions.log_softmax(-1).gather(-1, tail.unsqueeze(-1)).squeeze(-1).mean()


def localize(cfg: BoundaryEditConfig, variant: str) -> None:
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = Path(cfg.localization_report)
    if report.exists():
        log(f"skip completed localization {out}")
        return
    os.environ["CUDA_VISIBLE_DEVICES"] = str(cfg.gpu)
    torch.cuda.set_device(0)
    start_load = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_path, device_map="cuda", torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model.eval()
    for p in model.parameters():
        p.requires_grad = False
    keys = [x.strip() for x in cfg.module_filter.split(",") if x.strip()]
    params = []
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear) and any(k in name for k in keys):
            module.weight.requires_grad = True
            params.append((name, module.weight))
    load_s = time.perf_counter() - start_load
    rows = [r for r in read_jsonl(Path(cfg.edits_file)) if r.get("type") == "task_recommend" and r.get("hallucinated")]
    random.Random(cfg.seed).shuffle(rows)
    if cfg.max_records > 0:
        rows = rows[:cfg.max_records]
    scores = {name: 0.0 for name, _ in params}
    counts = {name: 0 for name, _ in params}
    record_times = []
    log(f"localize start {out}: {len(rows)} records, {len(params)} modules, load {load_s:.1f}s")
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for ri, rec in enumerate(rows):
        one_t0 = time.perf_counter()
        language = rec.get("language", "Python")
        question = task_question_from_prompt(language, rec["prompt"])
        prefix, _ = chat_message_ids(tokenizer, recommendation_messages(language, question), None, "cuda")
        bad_names = list(rec.get("hallucinated", []))
        good_names = list(rec.get("valid_reference", []))
        if variant == "first_token":
            logits = model(input_ids=prefix, use_cache=False).logits[:, -1, :]
            bad_ids = []
            good_ids = []
            for pkg in bad_names:
                bad_ids.extend(tokenizer(" " + pkg, add_special_tokens=False).input_ids[:1])
            for pkg in good_names:
                good_ids.extend(tokenizer(" " + pkg, add_special_tokens=False).input_ids[:1])
            if not bad_ids:
                continue
            obj = logits[:, sorted(set(bad_ids))].logsumexp(-1).mean()
            if good_ids:
                obj = obj - cfg.anchor_penalty * logits[:, sorted(set(good_ids))].logsumexp(-1).mean()
            family_ids = family_piece_ids(tokenizer, bad_names)
            if family_ids and cfg.family_penalty > 0:
                obj = obj - cfg.family_penalty * logits[:, family_ids].logsumexp(-1).mean()
        else:
            # Two passes give the exact log-sum-exp gradient while bounding
            # activation memory independently of the candidate count.
            def sequences(names):
                seen = set()
                values = []
                for pkg in names:
                    suffix = tuple(tokenizer(" " + pkg, add_special_tokens=False).input_ids)
                    if suffix and suffix not in seen:
                        seen.add(suffix)
                        values.append(list(suffix))
                return values
            bad = sequences(bad_names)
            good = sequences(good_names)
            if not bad:
                continue
            if cfg.family_penalty > 0:
                raise ValueError("full-sequence family penalty requires separate definition")
            with torch.no_grad():
                bad_values = torch.stack([candidate_score(model, prefix, x) for x in bad])
                good_values = torch.stack([candidate_score(model, prefix, x) for x in good]) if good else None
            bad_coeff = bad_values.softmax(0).tolist()
            good_coeff = (-cfg.anchor_penalty * good_values.softmax(0)).tolist() if good else []
        model.zero_grad(set_to_none=True)
        if variant == "first_token":
            obj.backward()
        else:
            for suffix, coeff in list(zip(bad, bad_coeff)) + list(zip(good, good_coeff)):
                if coeff:
                    (candidate_score(model, prefix, suffix) * coeff).backward()
        for name, weight in params:
            if weight.grad is not None:
                val = (weight.grad.detach().float() * weight.detach().float()).abs().mean().item()
                scores[name] += val
                counts[name] += 1
        torch.cuda.synchronize()
        record_times.append(time.perf_counter() - one_t0)
        if (ri + 1) % 10 == 0 or ri + 1 == len(rows):
            log(f"localize progress {out}: {ri+1}/{len(rows)}; latest 10 mean {sum(record_times[-10:])/len(record_times[-10:]):.1f}s/record")
    localization_s = time.perf_counter() - t0
    ranking = sorted((dict(module=n, score=scores[n] / max(counts[n], 1), count=counts[n]) for n in scores), key=lambda r: (-r["score"], r["module"]))
    write_json(report, dict(method=variant, n_records=len(rows), anchor_penalty=cfg.anchor_penalty,
                            family_penalty=cfg.family_penalty, layer_scores=ranking,
                            model_load_seconds=load_s, localization_seconds=localization_s,
                            record_seconds=record_times, candidate_prefix="leading ASCII space",
                            full_sequence_normalization="arithmetic mean token log-probability" if variant == "full_sequence" else None))
    log(f"localize done {out}: {localization_s:.1f}s; top5 {[r['module'] for r in ranking[:5]]}")
    del model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()


def edit_and_eval(cfg: BoundaryEditConfig, variant: str) -> None:
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    old = SOURCE / out.relative_to(E6 / "results").parts[0] / out.relative_to(E6 / "results").parts[1] / "blast_50"
    historical_edit = json.loads((old / "blast_config.json").read_text())
    effective_edit_seed = int(historical_edit["seed"])
    config_path = out / "experiment_config.json"
    if not config_path.exists():
        write_json(config_path, {k: str(v) if isinstance(v, Path) else v for k, v in asdict(cfg).items()} | {"localization_variant": variant, "effective_edit_seed": effective_edit_seed})
    if not (out / "blast_delta.pt").exists():
        log(f"edit start {out}")
        t0 = time.perf_counter()
        edit_cfg = to_edit_config(cfg)
        edit_cfg.seed = effective_edit_seed
        model, tokenizer = edit_package_boundary(edit_cfg)
        log(f"edit done {out}: {time.perf_counter()-t0:.1f}s")
    else:
        model = tokenizer = None
    old_delta = old / "blast_delta.pt"
    old_unseen = old / "eval_unseen_prompts.json"
    new_unseen = out / "eval_unseen_prompts.json"
    if not new_unseen.exists() and old_delta.exists() and old_unseen.exists():
        new_state = torch.load(out / "blast_delta.pt", map_location="cpu", weights_only=True)
        old_state = torch.load(old_delta, map_location="cpu", weights_only=True)
        identical = set(new_state) == set(old_state) and all(torch.equal(new_state[k], old_state[k]) for k in old_state)
        del new_state, old_state
        if identical:
            shutil.copy2(old_unseen, new_unseen)
            write_json(out / "unseen_reuse_provenance.json", {
                "source": str(old_unseen),
                "reason": "bitwise-identical LoRA tensor keys and values after full-sequence edit; same base model and evaluation inputs",
                "verification": "torch.equal for every adapter tensor",
            })
            log(f"unseen eval reused after bitwise adapter equality {out}")
        else:
            log(f"adapter differs from historical first-token edit; generate unseen responses {out}")
    if not (out / "eval_unseen_prompts.json").exists():
        log(f"unseen eval start {out}")
        t0 = time.perf_counter()
        evaluate_unseen_resume(cfg, model, tokenizer)
        log(f"unseen eval done {out}: {time.perf_counter()-t0:.1f}s")
    else:
        log(f"skip completed unseen eval {out}")


def evaluate_unseen_resume(cfg: BoundaryEditConfig, model, tokenizer) -> None:
    """Same unseen schema and metrics as the original evaluator, with per-prompt checkpoints."""
    out = Path(cfg.output_dir)
    progress = out / "unseen_progress.jsonl"
    questions = read_eval_questions(Path(cfg.unseen_file), 0, cfg.eval_unseen_max_samples)
    completed = [json.loads(line) for line in progress.read_text().splitlines() if line.strip()] if progress.exists() else []
    if len(completed) > len(questions):
        raise ValueError(f"checkpoint contains too many prompts: {progress}")
    for i, row in enumerate(completed):
        if row["id"] != questions[i][0] or row["question"] != questions[i][1]:
            raise ValueError(f"checkpoint prompt mismatch at {i}: {progress}")
    if model is None or tokenizer is None:
        model, tokenizer = load_model(Path(cfg.model_path), out)
    model.eval()
    baseline = load_baseline_response_index(cfg.baseline_response_file)
    cutoff = infer_model_cutoff(cfg.model_path, cfg.eval_model_cutoff)
    release_cache = {}
    for i in range(len(completed), len(questions)):
        prompt_id, question = questions[i]
        seeds = [cfg.seed + i * cfg.eval_num_generations + j for j in range(cfg.eval_num_generations)]
        trials = generate_recommendation_trials(
            model, tokenizer, question, "Python", cutoff, release_cache,
            num_generations=cfg.eval_num_generations, max_new_tokens=cfg.eval_max_new_tokens,
            temperature=cfg.eval_temperature, top_k=cfg.eval_top_k, top_p=cfg.eval_top_p,
            generation_seeds=seeds,
        )
        row = {"id": prompt_id, "question": question,
               "baseline": baseline_for_prompt(baseline, prompt_id, question),
               "edited": {"summary": summarize_trials(trials), "trials": trials}}
        with progress.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        completed.append(row)
        if (i + 1) % 50 == 0 or i + 1 == len(questions):
            log(f"unseen eval progress {out}: {i+1}/{len(questions)}")
    write_json(out / "eval_unseen_prompts.json", {"summary": summarize_eval_pairs(completed), "details": completed})


def summarize() -> None:
    from scipy.stats import spearmanr
    rows = []
    for model in MODELS:
        for fold in FOLDS:
            reports = []
            for variant in VARIANTS:
                _, out, report = paths(model, fold, variant)
                if not (report.exists() and (out / "eval_unseen_prompts.json").exists()):
                    reports = []
                    break
                reports.append((json.loads(report.read_text()), json.loads((out / "eval_unseen_prompts.json").read_text())))
            if not reports:
                continue
            rankings = [z[0]["layer_scores"] for z in reports]
            ranks = [{r["module"]: r["score"] for r in rank} for rank in rankings]
            if not set(ranks[0]).issubset(set(ranks[1])):
                raise ValueError(f"old top-200 modules missing from full-sequence: {model} fold {fold}")
            top_sets = [{r["module"] for r in rank[:5]} for rank in rankings]
            overlap = len(top_sets[0] & top_sets[1]) / 5
            names = list(ranks[0])
            top200_rho = float(spearmanr([ranks[0][n] for n in names], [ranks[1][n] for n in names]).statistic)
            # Scores for legacy ranks >200 were never saved. Rank 201 is a
            # right-censoring tie, not a reconstructed exact rank.
            all_names = list(ranks[1])
            old_censored = {r["module"]: i + 1 for i, r in enumerate(rankings[0])}
            censored_rho = float(spearmanr([-old_censored.get(n, 201) for n in all_names],
                                           [ranks[1][n] for n in all_names]).statistic)
            selected = []
            for variant in VARIANTS:
                old, out, report = paths(model, fold, variant)
                conf = json.loads((old / "experiment_config.json").read_text())
                selected.append(set(select_modules_from_report(report, conf["localization_top_k"], conf["localization_mode"], conf["localization_window"]).split(",")))
            edit_overlap = len(selected[0] & selected[1]) / max(len(selected[0] | selected[1]), 1)
            for variant, (loc, ev) in zip(VARIANTS, reports):
                s = ev["summary"]
                if variant == "first_token":
                    old, _, _ = paths(model, fold, variant)
                    old_timing = json.loads((old / "timing.json").read_text())
                    loc_seconds = old_timing["localization"]["elapsed_sec"]
                    load_seconds = ""
                    timing_scope = "historical subprocess including startup and model load"
                else:
                    loc_seconds = loc["localization_seconds"]
                    load_seconds = loc["model_load_seconds"]
                    timing_scope = "new pure scoring; model load shown separately"
                rows.append(dict(model=model, fold=fold, variant=variant, top5_overlap=overlap,
                                 old_top200_spearman=top200_rho, right_censored_all_module_spearman=censored_rho,
                                 exact_full_rank_spearman="unavailable: legacy report truncated at 200",
                                 localization_seconds=loc_seconds, model_load_seconds=load_seconds,
                                 timing_scope=timing_scope,
                                 selected_module_count=len(selected[VARIANTS.index(variant)]),
                                 selected_module_jaccard=edit_overlap,
                                 zero_score_module_count=sum(r["score"] == 0 for r in loc["layer_scores"]) if variant == "full_sequence" else "unknown beyond top 200",
                                 n_unseen=s["n_prompts"], sample_hr=s["edited_sample_hallucination_rate"],
                                 package_hr=s["edited_package_hallucination_rate"],
                                 valid_rate=s["edited_sample_valid_rate"],
                                 base_sample_hr=s["baseline_sample_hallucination_rate"],
                                 base_package_hr=s["baseline_package_hallucination_rate"],
                                 base_valid_rate=s["baseline_sample_valid_rate"]))
    dest = E6 / "results/localization_variant_results.csv"
    dest.parent.mkdir(exist_ok=True)
    if rows:
        with (dest.parent / ".summary.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            temp = dest.with_suffix(".csv.tmp")
            with temp.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            temp.replace(dest)
    log(f"summary updated: {len(rows)//2}/12 complete pairs")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=MODELS)
    p.add_argument("--fold", choices=FOLDS)
    p.add_argument("--variant", choices=("full_sequence",))
    p.add_argument("--gpu", type=int)
    p.add_argument("--stage", choices=("localize", "edit_eval", "all", "summarize"), default="all")
    a = p.parse_args()
    if a.stage == "summarize":
        summarize()
        return
    if a.model is None or a.fold is None or a.variant is None or a.gpu is None:
        p.error("model, fold, variant and gpu are required")
    # Set this even when localization/editing are skipped on resume.
    os.environ["CUDA_VISIBLE_DEVICES"] = str(a.gpu)
    cfg = make_config(a.model, a.fold, a.variant, a.gpu)
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
    with (Path(cfg.output_dir) / ".run.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if a.stage in ("all", "localize"):
            localize(cfg, a.variant)
        if a.stage in ("all", "edit_eval"):
            edit_and_eval(cfg, a.variant)


if __name__ == "__main__":
    main()
