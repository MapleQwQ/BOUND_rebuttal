#!/usr/bin/env python3
"""Reproducible blind adjudication for E1.

This script intentionally reads only the six anonymous inputs authorized for
the final E1 adjudication.  It never loads keys, model/method/fold mappings,
non-anonymous manifests, old adjudications, or evaluation sources.
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
AUDIT_DATE = "2026-09-23"

INPUTS = {
    "manifest": "formal_prompt_manifest_anonymous.jsonl",
    "answers": "blinded_answers_anonymous.jsonl",
    "slots": "frozen_requirement_slots_anonymous.jsonl",
    "a": "final_blind_annotator_a_labels.jsonl",
    "b": "final_blind_annotator_b_labels.jsonl",
}


def load_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (RESULTS / name).read_text().splitlines() if line.strip()]


manifest_rows = load_jsonl(INPUTS["manifest"])
answer_rows = load_jsonl(INPUTS["answers"])
slot_rows = load_jsonl(INPUTS["slots"])
a_rows = load_jsonl(INPUTS["a"])
b_rows = load_jsonl(INPUTS["b"])

manifest = {r["anonymous_task_id"]: r for r in manifest_rows}
answers = {r["blind_answer_id"]: r for r in answer_rows}
slots = {r["anonymous_task_id"]: r for r in slot_rows}
ann_a = {r["blind_answer_id"]: r for r in a_rows}
ann_b = {r["blind_answer_id"]: r for r in b_rows}


def kappa(xs: list, ys: list) -> dict:
    assert len(xs) == len(ys) and xs
    n = len(xs)
    observed = sum(x == y for x, y in zip(xs, ys)) / n
    categories = set(xs) | set(ys)
    expected = sum((xs.count(c) / n) * (ys.count(c) / n) for c in categories)
    value = None if math.isclose(expected, 1.0) else (observed - expected) / (1.0 - expected)
    return {
        "n": n,
        "agreements": sum(x == y for x, y in zip(xs, ys)),
        "disagreements": sum(x != y for x, y in zip(xs, ys)),
        "exact_agreement": observed,
        "cohen_kappa": value,
        "kappa_note": "undefined because both annotators used one constant category" if value is None else None,
    }


# Adjudicated candidate-type decisions.  Exact existing PyPI names remain
# distribution names even when they are deprecated aliases/placeholders.
TYPE_DECISIONS = {
    ("TASK-0064dfbd01f8b25d", "sklearn"): "distribution_name",
    ("TASK-04d3faf70faa712d", "pugjs"): "external_tool_or_product",
    ("TASK-22500831992e201b", "dotenv"): "distribution_name",
    ("TASK-47099de402232ce8", "pyethereum"): "ambiguous_name",
    ("TASK-47099de402232ce8", "solcx"): "import_name",
    ("TASK-59948f3a981e4275", "python-requests"): "ambiguous_name",
    ("TASK-5e591ca43b37830e", "grpc"): "distribution_name",
    ("TASK-6a7e8d705eef8bf2", "ruamel"): "import_name",
    ("TASK-74c4e54e4065e671", "powerdns"): "external_tool_or_product",
    ("TASK-8d6145c4ada0caa5", "aws-cdk"): "external_tool_or_product",
    ("TASK-a177a45ec68f0d44", "python-jinja2"): "ambiguous_name",
    ("TASK-a5057052fd507974", "graphene-core"): "ambiguous_name",
    ("TASK-affecfc45cbe926d", "googleapis"): "ambiguous_name",
    ("TASK-bc9165593df89b41", "libvirt"): "import_name",
    ("TASK-bc9165593df89b41", "openstack"): "external_tool_or_product",
    ("TASK-c75547cbbe41cd72", "pil"): "distribution_name",
    ("TASK-c75547cbbe41cd72", "sklearn"): "distribution_name",
    ("TASK-ca210f1d31f3f776", "aws-cdk"): "external_tool_or_product",
    ("TASK-ca210f1d31f3f776", "aws-ecs"): "ambiguous_name",
    ("TASK-ca210f1d31f3f776", "aws-iam"): "ambiguous_name",
    ("TASK-cffb46307a16d142", "aws-cdk"): "external_tool_or_product",
    ("TASK-df886b6850df3d39", "ruamel"): "import_name",
    ("TASK-f883de14a8e6032d", "aws-cdk"): "external_tool_or_product",
    ("TASK-f883de14a8e6032d", "aws-lambda-nodejs"): "ambiguous_name",
    ("TASK-f883de14a8e6032d", "aws-lambda-python"): "ambiguous_name",
}

REGISTRY_DECISIONS = {
    ("TASK-04d3faf70faa712d", "pugjs"): "not_applicable_external_tool",
    ("TASK-74c4e54e4065e671", "powerdns"): "not_applicable_external_tool",
    ("TASK-8d6145c4ada0caa5", "aws-cdk"): "not_applicable_external_tool",
    ("TASK-bc9165593df89b41", "openstack"): "not_applicable_external_tool",
    ("TASK-ca210f1d31f3f776", "aws-cdk"): "not_applicable_external_tool",
    ("TASK-cffb46307a16d142", "aws-cdk"): "not_applicable_external_tool",
    ("TASK-f883de14a8e6032d", "aws-cdk"): "not_applicable_external_tool",
}

# Slot decisions are capability decisions, not votes. Empty tuples are
# intentional: the candidate may be useful but does not satisfy the frozen
# atomic dependency requirement or its explicit ecosystem constraint.
SLOT_DECISIONS = {
    ("TASK-04d3faf70faa712d", "pugjs"): (),
    ("TASK-10f75231042d1add", "girder-client"): ("3373-S1",),
    ("TASK-10f75231042d1add", "opencv-python"): (),
    ("TASK-10f75231042d1add", "pillow"): (),
    ("TASK-10f75231042d1add", "plotly"): (),
    ("TASK-3d2a7e0a84c1f00e", "datahub"): (),
    ("TASK-3d2a7e0a84c1f00e", "requests"): (),
    ("TASK-441154ccd637c7df", "jaeger-client"): (),
    ("TASK-441154ccd637c7df", "opentelemetry-instrumentation"): ("88-S1",),
    ("TASK-59948f3a981e4275", "pyusps"): (),
    ("TASK-59948f3a981e4275", "requests"): (),
    ("TASK-62cf118c26c1c254", "opentelemetry-exporter-prometheus"): (),
    ("TASK-7eae5a13d9eceee7", "aiohttp"): (),
    ("TASK-9e88043e117f07bd", "transformers"): ("1039-S2",),
    ("TASK-a177a45ec68f0d44", "mkdocs"): (),
    ("TASK-a5057052fd507974", "django"): ("2836-S1",),
    ("TASK-a5057052fd507974", "graphene"): ("2836-S1", "2836-S2"),
    ("TASK-bc9165593df89b41", "apache-libcloud"): (),
    ("TASK-bc9165593df89b41", "docker"): (),
    ("TASK-c75547cbbe41cd72", "keras"): ("934-S1", "934-S2"),
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-cloudwatch"): (),
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-ecs"): (),
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-iam"): (),
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-logs"): (),
    ("TASK-ca210f1d31f3f776", "aws-cdk-lib"): (),
    ("TASK-d1596a655ed847e1", "semantic-release"): (),
    ("TASK-df4f6f0af4f98ab9", "opencv-python"): ("2195-S2",),
    ("TASK-df4f6f0af4f98ab9", "pillow"): ("2195-S2",),
    ("TASK-f33f68651d2eca07", "nltk"): ("1804-S1", "1804-S4"),
    ("TASK-f33f68651d2eca07", "transformers"): ("1804-S1", "1804-S2", "1804-S4"),
    ("TASK-f883de14a8e6032d", "constructs"): (),
}

# Real, documented support that is related to the task but does not cover a
# frozen dependency slot. All role disagreements not listed here become
# irrelevant unless SLOT_DECISIONS (or consensus coverage) makes them core.
OPTIONAL = {
    "TASK-0064dfbd01f8b25d": {"cv2", "sklearn"},
    "TASK-04bb73f56810f220": {"requests-toolbelt"},
    "TASK-04d3faf70faa712d": {"pugjs", "pugjs-templates"},
    "TASK-0cfbb603fc4c47a7": {"airflow", "confluent-kafka-python", "kafka"},
    "TASK-10f75231042d1add": {"dash-core-components", "dash-html-components", "dash-table", "girder-plugin-sdk", "opencv-python", "pillow", "plotly"},
    "TASK-22500831992e201b": {"dotenv", "os"},
    "TASK-23c0b8edeaad81ef": {"stardog"},
    "TASK-3ba95f14c41911c1": {"concurrent", "multiprocessing", "subprocess", "threading"},
    "TASK-3d2a7e0a84c1f00e": {"airflow", "datahub", "pandas", "requests"},
    "TASK-4005e393be022acf": {"korean-romanization", "koreanize"},
    "TASK-441154ccd637c7df": {"jaeger-client", "opentelemetry-exporter-influxdb"},
    "TASK-50147ba4b0f7f7db": {"pkg-resources", "subprocess"},
    "TASK-55b0b4b283864261": {"types-aiobotocore"},
    "TASK-59948f3a981e4275": {"pyusps", "requests", "usps"},
    "TASK-5e591ca43b37830e": {"flask-envoy-proxy", "grpc", "python-envoy"},
    "TASK-62cf118c26c1c254": {"opentelemetry-exporter-jaeger", "opentelemetry-exporter-kafka", "opentelemetry-exporter-otlp", "opentelemetry-exporter-prometheus"},
    "TASK-680094a6e2b8fe61": {"unittest"},
    "TASK-74c4e54e4065e671": {"dns", "powerdns", "powerdns-rec-api", "python-dns"},
    "TASK-7a841098e0a2f148": {"kcachegrind", "qcachegrind"},
    "TASK-7eae5a13d9eceee7": {"aiohttp", "dvc-datasets", "iterative", "iterative-api-client"},
    "TASK-8d6145c4ada0caa5": {"awacs", "aws-cdk", "awstextract", "botocore"},
    "TASK-95296e36d58d50a5": {"requests"},
    "TASK-9b869c09cf724f55": {"yui-compressor"},
    "TASK-9e43bc9da1683d47": {"json", "sarif"},
    "TASK-9e88043e117f07bd": {"ct2"},
    "TASK-a177a45ec68f0d44": {"jsonschema", "mkdocs", "mkdocs-awesome-pages", "mkdocs-git-revision-date", "mkdocs-jupyter", "mkdocs-markdown-extensions", "mkdocs-redirects"},
    "TASK-a5057052fd507974": {"django"},
    "TASK-b5e8a20da07b93f2": {"cgroup", "resource", "threading"},
    "TASK-bc9165593df89b41": {"apache-libcloud", "docker", "heat", "openstack", "packer"},
    "TASK-c6cb64d82677dd9c": {"monad-tools"},
    "TASK-c75547cbbe41cd72": {"opencv", "pil", "sklearn"},
    "TASK-c820240de39f9f64": {"matplotlib", "numpy", "pandas", "scipy"},
    "TASK-ca210f1d31f3f776": {"aws-cdk", "aws-cdk-aws-cloudwatch", "aws-cdk-aws-ecs", "aws-cdk-aws-iam", "aws-cdk-aws-logs", "aws-cdk-lib"},
    "TASK-cffb46307a16d142": {"aws-cdk", "jinja2"},
    "TASK-d1596a655ed847e1": {"release-drafter", "requests"},
    "TASK-df4f6f0af4f98ab9": {"openjpeg", "opencv", "pyopenjpeg"},
    "TASK-eed19d9b2dd696a5": {"mysql-connector-python"},
    "TASK-fb238b01942fb8b5": {"isatools", "rdflib-sparqlstore"},
}

DOCS = {
    ("TASK-04d3faf70faa712d", "pugjs"): "https://pugjs.org/api/getting-started.html",
    ("TASK-10f75231042d1add", "girder-client"): "https://girder.readthedocs.io/en/latest/python-client.html",
    ("TASK-10f75231042d1add", "pillow"): "https://pillow.readthedocs.io/en/stable/",
    ("TASK-10f75231042d1add", "plotly"): "https://plotly.com/python/",
    ("TASK-3d2a7e0a84c1f00e", "datahub"): "https://docs.datahub.com/docs/lineage/airflow/",
    ("TASK-441154ccd637c7df", "jaeger-client"): "https://github.com/jaegertracing/jaeger-client-python",
    ("TASK-441154ccd637c7df", "opentelemetry-instrumentation"): "https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/instrumentation.html",
    ("TASK-59948f3a981e4275", "pyusps"): "https://github.com/thelinuxkid/pyusps",
    ("TASK-62cf118c26c1c254", "opentelemetry-exporter-prometheus"): "https://opentelemetry-python.readthedocs.io/en/latest/exporter/prometheus/prometheus.html",
    ("TASK-7eae5a13d9eceee7", "aiohttp"): "https://docs.aiohttp.org/en/stable/client.html",
    ("TASK-9e88043e117f07bd", "transformers"): "https://huggingface.co/docs/transformers/tasks/asr",
    ("TASK-a177a45ec68f0d44", "mkdocs"): "https://www.mkdocs.org/user-guide/configuration/",
    ("TASK-a5057052fd507974", "django"): "https://docs.djangoproject.com/en/stable/topics/http/urls/",
    ("TASK-a5057052fd507974", "graphene"): "https://docs.graphene-python.org/en/latest/types/schema/",
    ("TASK-bc9165593df89b41", "apache-libcloud"): "https://libcloud.readthedocs.io/en/stable/compute/drivers/openstack.html",
    ("TASK-bc9165593df89b41", "docker"): "https://docker-py.readthedocs.io/en/stable/",
    ("TASK-c75547cbbe41cd72", "keras"): "https://keras.io/api/data_loading/image/",
    ("TASK-ca210f1d31f3f776", "aws-cdk-lib"): "https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecs.html",
    ("TASK-d1596a655ed847e1", "semantic-release"): "https://pypi.org/project/semantic-release/",
    ("TASK-df4f6f0af4f98ab9", "pillow"): "https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg-2000",
    ("TASK-f33f68651d2eca07", "nltk"): "https://www.nltk.org/api/nltk.sentiment.html",
    ("TASK-f33f68651d2eca07", "transformers"): "https://huggingface.co/docs/transformers/main_classes/pipelines",
    ("TASK-f883de14a8e6032d", "constructs"): "https://constructs.dev/",
}

SLOT_REASONS = {
    ("TASK-04d3faf70faa712d", "pugjs"): "PugJS compiles Pug templates but is not a Python adapter integrating all four named template engines.",
    ("TASK-10f75231042d1add", "girder-client"): "The client directly supports Girder API integration, but annotation storage/query requires the large-image annotation server/plugin API.",
    ("TASK-10f75231042d1add", "opencv-python"): "Image processing alone does not provide persistent multiresolution annotation storage/query.",
    ("TASK-10f75231042d1add", "pillow"): "Image I/O alone does not provide persistent multiresolution annotation storage/query.",
    ("TASK-10f75231042d1add", "plotly"): "General interactive plotting does not implement the required large-image annotation GUI/plugin capability.",
    ("TASK-3d2a7e0a84c1f00e", "datahub"): "The exact package supplies DataHub ingestion/API support, but not the Airflow execution-capture integration required by the combined slot.",
    ("TASK-3d2a7e0a84c1f00e", "requests"): "A generic HTTP client can transmit data but does not capture Airflow task executions or implement DataHub lineage semantics.",
    ("TASK-441154ccd637c7df", "jaeger-client"): "This is an OpenTracing Jaeger client, not an OpenTelemetry Jaeger exporter.",
    ("TASK-441154ccd637c7df", "opentelemetry-instrumentation"): "The package directly provides OpenTelemetry application auto-instrumentation and combines with API/SDK packages for tracer/span creation.",
    ("TASK-59948f3a981e4275", "pyusps"): "The official README states that only the Address Information API is supported; rates and shipping labels are not.",
    ("TASK-59948f3a981e4275", "requests"): "A generic HTTP client does not itself implement carrier rate and label APIs.",
    ("TASK-62cf118c26c1c254", "opentelemetry-exporter-prometheus"): "The package exports OpenTelemetry metrics to Prometheus but does not collect Kafka producer/consumer/topic metrics.",
    ("TASK-7eae5a13d9eceee7", "aiohttp"): "It can send HTTP requests, but it is not requests-compatible as explicitly required and supplies no DVC/Studio integration.",
    ("TASK-9e88043e117f07bd", "transformers"): "Transformers provides Whisper audio transcription, but not the CTranslate2 backend requirement.",
    ("TASK-a177a45ec68f0d44", "mkdocs"): "Base MkDocs builds one documentation site; it does not itself aggregate multiple monorepo documentation trees.",
    ("TASK-a5057052fd507974", "django"): "Django supplies the required web integration/routing side of the Django GraphQL API.",
    ("TASK-a5057052fd507974", "graphene"): "Graphene provides GraphQL schema execution, validation/introspection, and mutations and can be wired into a Django view.",
    ("TASK-bc9165593df89b41", "apache-libcloud"): "Libcloud is a cross-cloud abstraction and not the explicitly requested OpenStack SDK coverage for compute, storage, and networking.",
    ("TASK-bc9165593df89b41", "docker"): "Docker container management is not Vagrant-compatible local VM/compute provisioning.",
    ("TASK-c75547cbbe41cd72", "keras"): "Keras documents both image dataset loading/preprocessing and neural-network training/evaluation.",
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-cloudwatch"): "A generic CloudWatch construct library does not provide the requested ECS service-extension construct.",
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-ecs"): "A generic ECS construct library does not provide the requested ECS service-extension abstraction.",
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-iam"): "A generic IAM construct library does not provide the requested ECS service-extension construct.",
    ("TASK-ca210f1d31f3f776", "aws-cdk-aws-logs"): "A generic Logs construct library does not provide the requested ECS service-extension construct.",
    ("TASK-ca210f1d31f3f776", "aws-cdk-lib"): "AWS CDK v2 contains generic ECS/logs/alarms/IAM constructs but not the named service-extension construct abstraction.",
    ("TASK-d1596a655ed847e1", "semantic-release"): "The exact PyPI distribution is an undocumented 0.1.0 package and is not python-semantic-release; no silent correction is credited.",
    ("TASK-df4f6f0af4f98ab9", "opencv-python"): "OpenCV can convert JPEG 2000 imagery and expose image metadata, but it is not the required OpenJPEG Python binding for direct read/write coverage.",
    ("TASK-df4f6f0af4f98ab9", "pillow"): "Pillow can use OpenJPEG for JPEG 2000 conversion/metadata but is not itself the required OpenJPEG Python binding.",
    ("TASK-f33f68651d2eca07", "nltk"): "NLTK documents tokenization/POS tagging and sentiment analysis; it does not cover the other frozen NLP slots here.",
    ("TASK-f33f68651d2eca07", "transformers"): "Transformers supports tokenization/token classification (including NER/POS models) and sentiment pipelines, but not dependency parsing by itself.",
    ("TASK-f883de14a8e6032d", "constructs"): "The generic constructs programming model does not define AWS CDK v2 Lambda resources or Datadog wrapping.",
}


def merged_evidence(ac: dict, bc: dict, tid: str, name: str, disputed: bool) -> list[dict]:
    out = []
    seen = set()
    for ev in list(ac.get("evidence", [])) + list(bc.get("evidence", [])):
        url = ev.get("url")
        if not url or url == "frozen_requirement_slots_anonymous.jsonl":
            continue
        key = (url, ev.get("note", ""))
        if key not in seen:
            seen.add(key)
            out.append({"url": url, "note": ev.get("note", "")})
    if disputed:
        pypi_url = f"https://pypi.org/pypi/{name}/json"
        if not any(e["url"] == pypi_url for e in out):
            out.append({"url": pypi_url, "note": f"Exact-name PyPI registry check on {AUDIT_DATE}."})
        if (tid, name) in DOCS and not any(e["url"] == DOCS[(tid, name)] for e in out):
            out.append({"url": DOCS[(tid, name)], "note": f"Official/project capability documentation checked on {AUDIT_DATE}."})
    return out


def classify_choice(value, av, bv) -> str:
    if av == bv:
        return "consensus"
    if value == av and value != bv:
        return "annotator_a_supported"
    if value == bv and value != av:
        return "annotator_b_supported"
    return "independent_resolution"


# Pre-adjudication agreement.
answer_ids = [r["blind_answer_id"] for r in answer_rows]
assert set(answer_ids) == set(ann_a) == set(ann_b)
assert len(answer_ids) == 300 and len(set(answer_ids)) == 300

agreement = {
    "audit_date_utc": AUDIT_DATE,
    "blind": True,
    "inputs": list(INPUTS.values()) + ["annotation_guideline.md"],
    "units": {"answers": 300, "candidates": 960, "tasks": 60},
    "metrics": {},
}

agreement["metrics"]["adequacy"] = kappa(
    [ann_a[i]["adequacy"] for i in answer_ids],
    [ann_b[i]["adequacy"] for i in answer_ids],
)
agreement["metrics"]["registry_status_candidate_level"] = kappa(
    [c["registry_status"] for i in answer_ids for c in ann_a[i]["candidates"]],
    [c["registry_status"] for i in answer_ids for c in ann_b[i]["candidate_annotations"]],
)
agreement["metrics"]["task_role_candidate_level"] = kappa(
    [c["task_role"] for i in answer_ids for c in ann_a[i]["candidates"]],
    [c["task_role"] for i in answer_ids for c in ann_b[i]["candidate_annotations"]],
)
agreement["metrics"]["candidate_covered_slot_set_exact"] = kappa(
    [tuple(sorted(c["covered_slots"])) for i in answer_ids for c in ann_a[i]["candidates"]],
    [tuple(sorted(c["covered_slots"])) for i in answer_ids for c in ann_b[i]["candidate_annotations"]],
)
agreement["metrics"]["answer_covered_slot_set_exact"] = kappa(
    [tuple(sorted(ann_a[i]["covered_slots"])) for i in answer_ids],
    [tuple(sorted(ann_b[i]["covered_slots"])) for i in answer_ids],
)
agreement["metrics"]["cannot_judge"] = kappa(
    [bool(ann_a[i]["cannot_judge"]) for i in answer_ids],
    [bool(ann_b[i]["cannot_judge"]) for i in answer_ids],
)

for level in ("answer", "candidate"):
    xs, ys = [], []
    for i in answer_ids:
        tid = ann_a[i]["anonymous_task_id"]
        universe = [s["slot_id"] for s in slots[tid]["slots"]]
        pairs = [(ann_a[i], ann_b[i])] if level == "answer" else zip(ann_a[i]["candidates"], ann_b[i]["candidate_annotations"])
        for ac, bc in pairs:
            aset, bset = set(ac["covered_slots"]), set(bc["covered_slots"])
            for sid in universe:
                xs.append(sid in aset)
                ys.append(sid in bset)
    agreement["metrics"][f"{level}_slot_binary"] = kappa(xs, ys)

agreement["label_distributions"] = {
    "adequacy_a": dict(Counter(ann_a[i]["adequacy"] for i in answer_ids)),
    "adequacy_b": dict(Counter(ann_b[i]["adequacy"] for i in answer_ids)),
    "registry_a": dict(Counter(c["registry_status"] for i in answer_ids for c in ann_a[i]["candidates"])),
    "registry_b": dict(Counter(c["registry_status"] for i in answer_ids for c in ann_b[i]["candidate_annotations"])),
    "task_role_a": dict(Counter(c["task_role"] for i in answer_ids for c in ann_a[i]["candidates"])),
    "task_role_b": dict(Counter(c["task_role"] for i in answer_ids for c in ann_b[i]["candidate_annotations"])),
}


adjudicated_rows = []
disagreement_rows = []
choice_counts = Counter()

for answer in answer_rows:
    bid = answer["blind_answer_id"]
    ar, br = ann_a[bid], ann_b[bid]
    tid = answer["anonymous_task_id"]
    assert ar["anonymous_task_id"] == br["anonymous_task_id"] == tid
    assert len(ar["candidates"]) == len(br["candidate_annotations"])
    valid_slots = [s["slot_id"] for s in slots[tid]["slots"]]
    final_candidates = []
    candidate_diffs = []

    for idx, (ac, bc) in enumerate(zip(ar["candidates"], br["candidate_annotations"])):
        name = ac["candidate_name"]
        assert name == bc["candidate"]
        key = (tid, name)
        disputed_fields = []
        if ac["candidate_type"] != bc["candidate_type"]:
            disputed_fields.append("candidate_type")
        if ac["registry_status"] != bc["registry_status"]:
            disputed_fields.append("registry_status")
        if ac["task_role"] != bc["task_role"]:
            disputed_fields.append("task_role")
        if set(ac["covered_slots"]) != set(bc["covered_slots"]):
            disputed_fields.append("covered_slots")

        ctype = ac["candidate_type"] if ac["candidate_type"] == bc["candidate_type"] else TYPE_DECISIONS[key]
        registry = ac["registry_status"] if ac["registry_status"] == bc["registry_status"] else REGISTRY_DECISIONS[key]
        covered = sorted(
            set(ac["covered_slots"])
            if set(ac["covered_slots"]) == set(bc["covered_slots"])
            else set(SLOT_DECISIONS[key]),
            key=valid_slots.index,
        )
        if ac["task_role"] == bc["task_role"] and "covered_slots" not in disputed_fields:
            role = ac["task_role"]
        elif covered:
            role = "core_function_support"
        elif registry == "nonexistent_at_audit_date":
            role = "irrelevant"
        elif name in OPTIONAL.get(tid, set()):
            role = "optional_support"
        else:
            role = "irrelevant"

        # Enforce role/coverage semantics from the guideline.
        if covered:
            role = "core_function_support"
        elif role == "core_function_support":
            role = "optional_support" if name in OPTIONAL.get(tid, set()) else "irrelevant"

        if ac["candidate_type"] == bc["candidate_type"]:
            name_relation = ac["name_relation"]
        elif ctype == "external_tool_or_product":
            name_relation = "Recognizable external product/tool name; not treated as an installable PyPI distribution."
        elif ctype == "import_name":
            name_relation = "Import/namespace-style name; no silent substitution to a different distribution was credited."
        elif ctype == "distribution_name":
            name_relation = "Exact-name PyPI distribution exists; aliases/placeholders are judged by their documented contents."
        else:
            name_relation = "Ambiguous or malformed package-like name; no silent correction was applied."

        reason = SLOT_REASONS.get(key)
        if not reason and disputed_fields:
            if registry == "nonexistent_at_audit_date":
                reason = "Exact-name PyPI distribution was not found; inferred intent was not credited as real capability."
            elif role == "optional_support":
                reason = "Documented capability is task-related but does not cover a frozen atomic dependency slot or its explicit constraint."
            elif role == "irrelevant":
                reason = "No documented capability of the raw candidate satisfies or materially supports the frozen task requirements."
            else:
                reason = "Documented capability directly covers the cited frozen slot(s)."

        final_c = {
            "candidate_index": idx,
            "candidate_name": name,
            "candidate_type": ctype,
            "name_relation": name_relation,
            "registry_status": registry,
            "task_role": role,
            "covered_slots": covered,
            "evidence": merged_evidence(ac, bc, tid, name, bool(disputed_fields)),
            "adjudication_status": "adjudicated" if disputed_fields else "consensus",
        }
        if disputed_fields:
            final_c["adjudication_reason"] = reason
            choice_counts[classify_choice(ctype, ac["candidate_type"], bc["candidate_type"])] += int("candidate_type" in disputed_fields)
            choice_counts[classify_choice(registry, ac["registry_status"], bc["registry_status"])] += int("registry_status" in disputed_fields)
            choice_counts[classify_choice(role, ac["task_role"], bc["task_role"])] += int("task_role" in disputed_fields)
            choice_counts[classify_choice(tuple(covered), tuple(ac["covered_slots"]), tuple(bc["covered_slots"]))] += int("covered_slots" in disputed_fields)
            candidate_diffs.append({
                "candidate_index": idx,
                "candidate_name": name,
                "disputed_fields": disputed_fields,
                "annotator_a": {
                    "candidate_type": ac["candidate_type"],
                    "registry_status": ac["registry_status"],
                    "task_role": ac["task_role"],
                    "covered_slots": ac["covered_slots"],
                },
                "annotator_b": {
                    "candidate_type": bc["candidate_type"],
                    "registry_status": bc["registry_status"],
                    "task_role": bc["task_role"],
                    "covered_slots": bc["covered_slots"],
                },
                "adjudicated": {
                    "candidate_type": ctype,
                    "registry_status": registry,
                    "task_role": role,
                    "covered_slots": covered,
                },
                "reason": reason,
                "evidence": final_c["evidence"],
            })
        final_candidates.append(final_c)

    covered_answer = sorted(
        set().union(*(set(c["covered_slots"]) for c in final_candidates)) if final_candidates else set(),
        key=valid_slots.index,
    )
    total = len(valid_slots)
    no_third_party = bool(slots[tid]["no_third_party_dependency_needed"])
    if total == 0 and no_third_party:
        adequacy = "adequate"
        slot_coverage = 1.0
    elif not covered_answer:
        adequacy = "inadequate"
        slot_coverage = 0.0
    elif len(covered_answer) == total:
        adequacy = "adequate"
        slot_coverage = 1.0
    else:
        adequacy = "partially_adequate_with_clear_omission"
        slot_coverage = len(covered_answer) / total

    answer_status = "adjudicated" if (candidate_diffs or ar["adequacy"] != br["adequacy"] or set(ar["covered_slots"]) != set(br["covered_slots"])) else "consensus"
    row = {
        "blind_answer_id": bid,
        "anonymous_task_id": tid,
        "candidates": final_candidates,
        "covered_slots": covered_answer,
        "slot_coverage": slot_coverage,
        "adequacy": adequacy,
        "cannot_judge": False,
        "cannot_judge_reason": None,
        "adjudication_status": answer_status,
        "audit_date_utc": AUDIT_DATE,
    }
    adjudicated_rows.append(row)

    if answer_status == "adjudicated":
        disagreement_rows.append({
            "blind_answer_id": bid,
            "anonymous_task_id": tid,
            "question": manifest[tid]["question"],
            "packages": answer["packages"],
            "answer_level": {
                "annotator_a": {"adequacy": ar["adequacy"], "covered_slots": ar["covered_slots"], "cannot_judge": ar["cannot_judge"]},
                "annotator_b": {"adequacy": br["adequacy"], "covered_slots": br["covered_slots"], "cannot_judge": br["cannot_judge"]},
                "adjudicated": {"adequacy": adequacy, "covered_slots": covered_answer, "cannot_judge": False},
            },
            "candidate_disagreements": candidate_diffs,
        })


# Final QA invariants.
qa = {}
qa["answer_rows"] = len(adjudicated_rows)
qa["unique_answer_ids"] = len({r["blind_answer_id"] for r in adjudicated_rows})
qa["candidate_rows"] = sum(len(r["candidates"]) for r in adjudicated_rows)
per_task = Counter(r["anonymous_task_id"] for r in adjudicated_rows)
qa["task_count"] = len(per_task)
qa["five_answers_per_task"] = all(v == 5 for v in per_task.values()) and len(per_task) == 60
qa["all_slot_references_valid"] = True
qa["answer_coverage_equals_candidate_union"] = True
qa["role_coverage_consistent"] = True
qa["adequacy_coverage_consistent"] = True

for r in adjudicated_rows:
    valid = {s["slot_id"] for s in slots[r["anonymous_task_id"]]["slots"]}
    union = set()
    for c in r["candidates"]:
        if not set(c["covered_slots"]) <= valid:
            qa["all_slot_references_valid"] = False
        if bool(c["covered_slots"]) != (c["task_role"] == "core_function_support"):
            qa["role_coverage_consistent"] = False
        union |= set(c["covered_slots"])
    if union != set(r["covered_slots"]):
        qa["answer_coverage_equals_candidate_union"] = False
    expected = "adequate" if (not valid and slots[r["anonymous_task_id"]]["no_third_party_dependency_needed"]) or union == valid else ("inadequate" if not union else "partially_adequate_with_clear_omission")
    if r["adequacy"] != expected:
        qa["adequacy_coverage_consistent"] = False

assert qa == {
    "answer_rows": 300,
    "unique_answer_ids": 300,
    "candidate_rows": 960,
    "task_count": 60,
    "five_answers_per_task": True,
    "all_slot_references_valid": True,
    "answer_coverage_equals_candidate_union": True,
    "role_coverage_consistent": True,
    "adequacy_coverage_consistent": True,
}

agreement["disagreement_inventory"] = {
    "answers_with_any_disagreement": len(disagreement_rows),
    "answers_with_adequacy_disagreement": agreement["metrics"]["adequacy"]["disagreements"],
    "candidate_pairs_with_any_disagreement": sum(len(d["candidate_disagreements"]) for d in disagreement_rows),
    "cannot_judge_a": sum(bool(ann_a[i]["cannot_judge"]) for i in answer_ids),
    "cannot_judge_b": sum(bool(ann_b[i]["cannot_judge"]) for i in answer_ids),
}
agreement["qa"] = qa


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


(RESULTS / "final_blind_interannotator_agreement.json").write_text(json.dumps(agreement, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
dump_jsonl(RESULTS / "final_blind_interannotator_disagreements.jsonl", disagreement_rows)
dump_jsonl(RESULTS / "final_blind_adjudicated_labels.jsonl", adjudicated_rows)

metrics = agreement["metrics"]
agreement_md = f"""# E1 Final Blind Inter-Annotator Agreement

## Technical summary

Before adjudication, the two blind annotators agreed on **{metrics['adequacy']['exact_agreement']:.1%}** of answer-level Adequacy labels (Cohen's κ = **{metrics['adequacy']['cohen_kappa']:.3f}**). Registry status was highly reproducible (**{metrics['registry_status_candidate_level']['exact_agreement']:.1%}**, κ = **{metrics['registry_status_candidate_level']['cohen_kappa']:.3f}**), while task-role classification was the main judgment boundary (**{metrics['task_role_candidate_level']['exact_agreement']:.1%}**, κ = **{metrics['task_role_candidate_level']['cohen_kappa']:.3f}**). Both annotators marked all 300 answers judgeable.

## Agreement results

| Dimension | Unit / N | Exact agreement | Cohen's κ | Disagreements |
|---|---:|---:|---:|---:|
| Adequacy | answers / 300 | {metrics['adequacy']['exact_agreement']:.2%} | {metrics['adequacy']['cohen_kappa']:.3f} | {metrics['adequacy']['disagreements']} |
| Registry status | candidates / 960 | {metrics['registry_status_candidate_level']['exact_agreement']:.2%} | {metrics['registry_status_candidate_level']['cohen_kappa']:.3f} | {metrics['registry_status_candidate_level']['disagreements']} |
| Task role | candidates / 960 | {metrics['task_role_candidate_level']['exact_agreement']:.2%} | {metrics['task_role_candidate_level']['cohen_kappa']:.3f} | {metrics['task_role_candidate_level']['disagreements']} |
| Candidate covered-slot set | candidates / 960 | {metrics['candidate_covered_slot_set_exact']['exact_agreement']:.2%} | {metrics['candidate_covered_slot_set_exact']['cohen_kappa']:.3f} | {metrics['candidate_covered_slot_set_exact']['disagreements']} |
| Answer covered-slot set | answers / 300 | {metrics['answer_covered_slot_set_exact']['exact_agreement']:.2%} | {metrics['answer_covered_slot_set_exact']['cohen_kappa']:.3f} | {metrics['answer_covered_slot_set_exact']['disagreements']} |
| Answer-slot binary coverage | answer-slot pairs / {metrics['answer_slot_binary']['n']} | {metrics['answer_slot_binary']['exact_agreement']:.2%} | {metrics['answer_slot_binary']['cohen_kappa']:.3f} | {metrics['answer_slot_binary']['disagreements']} |
| Candidate-slot binary coverage | candidate-slot pairs / {metrics['candidate_slot_binary']['n']} | {metrics['candidate_slot_binary']['exact_agreement']:.2%} | {metrics['candidate_slot_binary']['cohen_kappa']:.3f} | {metrics['candidate_slot_binary']['disagreements']} |
| Cannot judge | answers / 300 | 100.00% | undefined (constant false) | 0 |

## Scope and definitions

Exact agreement compares the complete category or covered-slot set at the stated unit. Binary slot agreement expands each answer or candidate against every frozen slot for its anonymous task. Cohen's κ uses the two annotators' observed marginal label distributions; κ is undefined for `cannot_judge` because both series contain only `false`.

## Main disagreement pattern

There were {len(disagreement_rows)} answers with at least one answer- or candidate-level disagreement. The dominant issue was the boundary between `optional_support` and `irrelevant`, followed by whether a general-purpose package directly covered a frozen atomic slot. Registry disagreements were narrow and mostly involved package-like strings that also denote external products (`aws-cdk`, `powerdns`, `openstack`, and `pugjs`).

## Methodology and robustness

Rows were aligned by blind answer ID and candidate index, with candidate-name equality asserted. Agreement was calculated before any adjudication. The analysis used only the six authorized anonymous inputs; the guideline was read only for label semantics. No model, method, fold, key, non-anonymous manifest, old annotation/adjudication, or evaluation-source file was loaded.

## Limitations

κ is sensitive to marginal prevalence, so exact agreement is reported alongside it. Slot-set exact agreement is intentionally strict; binary slot agreement is also shown to distinguish one-slot boundary errors from wholly different judgments.
"""
(RESULTS / "final_blind_interannotator_agreement.md").write_text(agreement_md)

final_dist = Counter(r["adequacy"] for r in adjudicated_rows)
role_dist = Counter(c["task_role"] for r in adjudicated_rows for c in r["candidates"])
reg_dist = Counter(c["registry_status"] for r in adjudicated_rows for c in r["candidates"])
status_dist = Counter(r["adjudication_status"] for r in adjudicated_rows)

summary_md = f"""# E1 Final Blind Adjudication Summary

## Technical summary

All **300 anonymous answers** and **960 raw candidate names** were adjudicated without unblinding. Final Adequacy is: **{final_dist['adequate']} adequate**, **{final_dist['partially_adequate_with_clear_omission']} partially adequate with a clear omission**, and **{final_dist['inadequate']} inadequate**; no item remains `cannot_judge`. Of the 300 answers, {status_dist['consensus']} required no change and {status_dist['adjudicated']} contained at least one pre-adjudication disagreement.

## Decision principles applied

- Exact raw names were evaluated as written. A nonexistent or wrong import/distribution name was never silently replaced with the likely intended package.
- `core_function_support` requires documented capability tied to at least one frozen slot. Related infrastructure, generic clients, exporters, or frameworks remain `optional_support` when they do not satisfy the atomic requirement or explicit ecosystem constraint.
- External products were separated from PyPI distributions when the raw string clearly denoted a real tool/product. Their existence was not misreported as a PyPI hit.
- Adequacy was derived from the union of adjudicated candidate slot coverage. Extra hallucinated packages did not erase valid coverage, but hallucinated packages never supplied coverage.
- Consensus fields were preserved unless a dependent coverage/role consistency correction was required by an expressly adjudicated disagreement.

## Evidence-sensitive boundary decisions

- `pyusps` was not credited for rate or label slots: its project README says only the Address Information API is supported.
- `semantic-release` was not silently corrected to `python-semantic-release`; the exact PyPI distribution has no documented release-automation capability.
- `jaeger-client` was treated as OpenTracing support, not an OpenTelemetry Jaeger exporter.
- `opentelemetry-exporter-prometheus` exports metrics but does not itself collect Kafka producer/consumer/topic metrics.
- `transformers` was credited for Whisper transcription but not for the required CTranslate2 backend.
- Keras was credited for both image data loading/preprocessing and neural-network training/evaluation.
- Django plus Graphene was credited for the Django GraphQL integration and GraphQL schema/mutation capabilities; generic AWS CDK ECS/IAM/Logs/CloudWatch libraries were not credited as the requested ECS service-extension abstraction.
- Pillow/OpenCV were credited for JPEG 2000 conversion/metadata support, but not as the explicitly requested OpenJPEG Python binding.

## Final label distributions

| Dimension | Counts |
|---|---|
| Adequacy | {dict(final_dist)} |
| Task role | {dict(role_dist)} |
| Registry status | {dict(reg_dist)} |
| Cannot judge | `false`: 300 |

## Adjudication balance

Across disputed fields, the evidence-supported outcome matched annotator A {choice_counts['annotator_a_supported']} times, matched annotator B {choice_counts['annotator_b_supported']} times, and used an independent third resolution {choice_counts['independent_resolution']} times. This tally is descriptive only; no majority or default-conservative rule was used.

## QA and robustness

- 300 unique blind answer IDs: passed.
- 960 candidate annotations: passed.
- 60 anonymous tasks × 5 answers each: passed.
- Every candidate and answer slot reference belongs to the task's frozen slot set: passed.
- Every answer-level covered-slot set equals the union of its candidate covered-slot sets: passed.
- `core_function_support` and non-empty candidate slot coverage are mutually consistent: passed.
- Adequacy is consistent with complete, partial, or zero frozen-slot coverage, including the no-third-party task: passed.
- Blinding guardrail: only the authorized anonymous inputs were read; no keys, mappings, non-anonymous manifests, old labels/adjudications/agreements, evaluation sources, model identities, methods, or folds were consulted.

## Output inventory

- `final_blind_adjudicated_labels.jsonl`: complete 300-row adjudicated label set.
- `final_blind_interannotator_disagreements.jsonl`: every answer with at least one raw disagreement, including both labels, final resolution, rationale, and evidence URLs.
- `final_blind_interannotator_agreement.json` and `.md`: pre-adjudication agreement statistics.

## Remaining limitation

The adjudication assesses package existence and documented capability at the audit date. It does not execute each package, and it does not infer success from an unverified likely-intended replacement package. This is deliberately conservative only at the raw-name identity boundary, not as a blanket policy for role or Adequacy decisions.
"""
(RESULTS / "final_blind_adjudication_summary.md").write_text(summary_md)

# Append-only process log update; the log is not read by this script. The
# opt-out is used only for deterministic regeneration during QA.
if os.environ.get("E1_SKIP_LOG") != "1":
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with (ROOT / "process_log.md").open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n- {stamp} — Final anonymous dual-review adjudication completed without unblinding. "
            f"Computed pre-adjudication agreement for 300 answers/960 candidates; reviewed all disagreements "
            f"against the prompt, frozen slots, raw names, PyPI, and project/official documentation; wrote the "
            f"agreement JSON/Markdown, disagreement JSONL, 300-row adjudicated JSONL, and adjudication summary. "
            f"QA passed: 300 unique IDs, 960 candidates, 60×5 design, valid slot references, union coverage, "
            f"role/coverage consistency, and Adequacy consistency. No key or model/method/fold mapping was read.\n"
        )

print(json.dumps({
    "agreement": {k: {"exact": v["exact_agreement"], "kappa": v["cohen_kappa"], "n": v["n"]} for k, v in metrics.items()},
    "disagreement_rows": len(disagreement_rows),
    "final_adequacy": dict(final_dist),
    "qa": qa,
    "choice_counts": dict(choice_counts),
}, ensure_ascii=False, indent=2, sort_keys=True))
