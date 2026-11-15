import argparse, csv, json
from pathlib import Path
from collections import defaultdict

p = argparse.ArgumentParser()
p.add_argument("--root", required=True)
p.add_argument("--manifest", required=True)
args = p.parse_args()
root = Path(args.root)
manifest = Path(args.manifest)
errors, counts, group_splits = [], defaultdict(int), defaultdict(set)
with manifest.open(newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    required = {"path", "label", "group_id", "split", "dataset"}
    if not required.issubset(reader.fieldnames or []):
        raise SystemExit(f"Manifest requires columns: {sorted(required)}")
    for n, row in enumerate(reader, start=2):
        rel = Path(row["path"])
        path = rel if rel.is_absolute() else root / rel
        label, split, group = row["label"].lower(), row["split"].lower(), row["group_id"]
        if label not in {"real", "fake"}: errors.append(f"line {n}: invalid label {label}")
        if split not in {"train", "val", "test"}: errors.append(f"line {n}: invalid split {split}")
        if not path.is_file(): errors.append(f"line {n}: missing file {path}")
        if group:
            group_splits[group].add(split)
        counts[(row["dataset"], split, label)] += 1
for group, splits in group_splits.items():
    if len(splits) > 1:
        errors.append(f"group leakage: {group} occurs in {sorted(splits)}")
print(json.dumps({"counts": [{"dataset":k[0],"split":k[1],"label":k[2],"files":v} for k,v in counts.items()],
                  "errors": errors, "valid": not errors}, indent=2))
if errors: raise SystemExit(1)
