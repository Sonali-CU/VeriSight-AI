"""Check reachability of official dataset reference pages.
This does NOT determine legal permission, downloadability or dataset availability."""

import json, requests
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
items = json.loads((ROOT / "dataset_registry.json").read_text(encoding="utf-8"))
results = []
for item in items:
    row = {"id": item["id"], "name": item["name"], "url": item["source_url"],
           "license_review": item["license_review"], "access_status": item["access_status"]}
    try:
        r = requests.get(item["source_url"], timeout=20, allow_redirects=True,
                         headers={"User-Agent": "VeriSightAI-Dataset-Discovery/1.0"})
        row.update(http_status=r.status_code, reachable=r.ok, final_url=r.url)
    except requests.RequestException as exc:
        row.update(reachable=False, error=str(exc))
    results.append(row)
out = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "warning":
       "Reachability is not proof of licence approval, access permission, or direct download availability.",
       "datasets": results}
(ROOT / "discovery_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
