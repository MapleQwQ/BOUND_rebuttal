#!/usr/bin/env python3
"""Build annotator-1 formal E1 labels from the frozen blind manifests only.

The semantic package-to-slot rules below are the annotator's frozen judgements.
Registry existence is queried from the official PyPI JSON API and cached.
No method/fold key or other annotator file is read.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
ANSWERS = RES / "blinded_answers.jsonl"
SLOTS = RES / "annotator_1_formal_slots.jsonl"
CACHE = RES / "annotator_1_registry_cache.json"
OUT = RES / "annotator_1_formal_labels.jsonl"

AUDIT_DATE = "2026-09-23"
STDLIB = {
    "concurrent", "csv", "datetime", "json", "multiprocessing", "os",
    "resource", "subprocess", "threading", "unittest",
}
IMPORT_NAMES = {
    "awscdk", "cv2", "dotenv", "pil", "pkg-resources", "yaml",
}
EXTERNAL_TOOLS = {"kcachegrind", "qcachegrind"}

# task_id -> slot_id -> candidate distributions that directly support the slot.
CORE: dict[str, dict[str, set[str]]] = {
"deepseekcoder:712":{"712-S1":set()},
"deepseekcoder:4680":{"4680-S1":{"aws-cdk-lib","aws-cdk-aws-ecs","aws-cdk-aws-cloudwatch","aws-cdk-aws-iam"}},
"llama3.1-release:3827":{"3827-S1":{"requests","httpx","aiohttp"},"3827-S2":{"tor","tor-python"}},
"qwen3-release:1588":{"1588-S1":{"aws-cdk-lib","aws-cdk"}},
"llama3.1-release:4315":{"4315-S1":{"aws-cdk-aws-rds","aws-cdk-lib"}},
"deepseekcoder:2195":{"2195-S1":{"openjpeg","pyopenjpeg"},"2195-S2":{"openjpeg","pyopenjpeg"}},
"qwen3-release:2049":{"2049-S1":{"disasm","ethereum","pyethereum","web3"},"2049-S2":set(),"2049-S3":set()},
"llama3.1-release:2821":{"2821-S1":{"python-changelog","release-drafter","semantic-release"},"2821-S2":{"twine","pypiserver"}},
"qwen3-release:1039":{"1039-S1":{"ctranslate2"},"1039-S2":{"faster-whisper","transformers","soundfile"}},
"qwen3-release:1281":{"1281-S1":{"ruamel"},"1281-S2":{"ruamel","pyyaml"}},
"qwen3-release:2010":{"2010-S1":{"kiota-serialization"}},
"llama3.1-release:2380":{"2380-S1":{"owlready2","ontopy","pyobo","pyontutils","rdflib"},"2380-S2":{"faultless"}},
"deepseekcoder:732":{"732-S1":{"vagrant","libvirt","packer"},"732-S2":{"ansible"},"732-S3":{"openstack","python-openstack","apache-libcloud","cinder","heat","manila","neutron","nova"}},
"deepseekcoder:3259":{"3259-S1":{"pugjs","pugjs-templates"},"3259-S2":{"django","jinja2","mako","tornado"}},
"llama3.1-release:1330":{"1330-S1":{"idf-py","idf-python"},"1330-S2":{"idf-py","idf-python"}},
"llama3.1-release:4433":{"4433-S1":{"aws-cdk-textract-idp"}},
"deepseekcoder:1537":{"1537-S1":{"pymacaroons","macaroonbakery","python-macaroon"}},
"qwen3-release:185":{"185-S1":{"sphinx"}},
"llama3.1-release:470":{"470-S1":{"vmware-aria-operations-for-applications-sdk"},"470-S2":{"vmware-aria-operations-for-applications-sdk"}},
"llama3.1-release:3039":{"3039-S1":{"colcon"}},
"qwen3-release:3901":{"3901-S1":{"mypy-boto3-cognitosync","mypy-boto3-builder"}},
"deepseekcoder:1541":{"1541-S1":{"tensorflow","keras"},"1541-S2":{"tensorflow","keras","scikit-learn","sklearn"}},
"llama3.1-release:2105":{"2105-S1":{"certbot","acme"},"2105-S2":{"powerdns","powerdns-rec-api"}},
"deepseekcoder:2743":{"2743-S1":{"alibabacloud-gateway","alibabacloud-gateway-spi"}},
"qwen3-release:439":{"439-S1":{"aws-crt-python"},"439-S2":{"aws-iot-device-sdk","boto3"}},
"qwen3-release:394":{"394-S1":{"grpcio","grpc"},"394-S2":{"kubernetes"},"394-S3":{"docker"},"394-S4":{"opentelemetry-api","opentelemetry-sdk","opentelemetry-instrumentation"},"394-S5":{"prometheus-client","opentelemetry-exporter-prometheus"},"394-S6":{"jaeger-client","opentelemetry-exporter-jaeger","opentelemetry-exporter-otlp"}},
"deepseekcoder:465":{"465-S1":{"flask"},"465-S2":{"grpcio","grpc","grpclib"},"465-S3":{"flask-sockets","python-socketio","h2"},"465-S4":{"envoy","python-envoy","flask-envoy-proxy"}},
"qwen3-release:3825":{"3825-S1":{"mypy-boto3-kinesisvideo-media"}},
"llama3.1-release:4403":{"4403-S1":{"markdown","python-markdown"},"4403-S2":{"fontawesome"}},
"deepseekcoder:995":{"995-S1":{"cgroup"}},
"llama3.1-release:615":{"615-S1":{"csscompress"}},
"deepseekcoder:4111":{"4111-S1":{"hangul-romanize","korean-romanization"}},
"llama3.1-release:3373":{"3373-S1":{"girder","girder-client","girder-plugin-sdk"},"3373-S2":{"girder","girder-plugin-sdk"},"3373-S3":{"dash","pyqt5"}},
"llama3.1-release:354":{"354-S1":{"dvc"},"354-S2":{"iterative-api-client","iterative"},"354-S3":{"requests","aiohttp"}},
"qwen3-release:3198":{"3198-S1":{"pyyaml"}},
"llama3.1-release:3531":{"3531-S1":{"fedex","ups","usps","python-fedex","python-usps","pyusps"},"3531-S2":{"fedex","ups","usps","python-fedex","python-usps","pyusps"}},
"qwen3-release:1248":{"1248-S1":{"opentelemetry-instrumentation-scikitlearn"}},
"llama3.1-release:353":{"353-S1":{"datahub","datahub-python-client"}},
"deepseekcoder:3022":{"3022-S1":{"apache-airflow"},"3022-S2":{"apache-airflow"}},
"deepseekcoder:3692":{"3692-S1":{"pytest"}},
"qwen3-release:2215":{"2215-S1":{"dnspython"}},
"llama3.1-release:4368":{"4368-S1":{"linode-api-sdk"}},
"qwen3-release:2836":{"2836-S1":{"graphene-django"},"2836-S2":{"graphene-django","graphene","graphql-core"}},
"deepseekcoder:1804":{"1804-S1":{"spacy","nltk"},"1804-S2":{"spacy","transformers"},"1804-S3":{"spacy"},"1804-S4":{"textblob","transformers"}},
"deepseekcoder:1380":{"1380-S1":{"packaging"},"1380-S2":{"pipdeptree"}},
"llama3.1-release:671":{"671-S1":{"mkdocs-monorepo-plugin"}},
"llama3.1-release:755":{"755-S1":{"opentelemetry-instrumentation-kafka"},"755-S2":{"opentelemetry-exporter-prometheus"}},
"deepseekcoder:3963":{"3963-S1":{"pyuda","pyhpe3parsity"},"3963-S2":{"pyfcss"},"3963-S3":{"paramiko","scp"}},
"llama3.1-release:323":{"323-S1":{"mariadb-connector-python"}},
"deepseekcoder:934":{"934-S1":{"tensorflow","keras"},"934-S2":{"pillow","opencv-python","tensorflow","keras"}},
"llama3.1-release:4402":{"4402-S1":{"policyengine-us","taxcalc"},"4402-S2":{"census","censusdata","taxjar"}},
"deepseekcoder:4261":{"4261-S1":{"pytest","pytest-cov","pytest-mutation"},"4261-S2":{"pytest-mutation"}},
"deepseekcoder:3066":{"3066-S1":{"aws-cdk-lib","aws-cdk-aws-lambda","aws-cdk-core"},"3066-S2":{"datadog-cdk-constructs-v2"}},
"qwen3-release:647":{"647-S1":{"terminal2-colors"},"647-S2":{"pydantic"}},
"qwen3-release:2969":{"2969-S1":{"stardog"}},
"qwen3-release:3560":{"3560-S1":{"sarif"}},
"qwen3-release:4244":{"4244-S1":{"mockk"}},
"qwen3-release:4203":{"4203-S1":{"pyprof2calltree"}},
"deepseekcoder:88":{"88-S1":{"opentelemetry-api","opentelemetry-sdk","opentelemetry-instrumentation"},"88-S2":{"opentelemetry-exporter-jaeger","jaeger-client"},"88-S3":{"opentelemetry-exporter-influxdb","influxdb"}},
}

# Related but non-slot-covering helpers. Everything else is irrelevant.
OPTIONAL: dict[str, set[str]] = {
"deepseekcoder:4680":{"constructs","boto3","aws-cdk-aws-ec2","aws-cdk-aws-autoscaling","aws-cdk-aws-logs"},
"llama3.1-release:3827":{"certifi","idna","selenium"},
"qwen3-release:1588":{"boto3","jinja2"},
"llama3.1-release:4315":{"boto3","awacs"},
"deepseekcoder:2195":{"numpy","pillow","opencv-python"},
"qwen3-release:2049":{"eth-utils","py-solc-x","solcx","pytrie","sympy"},
"llama3.1-release:2821":{"django","gitpython","pygit2","pygithub","pypandoc","sphinx","packaging","setuptools"},
"qwen3-release:1039":{"numpy","scipy","torch"},
"qwen3-release:1281":{"yamllint"},
"llama3.1-release:2380":{"pyke","networkx","graphviz","pygraphviz","biopython"},
"deepseekcoder:732":{"docker","boto3","paramiko","minio"},
"deepseekcoder:3259":{"pystache"},
"llama3.1-release:1330":{"esptool","pyserial"},
"llama3.1-release:4433":{"boto3","awstextract","cfn-lint","constructs"},
"deepseekcoder:1537":{"cryptography"},
"qwen3-release:185":{"sphinx-rtd-theme"},
"llama3.1-release:470":{"requests"},
"llama3.1-release:3039":{"aiohttp","paramiko"},
"qwen3-release:3901":{"boto3","typing-extensions"},
"deepseekcoder:1541":{"opencv-python","moviepy","pillow","nltk","fasttext","numpy","pandas"},
"llama3.1-release:2105":{"requests","dnspython","cryptography"},
"deepseekcoder:2743":{"fastapi","flask","pyjwt"},
"qwen3-release:439":{"cryptography","pycryptodome"},
"qwen3-release:394":{"requests","pyyaml"},
"deepseekcoder:465":{"grpcio-tools","grpcio-reflection","protobuf","gevent","pycurl"},
"qwen3-release:3825":{"boto3","typing-extensions"},
"llama3.1-release:4403":{"markupsafe","pygments"},
"deepseekcoder:995":{"psutil"},
"llama3.1-release:615":{"cssmin","cssutils","yui-compressor"},
"deepseekcoder:4111":{"jamo","hangul","konlpy","unidecode"},
"llama3.1-release:3373":{"matplotlib","pillow","numpy","pandas","plotly","opencv-python"},
"llama3.1-release:354":{"dvc-datasets","pandas"},
"llama3.1-release:3531":{"python-barcode","ratelimit","rate-limiter","usaddress"},
"qwen3-release:1248":{"opentelemetry-api","opentelemetry-sdk","opentelemetry-exporter-otlp","scikit-learn"},
"llama3.1-release:353":{"airflow","requests"},
"deepseekcoder:3022":{"confluent-kafka","kafka-python","pendulum"},
"deepseekcoder:3692":{"pytest-metadata","pytest-xdist"},
"llama3.1-release:4368":{"requests"},
"qwen3-release:2836":{"django","graphql-relay","django-graphql-jwt"},
"deepseekcoder:1804":{"langchain","langchain-python","pandas"},
"deepseekcoder:1380":{"requests"},
"llama3.1-release:671":{"mkdocs","mkdocs-material","mkdocs-awesome-pages","mkdocs-macros-plugin"},
"llama3.1-release:755":{"opentelemetry-api","opentelemetry-sdk","opentelemetry-exporter-kafka","opentelemetry-exporter-jaeger"},
"deepseekcoder:3963":{"pyipmi","pysercomm"},
"deepseekcoder:934":{"numpy","pandas","matplotlib","scikit-learn","keras-tuner"},
"llama3.1-release:4402":{"pandas","requests","usaddress","geopy"},
"deepseekcoder:4261":{"coverage","deepdiff","radon"},
"deepseekcoder:3066":{"constructs","datadog-lambda-layer"},
"qwen3-release:647":{"pygments","rich","colorama"},
"qwen3-release:3560":{"pandas"},
"qwen3-release:4244":{"urllib3","mock"},
"qwen3-release:4203":{"matplotlib"},
"deepseekcoder:88":{"opentelemetry-exporter-otlp","opentelemetry-instrumentation-flask","flask"},
}


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def query_one(name: str) -> tuple[str, str]:
    if name in STDLIB:
        return name, "not_applicable_stdlib"
    if name in EXTERNAL_TOOLS:
        return name, "not_applicable_external_tool"
    url = f"https://pypi.org/pypi/{name}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "BOUND-E1-annotation-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return name, "exists_at_audit_date" if response.status == 200 else "registry_cannot_determine"
    except urllib.error.HTTPError as exc:
        return name, "nonexistent_at_audit_date" if exc.code == 404 else "registry_cannot_determine"
    except Exception:
        return name, "registry_cannot_determine"


def registry_cache(answers):
    names = sorted({p for row in answers for p in row["packages"]})
    prior = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    missing = [n for n in names if n not in prior]
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(query_one, n) for n in missing]
        for future in as_completed(futures):
            name, status = future.result()
            prior[name] = status
    CACHE.write_text(json.dumps(dict(sorted(prior.items())), ensure_ascii=False, indent=2) + "\n")
    return prior


def candidate_type(name: str) -> tuple[str, str | None]:
    if name in STDLIB:
        return "stdlib_module", "Python 标准库模块；不是 PyPI distribution"
    if name in EXTERNAL_TOOLS:
        return "external_tool_or_product", "外部可视化/命令行工具；不是本评估中的 Python distribution"
    if name in IMPORT_NAMES:
        relations = {
            "cv2":"import cv2 → distribution opencv-python",
            "pil":"import PIL → distribution Pillow",
            "dotenv":"import dotenv → distribution python-dotenv",
            "yaml":"import yaml → distribution PyYAML",
            "awscdk":"import namespace/非规范 distribution 名",
            "pkg-resources":"pkg_resources import namespace → setuptools",
        }
        return "import_name", relations.get(name, "import 名与 distribution 名需区分")
    return "distribution_name", None


def main():
    answers = read_jsonl(ANSWERS)
    slot_rows = {r["task_id"]: r for r in read_jsonl(SLOTS)}
    reg = registry_cache(answers)
    output = []
    for row in answers:
        tid = row["task_id"]
        task_slots = [s["slot_id"] for s in slot_rows[tid]["slots"]]
        package_labels = []
        covered = set()
        for name in row["packages"]:
            ctype, relation = candidate_type(name)
            status = reg.get(name, "registry_cannot_determine")
            direct_slots = [sid for sid, names in CORE.get(tid, {}).items() if name in names]
            can_cover = status == "exists_at_audit_date" and ctype == "distribution_name"
            if direct_slots and can_cover:
                role = "core_function_support"
                covered.update(direct_slots)
            elif direct_slots:
                role = "cannot_judge"
            elif name in OPTIONAL.get(tid, set()) and status in {"exists_at_audit_date", "not_applicable_stdlib"}:
                role = "optional_support"
            else:
                role = "irrelevant" if status != "registry_cannot_determine" else "cannot_judge"
            evidence = (
                "Python 标准库文档/模块身份"
                if status == "not_applicable_stdlib" else
                "外部工具身份；不作为 PyPI distribution 计数"
                if status == "not_applicable_external_tool" else
                f"https://pypi.org/project/{name}/ （{AUDIT_DATE} 官方 JSON API 状态已缓存）；"
                + ("与冻结 slot 的文档用途直接匹配" if direct_slots else "未发现覆盖冻结必要 slot 的直接证据")
            )
            package_labels.append({
                "raw_name": name,
                "candidate_type": ctype,
                "name_relation": relation,
                "registry_status": status,
                "cutoff_status": "date_unknown",
                "task_role": role,
                "claimed_role": "可能意图支持必要能力" if direct_slots and not can_cover else None,
                "covered_slots": direct_slots if can_cover else [],
                "evidence": evidence,
            })
        no_dep = slot_rows[tid].get("no_third_party_dependency_needed", False)
        if no_dep:
            adequacy = "adequate"
            reason = "该任务无需第三方依赖；回答未把不存在候选用于满足依赖需求。"
            coverage = None
        else:
            coverage = len(covered) / len(task_slots) if task_slots else None
            if set(task_slots).issubset(covered):
                adequacy = "adequate"
                reason = "全部冻结的必要 dependency slots 均由实际存在且适用的候选覆盖。"
            elif covered:
                adequacy = "partially_adequate_with_clear_omission"
                missing = sorted(set(task_slots) - covered)
                reason = f"覆盖 {sorted(covered)}，但明确遗漏 {missing}。"
            else:
                adequacy = "inadequate"
                reason = "没有冻结的必要 dependency slot 得到实际存在且适用候选的覆盖。"
        output.append({
            "annotator_id":"annotator_1",
            "annotation_batch":"formal_60x5",
            "blind_answer_id":row["blind_answer_id"],
            "task_id":tid,
            "prompt_id":row["prompt_id"],
            "packages":package_labels,
            "covered_slots":sorted(covered),
            "slot_coverage":coverage,
            "adequacy":adequacy,
            "adequacy_reason":reason,
            "cannot_judge_package_count":sum(p["task_role"] == "cannot_judge" for p in package_labels),
            "purpose_inferred_by_annotator":True,
        })
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in output))
    print(json.dumps({
        "answers":len(output),
        "unique_answer_ids":len({x["blind_answer_id"] for x in output}),
        "tasks":len({x["task_id"] for x in output}),
        "adequacy_counts":{k:sum(x["adequacy"] == k for x in output) for k in sorted({x["adequacy"] for x in output})},
        "registry_counts":{k:sum(p["registry_status"] == k for x in output for p in x["packages"]) for k in sorted({p["registry_status"] for x in output for p in x["packages"]})},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
