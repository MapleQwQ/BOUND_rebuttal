"""BOUND method implementation for the replication package.

This module covers package parsing, PyPI validation, module localization,
localized LoRA editing, and package-recommendation evaluation.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import requests
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Constants and package-recommendation prompt

MODEL_CUTOFFS = {
    "deepseekcoder": dt.datetime(2023, 10, 29),
    "qwen3": dt.datetime(2025, 4, 29),
    "llama3.1": dt.datetime(2023, 12, 31),
    "llama-3.1": dt.datetime(2023, 12, 31),
}
REQUEST_RETRIES = 3
REQUEST_TIMEOUT = 10
ANSWER_PATTERN = re.compile(r"\[ANSWER\](.*?)\[/ANSWER\]", re.DOTALL | re.IGNORECASE)

PACKAGE_RECOMMEND_SYSTEM = """You are a coding assistant that recommends Python packages for programming tasks.
Return only package names, comma separated, inside [ANSWER] and [/ANSWER] tags, no additional text or formatting.
If no third-party Python package is needed, return only "None" inside the tags.
Example:
[TASK]
Generate Python code that loads a CSV file, analyzes it with a dataframe, and plots a histogram.
[/TASK]
[ANSWER]
pandas, matplotlib
[/ANSWER]
"""

try:
    STD_LIBRARY_MODULES = set(sys.stdlib_module_names)
except AttributeError:
    STD_LIBRARY_MODULES = set()
STD_LIBRARY_MODULES |= set(sys.builtin_module_names)
STD_CHECK_CACHE: dict[str, bool] = {}


# Package parsing and PyPI validation

def normalize(name: str, language: str) -> str:
    """Normalize package names for de-duplication and PyPI lookup."""
    name = "" if name is None else str(name)
    name = re.sub(r"\d+\.\s*", "", name)
    name = re.sub(r"[`'\"()\[\]]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    if language == "Python":
        if "." in name and "-" not in name and "_" not in name:
            name = name.split(".", 1)[0]
        return re.sub(r"[-_.]+", "-", name).strip(" `.-").lower()
    return name.strip(" `.-").lower()


def split_packages(text: str, language: str) -> list[str]:
    """Extract package candidates from a package-recommendation answer."""
    raw = "" if text is None else str(text)
    matches = ANSWER_PATTERN.findall(raw)
    if matches:
        raw = matches[0].strip()
    elif re.search(r"\[ANSWER\]", raw, flags=re.I):
        raw = re.split(r"\[ANSWER\]", raw, flags=re.I, maxsplit=1)[1].strip()
        raw = raw.split("\n\n", 1)[0].strip()
    if raw.lower().lstrip().startswith("none"):
        return []

    candidates: list[str] = []

    def add_parts(value: str) -> None:
        value = str(value).strip()
        if not value:
            return
        value = value.replace("\\n", "\n")
        for part in re.split(r"[,，\n]+", value):
            part = part.strip()
            if not part:
                continue
            if " " in part and not re.match(r"^[A-Za-z0-9_.@/-]+$", part):
                continue
            candidates.extend(x for x in re.split(r"\s+", part) if x)

    def add_install_args(value: str) -> None:
        if language == "Python":
            matches = re.findall(r"\b(?:python\s+-m\s+)?pip(?:3)?\s+install\s+([^\n#;&|]+)", value, flags=re.I)
        else:
            matches = re.findall(r"\bnpm\s+install\s+([^\n#;&|]+)", value, flags=re.I)
        for match in matches:
            add_parts(match)

    add_install_args(raw)
    for block in re.findall(r"```(?:[A-Za-z0-9_-]+)?\s*(.*?)```", raw, flags=re.DOTALL):
        add_install_args(block)

    text_only = re.sub(r"```.*?```", " ", raw, flags=re.DOTALL)
    text_only = re.sub(r"```.*", " ", text_only, flags=re.DOTALL)
    for span in re.findall(r"`([^`\n]{1,160})`", text_only):
        add_parts(span)
    for quoted in re.findall(r"['\"]([^'\"\n]{1,200})['\"]", text_only):
        add_parts(quoted)
    for line in text_only.splitlines():
        clean = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line.strip())
        if clean and ("," in clean or re.fullmatch(r"[A-Za-z0-9_.@/\-\s]+", clean)):
            add_parts(clean)

    stop = {
        "and", "or", "the", "a", "an", "package", "module", "library", "python", "javascript", "node", "none",
        "bash", "shell", "python3", "pip", "pip3", "install", "built-in", "builtin", "standard", "stdlib",
        "class", "def", "from", "import", "as", "true", "false", "null", "to", "in", "for", "of", "on", "by",
        "you", "your", "we", "can", "will", "should",
    }
    pkgs = []
    for cand in candidates:
        pkg = normalize(cand, language)
        pkg = re.sub(r"^(?:pip|npm)\s+install\s+", "", pkg, flags=re.I)
        pkg = pkg.strip(" ,;:。")
        if (
            pkg
            and pkg not in stop
            and 1 < len(pkg) <= 80
            and len(pkg.split()) == 1
            and not pkg.isdigit()
            and "," not in pkg
            and re.fullmatch(r"@?[a-z0-9][a-z0-9_.@/-]*", pkg)
        ):
            pkgs.append(pkg)
    return sorted(set(pkgs))


def infer_model_cutoff(model_path: str, explicit_cutoff: str = "") -> dt.datetime | None:
    """Infer the model release/cutoff date from config, or use an explicit date."""
    if explicit_cutoff:
        return dt.datetime.fromisoformat(explicit_cutoff)
    lower = str(model_path).lower()
    for key, cutoff in MODEL_CUTOFFS.items():
        if key in lower:
            return cutoff
    return None


def clean_extracted_package_name(name: str | None) -> str:
    """Clean pip options, extras, and version constraints from a package name."""
    if not isinstance(name, str):
        return ""
    pkg = name.strip().lower().strip(",;")
    skip = {
        "--upgrade", "-u", "-e", "--cert", "--trusted-host", "--extra-index-url", "-r",
        "requirements.txt", "requirements", "pip", "install", ".", "",
    }
    if not pkg or pkg in skip:
        return ""
    if "[" in pkg:
        pkg = pkg.split("[", 1)[0]
    if "=" in pkg:
        pkg = pkg.split("=", 1)[0]
    return pkg.strip(" \t\r\n`'\".,:;)")


def check_std_package(package_name: str) -> bool:
    """Return whether a Python package candidate is a standard-library module."""
    if not package_name:
        return False
    if package_name in STD_CHECK_CACHE:
        return STD_CHECK_CACHE[package_name]
    STD_CHECK_CACHE[package_name] = package_name in STD_LIBRARY_MODULES
    return STD_CHECK_CACHE[package_name]


def fetch_first_release_date(package_name: str) -> dt.datetime | None:
    """Query PyPI for the first release timestamp of a package."""
    if not package_name:
        return None
    url = f"https://pypi.org/pypi/{package_name}/json"
    for _ in range(REQUEST_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        try:
            data = response.json()
        except ValueError:
            return None
        timestamps = []
        for details in data.get("releases", {}).values():
            if not details:
                continue
            upload_time = details[0].get("upload_time")
            if not upload_time:
                continue
            try:
                timestamps.append(dt.datetime.fromisoformat(upload_time.replace("Z", "+00:00")).replace(tzinfo=None))
            except ValueError:
                continue
        return min(timestamps) if timestamps else None
    return None


def fetch_first_pypi_release(package_name: str, release_cache: dict) -> dt.datetime | None:
    """Query PyPI with a caller-provided cache."""
    if package_name in release_cache:
        return release_cache[package_name]
    release_time = fetch_first_release_date(package_name)
    release_cache[package_name] = release_time
    return release_time


def classify_packages_by_pypi(
    packages: Iterable[str],
    *,
    language: str = "Python",
    cutoff: dt.datetime | None,
    release_cache: dict,
) -> tuple[list[str], list[str]]:
    """Classify package candidates as valid or hallucinated using PyPI release time."""
    if language != "Python":
        raise ValueError("BOUND replication package supports Python package hallucination evaluation.")
    valid, hall, seen = [], [], set()
    for raw_pkg in packages:
        pkg = clean_extracted_package_name(normalize(raw_pkg, language))
        if not pkg or pkg in seen:
            continue
        seen.add(pkg)
        if check_std_package(pkg):
            continue
        release_time = fetch_first_pypi_release(pkg, release_cache)
        if release_time is not None and (cutoff is None or release_time <= cutoff):
            valid.append(pkg)
        else:
            hall.append(pkg)
    return sorted(valid), sorted(hall)


def question_prompt(language: str, question: str) -> str:
    """Build the package-recommendation prompt for a coding task."""
    return f"What {language} packages would be useful in solving the following coding problem: {question.strip()}"


# Environment, IO, and chat-template helpers

def set_gpu(gpu: str) -> None:
    """Set CUDA_VISIBLE_DEVICES from an explicit config value."""
    gpu = str(gpu).strip()
    if gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file and skip blank lines."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write JSONL rows with UTF-8 text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict) -> None:
    """Write a JSON file with UTF-8 text and readable indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config_file(path: str | Path | None) -> dict[str, Any]:
    """Load a BOUND YAML config or a JSON config file."""
    if not path:
        return {}
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(cfg_path)
    text = cfg_path.read_text(encoding="utf-8")
    if cfg_path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("YAML config requires PyYAML; use JSON or install pyyaml.") from exc
    data = yaml.safe_load(text)
    return data or {}


def apply_chat_template(tokenizer, messages: list[dict], *, add_generation_prompt: bool, return_tensors: str):
    """Apply a chat template while disabling Qwen3 thinking when supported."""
    try:
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=add_generation_prompt,
            return_tensors=return_tensors,
            enable_thinking=False,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=add_generation_prompt,
            return_tensors=return_tensors,
        )


def chat_message_ids(tokenizer, messages: list[dict], target: str | None, device: str):
    """Encode chat messages for generation or supervised assistant-token loss."""
    if target is None:
        encoded = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt")
        ids = encoded["input_ids"] if hasattr(encoded, "keys") and "input_ids" in encoded else encoded
        return ids.to(device), None
    encoded_prefix = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt")
    prefix = encoded_prefix["input_ids"] if hasattr(encoded_prefix, "keys") and "input_ids" in encoded_prefix else encoded_prefix
    suffix = tokenizer(target, add_special_tokens=False, return_tensors="pt").input_ids
    input_ids = torch.cat([prefix, suffix], dim=1).to(device)
    labels = torch.full_like(input_ids, -100)
    labels[:, prefix.shape[1] :] = suffix.to(device)
    return input_ids, labels


def chat_ids(tokenizer, prompt: str, target: str | None, device: str):
    """Encode a plain user prompt using the model chat template."""
    return chat_message_ids(tokenizer, [{"role": "user", "content": prompt}], target, device)


# LoRA injection and module selection

class LoRALinear(nn.Module):
    """Small LoRA wrapper used by the package boundary editor."""

    def __init__(self, base: nn.Linear, rank: int, alpha: float, dropout: float):
        super().__init__()
        self.base = base
        self.rank = rank
        self.scale = alpha / rank
        self.drop = nn.Dropout(dropout)
        self.A = nn.Parameter(torch.zeros(rank, base.in_features, dtype=base.weight.dtype, device=base.weight.device))
        self.B = nn.Parameter(torch.zeros(base.out_features, rank, dtype=base.weight.dtype, device=base.weight.device))
        nn.init.kaiming_uniform_(self.A, a=5**0.5)
        nn.init.zeros_(self.B)
        self.enabled = True
        for p in self.base.parameters():
            p.requires_grad = False

    def forward(self, x):
        if not self.enabled:
            return self.base(x)
        return self.base(x) + F.linear(F.linear(self.drop(x), self.A), self.B) * self.scale


def find_parent(model, module_name: str):
    """Return the parent module and child attribute name for a dotted module path."""
    parent = model
    parts = module_name.split(".")
    for part in parts[:-1]:
        parent = getattr(parent, part)
    return parent, parts[-1]


def inject_lora(model, target_keywords: list[str], rank: int, alpha: float, dropout: float) -> list[str]:
    """Inject LoRA into linear modules whose names contain any target keyword."""
    names = [n for n, m in model.named_modules() if isinstance(m, nn.Linear)]
    edited = []
    for name in names:
        if not any(k in name for k in target_keywords):
            continue
        parent, child = find_parent(model, name)
        setattr(parent, child, LoRALinear(getattr(parent, child), rank, alpha, dropout))
        edited.append(name)
    return edited


def lora_state(model) -> dict:
    """Export only LoRA A/B parameters."""
    return {k: v.detach().cpu() for k, v in model.state_dict().items() if ".A" in k or ".B" in k}


def set_lora_enabled(model, enabled: bool) -> None:
    """Enable or disable every LoRA branch in a model."""
    for module in model.modules():
        if isinstance(module, LoRALinear):
            module.enabled = enabled


def module_family(name: str) -> str:
    """Map a module name to a projection family."""
    for key in ["gate_proj", "up_proj", "down_proj", "q_proj", "k_proj", "v_proj", "o_proj"]:
        if key in name:
            return key
    return name.split(".")[-1]


def parse_layer_module(name: str) -> tuple[int | None, str]:
    """Parse `(layer_id, projection_family)` from a transformer module path."""
    m = re.search(r"model\.layers\.(\d+)\.", name)
    return (int(m.group(1)) if m else None), module_family(name)


def select_modules_from_report(report_file: Path, top_k: int, mode: str, window: int = 1) -> str:
    """Select edit modules from a localization report."""
    report = json.loads(report_file.read_text(encoding="utf-8"))
    rows = report["layer_scores"][:top_k]
    if mode == "exact":
        return ",".join(row["module"] for row in rows)
    if mode != "window_family":
        raise ValueError(f"unsupported localization mode for main experiments: {mode}")

    all_rows = report["layer_scores"]
    centers: list[int] = []
    families: list[str] = []
    for row in rows:
        layer, fam = parse_layer_module(row["module"])
        if layer is not None and layer not in centers:
            centers.append(layer)
        if fam not in families:
            families.append(fam)
    out, seen = [], set()
    for row in all_rows:
        layer, fam = parse_layer_module(row["module"])
        if layer is None or fam not in families:
            continue
        if any(abs(layer - center) <= window for center in centers) and row["module"] not in seen:
            seen.add(row["module"])
            out.append(row["module"])
    return ",".join(out)


def task_question_from_prompt(language: str, prompt: str) -> str:
    """Strip the package recommendation prefix from an edit record prompt."""
    prefix = question_prompt(language, "")
    if prompt.startswith(prefix):
        return prompt[len(prefix) :].strip()
    return prompt.strip()


# Package-recommendation chat prompt builder

def recommendation_messages(language: str, question: str) -> list[dict]:
    """Build the package recommendation chat prompt used by train/eval/localize."""
    system = PACKAGE_RECOMMEND_SYSTEM.replace("Python", language)
    prompt = f"[TASK]\n{question_prompt(language, question)}\n[/TASK]"
    return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]


def package_family_pieces(pkg: str) -> list[str]:
    """Extract ecosystem/family pieces from a package name for localization analysis."""
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(pkg or "").lower()).strip("-_.")
    pieces = [x for x in re.split(r"[-_.]+", text) if len(x) > 1]
    stop = {
        "core", "helper", "utils", "util", "python", "python3", "py", "js", "lib", "api", "sdk",
        "client", "server", "plugin", "plugins", "adapter", "wrapper",
    }
    return sorted({p for p in pieces if p not in stop and not p.isdigit()})


def family_piece_ids(tokenizer, packages: list[str]) -> list[int]:
    """Convert package family pieces to first-token ids."""
    ids: list[int] = []
    for pkg in packages:
        for piece in package_family_pieces(pkg):
            for text in (piece, " " + piece):
                enc = tokenizer(text, add_special_tokens=False).input_ids
                if enc:
                    ids.append(enc[0])
                    break
    return sorted(set(ids))


# Dataset readers and experiment configuration

def read_eval_questions(path: Path, start: int, max_samples: int) -> list[tuple[int, str]]:
    """Read unseen tasks from JSONL high-risk files."""

    def parse_id(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    with path.open(encoding="utf-8") as f:
        first = f.readline().strip()
    if not first.startswith("{"):
        raise ValueError(f"expected JSONL unseen prompt file: {path}")
    rows = []
    with path.open(encoding="utf-8") as f:
        for offset, line in enumerate(f):
            if not line.strip():
                continue
            row = json.loads(line)
            question = row.get("question")
            if question is not None:
                rows.append((parse_id(row.get("id"), offset), str(question)))
    end = start + max_samples if max_samples > 0 else None
    return rows[start:end]


@dataclass
class EditConfig:
    """Configuration for BOUND/SFT package-boundary editing."""

    model_path: Path
    edits_file: Path
    output_dir: Path
    method: str = "bound"
    gpu: str = "0"
    seed: int = 42
    max_edits: int = 2000
    epochs: int = 1
    batch_size: int = 1
    lr: float = 2e-4
    rank: int = 8
    alpha: float = 16.0
    dropout: float = 0.05
    target_modules: str = ""
    localization_report: str = ""
    localization_top_k: int = 16
    localization_mode: str = "exact"
    localization_window: int = 1
    task_weight: float = 1.0
    answer_neg_weight: float = 0.25
    kl_weight: float = 0.03
    max_task_packages: int = 5


@dataclass
class LocalizationConfig:
    """Configuration for package-boundary module localization."""

    model_path: Path
    edits_file: Path
    out_file: Path
    gpu: str = "0"
    max_records: int = 128
    seed: int = 42
    anchor_penalty: float = 0.5
    family_penalty: float = 0.0
    module_filter: str = "gate_proj,up_proj,down_proj,q_proj,k_proj,v_proj,o_proj"


@dataclass
class BoundaryEditConfig:
    """Single model-level config for localization followed by BOUND/SFT editing."""

    model_path: Path
    edits_file: Path
    output_dir: Path | str = ""
    localization_report: str = ""
    experiment_dir: Path | str = ""
    edit_case_count: int = 0
    edit_case_strategy: str = "first"
    edit_case_seed: int = 42
    method: str = "bound"
    gpu: str = "0"
    seed: int = 42
    max_records: int = 128
    anchor_penalty: float = 0.5
    family_penalty: float = 0.0
    module_filter: str = "gate_proj,up_proj,down_proj,q_proj,k_proj,v_proj,o_proj"
    max_edits: int = 2000
    epochs: int = 1
    batch_size: int = 1
    lr: float = 2e-4
    rank: int = 8
    alpha: float = 16.0
    dropout: float = 0.05
    target_modules: str = ""
    localization_top_k: int = 16
    localization_mode: str = "exact"
    localization_window: int = 1
    task_weight: float = 1.0
    answer_neg_weight: float = 0.25
    kl_weight: float = 0.03
    sft_optimizer: str = "adamw"
    max_task_packages: int = 5
    auto_eval: bool = True
    reference_response_file: Path | str = ""
    unseen_file: Path | str = ""
    eval_edit_max_samples: int = 0
    eval_unseen_max_samples: int = 100
    eval_num_generations: int = 1
    eval_max_new_tokens: int = 128
    eval_temperature: float = 0.7
    eval_top_k: int = 40
    eval_top_p: float = 0.9
    eval_model_cutoff: str = ""


def _case_group_id(row: dict) -> str:
    """Return a stable prompt-level id for task_recommend edit cases."""
    row_id = str(row.get("id", ""))
    parts = row_id.split("-")
    for idx, part in enumerate(parts):
        if part.isdigit():
            return "-".join(parts[: idx + 1])
    return row_id or str(row.get("prompt", ""))


def _serialize_config(cfg: BoundaryEditConfig) -> dict[str, Any]:
    """Convert a BoundaryEditConfig to JSON-serializable values."""
    payload = dataclasses.asdict(cfg)
    for key, value in list(payload.items()):
        if isinstance(value, Path):
            payload[key] = str(value)
    return payload


def prepare_boundary_experiment(cfg: BoundaryEditConfig) -> BoundaryEditConfig:
    """Prepare a self-contained experiment directory and selected edit cases.

    The source edits file can contain mixed edit records. The main BOUND
    experiment uses only prompt-level `task_recommend` cases. This function
    filters those cases, optionally keeps the configured number of prompts, and
    rewrites the config so localization and editing read/write inside one
    experiment directory.
    """
    source_edits_file = Path(cfg.edits_file)
    if not cfg.experiment_dir and not cfg.output_dir:
        raise ValueError("experiment_dir is required when output_dir is not specified")
    experiment_dir = Path(cfg.experiment_dir) if cfg.experiment_dir else Path(cfg.output_dir)
    experiment_dir.mkdir(parents=True, exist_ok=True)

    rows = [row for row in read_jsonl(source_edits_file) if row.get("type") == "task_recommend"]
    prompt_cases = []
    seen = set()
    for row in rows:
        key = _case_group_id(row)
        if key in seen:
            continue
        seen.add(key)
        prompt_cases.append(row)

    if cfg.edit_case_strategy == "random":
        prompt_cases = list(prompt_cases)
        random.Random(cfg.edit_case_seed).shuffle(prompt_cases)
    elif cfg.edit_case_strategy != "first":
        raise ValueError(f"unsupported edit_case_strategy: {cfg.edit_case_strategy}")

    requested = int(cfg.edit_case_count)
    selected = prompt_cases[:requested] if requested > 0 else prompt_cases
    if requested > 0 and len(selected) < requested:
        print(f"warning: requested {requested} edit cases, but only {len(selected)} task_recommend cases exist")

    selected_file = experiment_dir / "selected_task_recommend_cases.jsonl"
    write_jsonl(selected_file, selected)

    cfg.experiment_dir = experiment_dir
    cfg.edits_file = selected_file
    cfg.output_dir = experiment_dir
    cfg.localization_report = str(experiment_dir / "localization_report.json")

    write_json(
        experiment_dir / "experiment_config.json",
        _serialize_config(cfg)
        | {
            "source_edits_file": str(source_edits_file),
            "n_task_recommend_source_cases": len(prompt_cases),
            "n_selected_edit_cases": len(selected),
            "selected_cases_file": str(selected_file),
        },
    )
    return cfg


def to_edit_config(cfg: BoundaryEditConfig) -> EditConfig:
    """Extract edit-stage fields from the single model config."""
    return EditConfig(
        model_path=cfg.model_path,
        edits_file=cfg.edits_file,
        output_dir=cfg.output_dir,
        method=cfg.method,
        gpu=cfg.gpu,
        seed=cfg.seed,
        max_edits=cfg.max_edits,
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        lr=cfg.lr,
        rank=cfg.rank,
        alpha=cfg.alpha,
        dropout=cfg.dropout,
        target_modules=cfg.target_modules,
        localization_report=cfg.localization_report,
        localization_top_k=cfg.localization_top_k,
        localization_mode=cfg.localization_mode,
        localization_window=cfg.localization_window,
        task_weight=cfg.task_weight,
        answer_neg_weight=cfg.answer_neg_weight,
        kl_weight=cfg.kl_weight,
        max_task_packages=cfg.max_task_packages,
    )


def to_localization_config(cfg: BoundaryEditConfig) -> LocalizationConfig:
    """Extract localization-stage fields from the single model config."""
    return LocalizationConfig(
        model_path=cfg.model_path,
        edits_file=cfg.edits_file,
        out_file=Path(cfg.localization_report),
        gpu=cfg.gpu,
        max_records=cfg.max_records,
        seed=cfg.seed,
        anchor_penalty=cfg.anchor_penalty,
        family_penalty=cfg.family_penalty,
        module_filter=cfg.module_filter,
    )


# Boundary-editing losses and training

def resolve_target_modules(cfg: EditConfig) -> str:
    """Resolve explicit or localization-report-based edit module selection."""
    if cfg.localization_report:
        target_modules = select_modules_from_report(
            Path(cfg.localization_report),
            int(cfg.localization_top_k),
            cfg.localization_mode,
            window=int(cfg.localization_window),
        )
        print(f"localized target modules: {target_modules}")
        return target_modules
    return cfg.target_modules


def continuation_unlikelihood(model, tokenizer, messages: list[dict], prefix_text: str, bad_text: str, device: str):
    """Apply unlikelihood loss to a bad package continuation after a fixed answer prefix."""
    bad_ids = tokenizer(bad_text, add_special_tokens=False, return_tensors="pt").input_ids
    if bad_ids.numel() == 0:
        return torch.tensor(0.0, device=device)
    encoded_prefix = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt")
    chat_prefix = (
        encoded_prefix["input_ids"]
        if hasattr(encoded_prefix, "keys") and "input_ids" in encoded_prefix
        else encoded_prefix
    )
    prefix_ids = tokenizer(prefix_text, add_special_tokens=False, return_tensors="pt").input_ids
    input_ids = torch.cat([chat_prefix, prefix_ids, bad_ids], dim=1).to(device)
    labels = torch.full_like(input_ids, -100)
    labels[:, -bad_ids.shape[1] :] = bad_ids.to(device)
    logits = model(input_ids=input_ids).logits[:, :-1, :]
    labels = labels[:, 1:]
    mask = labels.ne(-100)
    if not mask.any():
        return torch.tensor(0.0, device=device)
    logp = logits.log_softmax(dim=-1).gather(-1, labels.clamp_min(0).unsqueeze(-1)).squeeze(-1)
    seq_p = ((logp * mask).sum() / mask.sum()).exp()
    return -torch.log(torch.clamp(1.0 - seq_p, min=1e-6))


def kl_to_base(model, tokenizer, prompt: str, device: str):
    """Compute next-token KL between LoRA-disabled and LoRA-enabled model states."""
    ids, _ = chat_ids(tokenizer, prompt, None, device)
    with torch.no_grad():
        set_lora_enabled(model, False)
        base = model(input_ids=ids).logits[:, -1, :].softmax(dim=-1)
        set_lora_enabled(model, True)
    cur = model(input_ids=ids).logits[:, -1, :].log_softmax(dim=-1)
    return F.kl_div(cur, base, reduction="batchmean")


def train_context(tokenizer, rec: dict, target: str | None, device: str):
    """Build a task_recommend context and supervise only assistant target tokens."""
    language = rec.get("language", "Python")
    question = task_question_from_prompt(language, rec["prompt"])
    return chat_message_ids(tokenizer, recommendation_messages(language, question), target, device)


def format_task_target(target: str) -> str:
    """Wrap valid packages in the answer format used for training."""
    return f"[ANSWER]\n{target or 'None'}\n[/ANSWER]"


def task_bad_aliases(pkg: str) -> list[str]:
    """Return negative aliases for a hallucinated package; keep only the raw name to avoid noise."""
    aliases = {pkg}
    return sorted(x for x in aliases if x)


def task_answer_unlikelihood(model, tokenizer, rec: dict, bad_text: str, device: str):
    """Suppress hallucinated package probability after the `[ANSWER]\n` prefix."""
    language = rec.get("language", "Python")
    question = task_question_from_prompt(language, rec["prompt"])
    return continuation_unlikelihood(model, tokenizer, recommendation_messages(language, question), "[ANSWER]\n", bad_text, device)


def target_for_record(rec: dict, max_task_packages: int) -> str:
    """Build the positive valid-package target from an edit record's target_new field."""
    target = str(rec.get("target_new", ""))
    pkgs = split_packages(target, "Python")
    if max_task_packages > 0:
        pkgs = pkgs[:max_task_packages]
    return ", ".join(pkgs) if pkgs else "None"


def batch_loss(model, tokenizer, batch: list[dict], cfg: EditConfig, device: str):
    """Compute the BOUND/SFT batch loss."""
    nll = torch.tensor(0.0, device=device)
    neg = torch.tensor(0.0, device=device)
    kl = torch.tensor(0.0, device=device)
    count = 0
    for rec in batch:
        target = target_for_record(rec, cfg.max_task_packages)
        if target:
            target = format_task_target(target)
            ids, labels = train_context(tokenizer, rec, target, device)
            nll = nll + cfg.task_weight * model(input_ids=ids, labels=labels).loss
            count += 1
        if cfg.method == "bound":
            for bad in list(rec.get("hallucinated", []))[:4]:
                for alias in task_bad_aliases(bad)[:4]:
                    if cfg.answer_neg_weight > 0:
                        neg = neg + cfg.answer_neg_weight * task_answer_unlikelihood(model, tokenizer, rec, alias, device)
            if cfg.kl_weight > 0:
                for lp in rec.get("locality_prompts", [])[:2]:
                    kl = kl + kl_to_base(model, tokenizer, lp, device)
                kl = kl + 0.25 * kl_to_base(model, tokenizer, rec["prompt"], device)
    denom = max(count, 1)
    loss = nll / denom + neg / denom + cfg.kl_weight * kl / denom
    return loss, {
        "nll": float((nll / denom).detach().cpu()),
        "neg": float((neg / denom).detach().cpu()),
        "kl": float((kl / denom).detach().cpu()),
    }


def edit_package_boundary(cfg: EditConfig):
    """Run localized package-boundary editing.

    `method=bound` uses valid-package NLL, answer-prefix bad-package
    unlikelihood, and locality KL. `method=sft` keeps only valid-package NLL.
    """
    if cfg.method not in {"bound", "sft"}:
        raise ValueError(f"unsupported method: {cfg.method}")

    set_gpu(cfg.gpu)
    random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_path,
        device_map="cuda",
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    for p in model.parameters():
        p.requires_grad = False

    target_modules = resolve_target_modules(cfg)
    targets = [x.strip() for x in target_modules.split(",") if x.strip()]
    edited = inject_lora(model, targets, cfg.rank, cfg.alpha, cfg.dropout)
    if not edited:
        raise RuntimeError(f"no target module matched: {targets}")
    print(f"inject {len(edited)} LoRA modules")

    records = [r for r in read_jsonl(cfg.edits_file) if r.get("type") == "task_recommend"]
    random.shuffle(records)
    if cfg.max_edits > 0:
        records = records[: cfg.max_edits]

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=cfg.lr)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logs = []
    for epoch in range(cfg.epochs):
        random.shuffle(records)
        pbar = tqdm(range(0, len(records), cfg.batch_size), desc=f"{cfg.method} epoch {epoch + 1}")
        for step, start in enumerate(pbar):
            batch = records[start : start + cfg.batch_size]
            loss, parts = batch_loss(model, tokenizer, batch, cfg, device)
            if loss.requires_grad:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                opt.zero_grad(set_to_none=True)
            else:
                parts["skipped"] = 1
            parts["loss"] = float(loss.detach().cpu())
            pbar.set_postfix(parts)
            logs.append({"epoch": epoch + 1, "step": step, **parts})

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(lora_state(model), cfg.output_dir / "bound_delta.pt")
    tokenizer.save_pretrained(cfg.output_dir)
    with (cfg.output_dir / "train_log.jsonl").open("w", encoding="utf-8") as f:
        for row in logs:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    payload = cfg.__dict__ | {
        "model_path": str(cfg.model_path),
        "edits_file": str(cfg.edits_file),
        "output_dir": str(cfg.output_dir),
        "resolved_target_modules": target_modules,
        "edited_modules": edited[:20],
        "n_edited_modules": len(edited),
    }
    write_json(cfg.output_dir / "bound_config.json", payload)
    model.eval()
    return model, tokenizer


# Localization and end-to-end package recommendation workflow

def localize_package_boundary(cfg: LocalizationConfig) -> None:
    """Locate linear modules most sensitive to package-boundary errors."""
    set_gpu(cfg.gpu)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_path,
        device_map="cuda",
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        trust_remote_code=True,
    )
    for p in model.parameters():
        p.requires_grad = False

    keys = [x.strip() for x in cfg.module_filter.split(",") if x.strip()]
    params = []
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear) and any(k in name for k in keys):
            module.weight.requires_grad = True
            params.append((name, module.weight))

    rows = [r for r in read_jsonl(cfg.edits_file) if r.get("type") == "task_recommend" and r.get("hallucinated")]
    random.Random(cfg.seed).shuffle(rows)
    rows = rows[: cfg.max_records] if cfg.max_records > 0 else rows
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    device = "cuda" if torch.cuda.is_available() else "cpu"

    for rec in tqdm(rows, desc="localize boundary modules"):
        language = rec.get("language", "Python")
        question = task_question_from_prompt(language, rec["prompt"])
        ids, _ = chat_message_ids(tokenizer, recommendation_messages(language, question), None, device)
        logits = model(input_ids=ids).logits[:, -1, :]
        bad_ids = []
        good_ids = []
        for pkg in rec.get("hallucinated", []):
            bad_ids.extend(tokenizer(" " + pkg, add_special_tokens=False).input_ids[:1])
        for pkg in rec.get("valid_reference", []):
            good_ids.extend(tokenizer(" " + pkg, add_special_tokens=False).input_ids[:1])
        if not bad_ids:
            continue

        obj = logits[:, sorted(set(bad_ids))].logsumexp(dim=-1).mean()
        if good_ids:
            obj = obj - cfg.anchor_penalty * logits[:, sorted(set(good_ids))].logsumexp(dim=-1).mean()
        family_ids = family_piece_ids(tokenizer, list(rec.get("hallucinated", [])))
        if family_ids and cfg.family_penalty > 0:
            obj = obj - cfg.family_penalty * logits[:, family_ids].logsumexp(dim=-1).mean()

        model.zero_grad(set_to_none=True)
        obj.backward()
        for name, weight in params:
            if weight.grad is None:
                continue
            val = (weight.grad.detach().float() * weight.detach().float()).abs().mean().item()
            scores[name] = scores.get(name, 0.0) + val
            counts[name] = counts.get(name, 0) + 1

    out = sorted(
        [{"module": name, "score": scores[name] / max(counts[name], 1), "count": counts[name]} for name in scores],
        key=lambda x: x["score"],
        reverse=True,
    )
    method = "risk-aware-boundary-localization"
    if cfg.family_penalty > 0:
        method = "family-residual-boundary-localization"
    write_json(
        cfg.out_file,
        {
            "method": method,
            "n_records": len(rows),
            "anchor_penalty": cfg.anchor_penalty,
            "family_penalty": cfg.family_penalty,
            "layer_scores": out[:200],
        },
    )
    print(json.dumps({"n_records": len(rows), "top": out[:5]}, ensure_ascii=False, indent=2))


def run_localize_then_edit(cfg: BoundaryEditConfig) -> None:
    """Run localization, editing, and optional post-edit evaluation."""
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Experiment directory: {cfg.output_dir}")
    print(f"Edit prompt file: {cfg.edits_file}")

    try:
        write_run_status(cfg, "localize", "running")
        print("Starting module localization...")
        localize_package_boundary(to_localization_config(cfg))
        write_run_status(cfg, "localize", "done", {"localization_report": str(cfg.localization_report)})
        print(f"Module localization finished: {cfg.localization_report}")

        write_run_status(cfg, "edit", "running")
        print("Starting BOUND editing...")
        model, tokenizer = edit_package_boundary(to_edit_config(cfg))
        write_run_status(cfg, "edit", "done", {"delta": str(Path(cfg.output_dir) / "bound_delta.pt")})
        print(f"BOUND editing finished: {Path(cfg.output_dir) / 'bound_delta.pt'}")

        if cfg.auto_eval:
            write_run_status(cfg, "eval", "running")
            print("Starting post-edit evaluation...")
            evaluate_after_edit(cfg, model, tokenizer)
            write_run_status(
                cfg,
                "eval",
                "done",
                {
                    "edit_eval": str(Path(cfg.output_dir) / "eval_edit_prompts.json"),
                    "unseen_eval": str(Path(cfg.output_dir) / "eval_unseen_prompts.json"),
                },
            )
            print(f"Edit prompt evaluation output: {Path(cfg.output_dir) / 'eval_edit_prompts.json'}")
            print(f"Unseen prompt evaluation output: {Path(cfg.output_dir) / 'eval_unseen_prompts.json'}")
    except Exception as exc:
        write_run_status(cfg, "failed", "error", {"error": repr(exc)})
        print(f"Experiment failed; status written to: {Path(cfg.output_dir) / 'run_status.json'}")
        raise


def write_run_status(cfg: BoundaryEditConfig, stage: str, status: str, extra: dict | None = None) -> None:
    """Record the current experiment stage so failed or interrupted runs are easy to inspect."""
    payload = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "stage": stage,
        "status": status,
        "experiment_dir": str(cfg.output_dir),
    }
    if extra:
        payload.update(extra)
    write_json(Path(cfg.output_dir) / "run_status.json", payload)


# Model loading, generation, and evaluation

def load_model(model_path: Path, delta_dir: Path | None):
    """Load the base model and optionally restore a BOUND/SFT LoRA delta."""
    if delta_dir and (delta_dir / "full_model").exists():
        tokenizer = AutoTokenizer.from_pretrained(delta_dir / "full_model", trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            delta_dir / "full_model",
            device_map="cuda",
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )
        model.eval()
        print(f"loaded full fine-tuned model {delta_dir / 'full_model'}")
        return model, tokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="cuda",
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        trust_remote_code=True,
    )
    if delta_dir:
        config_file = delta_dir / "bound_config.json"
        delta_file = delta_dir / "bound_delta.pt"
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        target_modules = cfg.get("resolved_target_modules", cfg["target_modules"])
        targets = [x.strip() for x in target_modules.split(",") if x.strip()]
        inject_lora(model, targets, int(cfg["rank"]), float(cfg["alpha"]), 0.0)
        state = torch.load(delta_file, map_location="cpu")
        model.load_state_dict(state, strict=False)
        print(f"loaded delta {delta_dir}")
    model.eval()
    return model, tokenizer


def gen_chat(
    model,
    tokenizer,
    messages: list[dict],
    max_new_tokens: int = 128,
    *,
    do_sample: bool = False,
    temperature: float = 0.7,
    top_p: float = 0.9,
    top_k: int = 40,
) -> str:
    """Generate text from a chat prompt."""
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    encoded = apply_chat_template(tokenizer, messages, add_generation_prompt=True, return_tensors="pt").to(device)
    if hasattr(encoded, "keys") and "input_ids" in encoded:
        ids = encoded["input_ids"]
        model_inputs = {key: encoded[key] for key in encoded.keys()}
    else:
        ids = encoded
        model_inputs = {"input_ids": ids}
    kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if do_sample:
        kwargs.update({"temperature": temperature, "top_p": top_p, "top_k": top_k})
    with torch.no_grad():
        out = model.generate(**model_inputs, **kwargs)
    return tokenizer.decode(out[0, ids.shape[1] :], skip_special_tokens=True).strip()


def response_key_for_question(question: str) -> str:
    """Build a stable key for matching original response rows by question text."""
    return "question:" + " ".join(str(question or "").split())


def response_key_for_id(value) -> str:
    """Build a stable key for matching original response rows by numeric prompt id."""
    return "id:" + str(value)


def edit_record_numeric_id(rec: dict):
    """Extract the numeric high-risk prompt id from an edit record id."""
    row_id = str(rec.get("id", ""))
    parts = row_id.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return rec.get("id")


def add_reference_trial(index: dict[str, list[dict]], row: dict, trial: dict | None = None) -> None:
    """Index one original-response trial by id and question."""
    trial_row = dict(trial or row)
    trial_row.setdefault("id", row.get("id"))
    trial_row.setdefault("question", row.get("question"))
    for key in [response_key_for_id(row.get("id")), response_key_for_question(row.get("question", ""))]:
        index.setdefault(key, []).append(trial_row)


def load_reference_response_index(path: Path | str) -> dict[str, list[dict]]:
    """Load original model responses and group trials by prompt id/question."""
    if not path:
        return {}
    index: dict[str, list[dict]] = {}
    for row in read_jsonl(Path(path)):
        trials = row.get("trials")
        if isinstance(trials, list):
            for trial in trials:
                add_reference_trial(index, row, trial)
        else:
            add_reference_trial(index, row)
    return index


def summarize_trials(trials: list[dict]) -> dict:
    """Summarize valid/hallucinated package behavior for a list of generation trials."""
    total_valid = sum(len(t.get("valid", []) or []) for t in trials)
    total_hall = sum(len(t.get("hallucinated", []) or []) for t in trials)
    total_packages = total_valid + total_hall
    n = len(trials)
    return {
        "n_trials": n,
        "total_valid": total_valid,
        "total_hallucinated": total_hall,
        "package_hallucination_rate": total_hall / max(total_packages, 1),
        "sample_hallucination_rate": sum(bool(t.get("hallucinated")) for t in trials) / max(n, 1),
        "sample_valid_rate": sum(bool(t.get("valid")) for t in trials) / max(n, 1),
        "avg_packages_per_trial": total_packages / max(n, 1),
        "avg_valid_per_trial": total_valid / max(n, 1),
        "avg_hallucinated_per_trial": total_hall / max(n, 1),
    }


def reference_for_prompt(index: dict[str, list[dict]], prompt_id, question: str) -> dict:
    """Return original model baseline trials for a prompt id/question pair."""
    trials = index.get(response_key_for_id(prompt_id), [])
    if not trials:
        trials = index.get(response_key_for_question(question), [])
    return {"summary": summarize_trials(trials), "trials": trials}


def generate_recommendation_trials(
    model,
    tokenizer,
    question: str,
    language: str,
    cutoff,
    release_cache: dict,
    *,
    num_generations: int,
    max_new_tokens: int,
    temperature: float,
    top_k: int,
    top_p: float,
) -> list[dict]:
    """Generate edited-model package recommendation trials and classify packages."""
    trials = []
    for gen_id in range(num_generations):
        ans = gen_chat(
            model,
            tokenizer,
            recommendation_messages(language, question),
            max_new_tokens,
            do_sample=num_generations > 1,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )
        pkgs = split_packages(ans, language)
        valid, hall = classify_packages_by_pypi(pkgs, language=language, cutoff=cutoff, release_cache=release_cache)
        trials.append(
            {
                "generation": gen_id,
                "answer": ans,
                "packages": pkgs,
                "valid": valid,
                "hallucinated": hall,
            }
        )
    return trials


def evaluate_after_edit(
    cfg: BoundaryEditConfig,
    model=None,
    tokenizer=None,
    *,
    eval_edit: bool = True,
    eval_unseen: bool = True,
) -> None:
    """Evaluate selected edit prompts and unseen prompts immediately after editing."""
    if not cfg.reference_response_file:
        print("skip post-edit evaluation: reference_response_file is empty")
        return

    reference_index = load_reference_response_index(cfg.reference_response_file)
    if model is None or tokenizer is None:
        model, tokenizer = load_model(Path(cfg.model_path), Path(cfg.output_dir))
    cutoff = infer_model_cutoff(cfg.model_path, cfg.eval_model_cutoff)
    release_cache: dict = {}

    if eval_edit:
        edit_records = [r for r in read_jsonl(Path(cfg.edits_file)) if r.get("type") == "task_recommend"]
        if cfg.eval_edit_max_samples:
            edit_records = edit_records[: cfg.eval_edit_max_samples]
        edit_details = []
        for rec in tqdm(edit_records, desc="eval selected edit prompts"):
            language = rec.get("language", "Python")
            question = task_question_from_prompt(language, rec["prompt"])
            prompt_id = edit_record_numeric_id(rec)
            trials = generate_recommendation_trials(
                model,
                tokenizer,
                question,
                language,
                cutoff,
                release_cache,
                num_generations=cfg.eval_num_generations,
                max_new_tokens=cfg.eval_max_new_tokens,
                temperature=cfg.eval_temperature,
                top_k=cfg.eval_top_k,
                top_p=cfg.eval_top_p,
            )
            edit_details.append(
                {
                    "id": rec.get("id"),
                    "prompt_id": prompt_id,
                    "question": question,
                    "baseline": reference_for_prompt(reference_index, prompt_id, question),
                    "edited": {"summary": summarize_trials(trials), "trials": trials},
                    "valid_reference": rec.get("valid_reference", []),
                    "training_hallucinated": rec.get("hallucinated", []),
                }
            )
        edit_summary = summarize_eval_pairs(edit_details)
        write_json(Path(cfg.output_dir) / "eval_edit_prompts.json", {"summary": edit_summary, "details": edit_details})
        print("Edit prompt evaluation summary:")
        print(json.dumps(edit_summary, ensure_ascii=False, indent=2))

    if not eval_unseen:
        return
    if not cfg.unseen_file:
        print("skip unseen post-edit evaluation: unseen_file is empty")
        return

    unseen_questions = read_eval_questions(Path(cfg.unseen_file), 0, cfg.eval_unseen_max_samples)
    unseen_details = []
    for prompt_id, question in tqdm(unseen_questions, desc="eval unseen prompts"):
        trials = generate_recommendation_trials(
            model,
            tokenizer,
            question,
            "Python",
            cutoff,
            release_cache,
            num_generations=cfg.eval_num_generations,
            max_new_tokens=cfg.eval_max_new_tokens,
            temperature=cfg.eval_temperature,
            top_k=cfg.eval_top_k,
            top_p=cfg.eval_top_p,
        )
        unseen_details.append(
            {
                "id": prompt_id,
                "question": question,
                "baseline": reference_for_prompt(reference_index, prompt_id, question),
                "edited": {"summary": summarize_trials(trials), "trials": trials},
            }
        )
    unseen_summary = summarize_eval_pairs(unseen_details)
    write_json(Path(cfg.output_dir) / "eval_unseen_prompts.json", {"summary": unseen_summary, "details": unseen_details})
    print("Unseen prompt evaluation summary:")
    print(json.dumps(unseen_summary, ensure_ascii=False, indent=2))


def summarize_eval_pairs(details: list[dict]) -> dict:
    """Aggregate baseline/edited summaries over evaluated prompts."""
    def avg(path: str) -> float:
        vals = []
        side, metric = path.split(".", 1)
        for row in details:
            summary = row.get(side, {}).get("summary", {})
            if summary.get("n_trials", 0) > 0:
                vals.append(float(summary.get(metric, 0.0)))
        return sum(vals) / max(len(vals), 1)

    return {
        "n_prompts": len(details),
        "baseline_sample_hallucination_rate": avg("baseline.sample_hallucination_rate"),
        "edited_sample_hallucination_rate": avg("edited.sample_hallucination_rate"),
        "baseline_package_hallucination_rate": avg("baseline.package_hallucination_rate"),
        "edited_package_hallucination_rate": avg("edited.package_hallucination_rate"),
        "baseline_sample_valid_rate": avg("baseline.sample_valid_rate"),
        "edited_sample_valid_rate": avg("edited.sample_valid_rate"),
    }
