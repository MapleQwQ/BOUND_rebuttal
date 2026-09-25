"""Read installed distribution file manifests; never import package code."""
from __future__ import annotations

import importlib.metadata as metadata
import json
import re
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "results"


def module_paths(files):
    result = set()
    for file in files or []:
        name = str(file).replace("\\", "/")
        if ".dist-info/" in name or ".data/" in name or ".egg-info/" in name:
            continue
        if name.endswith("/__init__.py"):
            pieces = name[:-len("/__init__.py")].split("/")
        elif name.endswith(".py"):
            pieces = name[:-3].split("/")
        else:
            continue
        if pieces and all(piece.isidentifier() for piece in pieces):
            result.update(".".join(pieces[:n]) for n in range(1, len(pieces) + 1))
    return result


def main():
    roots = [Path("/home/shuhanliu/miniconda3")]
    roots.extend(Path("/home/shuhanliu/miniconda3/envs").glob("*"))
    entries = defaultdict(lambda: {"import_paths": set(), "environment_paths": set(), "versions": set()})
    for root in roots:
        for site in root.glob("lib/python3.*/site-packages"):
            if not re.search(r"python3\.\d+$", str(site.parent)):
                continue
            for dist in metadata.distributions(path=[str(site)]):
                name = dist.metadata.get("Name")
                if not name:
                    continue
                key = re.sub(r"[-_.]+", "-", name).lower()
                item = entries[key]
                item["import_paths"].update(module_paths(dist.files))
                item["environment_paths"].add(str(site))
                item["versions"].add(dist.version)
    data = {key: {"canonical_name": key, "import_paths": sorted(value["import_paths"]),
                  "environment_paths": sorted(value["environment_paths"]), "versions": sorted(value["versions"])}
            for key, value in entries.items()}
    (OUT / "local_distribution_metadata.json").write_text(json.dumps(data, ensure_ascii=False) + "\n")
    print(json.dumps({"distribution_count": len(data), "with_paths": sum(bool(x["import_paths"]) for x in data.values()),
                      "environment_count": len({p for x in data.values() for p in x["environment_paths"]})}, indent=2))


if __name__ == "__main__":
    main()
