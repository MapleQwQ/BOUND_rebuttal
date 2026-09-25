"""Rank unresolved import paths for transparent human adjudication."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "results"
mapping = {r["import_path"]: r for r in csv.DictReader((OUT / "audited_mapping.csv").open())}
count = Counter()
examples = defaultdict(list)
for row in csv.DictReader((OUT / "per_generation_audit.csv").open()):
    for path in json.loads(row["unresolved_imports"]):
        count[path] += 1
        if len(examples[path]) < 3:
            examples[path].append(f"{row['model']}/{row['method']}/{row['fold']}/{row['generation_id']}")
rows = [dict(import_path=path, answer_occurrences=n, status=mapping[path]["status"],
             candidate_distributions=mapping[path]["distributions"], evidence=mapping[path]["evidence"],
             example_generations=" | ".join(examples[path]), human_decision="", human_evidence="")
        for path, n in count.most_common()]
with (OUT / "manual_review_queue.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
print("unresolved unique paths", len(rows), "affected answers", sum(1 for row in csv.DictReader((OUT / "per_generation_audit.csv").open()) if row["unresolved_imports"] != "{}"))
