import argparse, json, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
parser = argparse.ArgumentParser(description="Download only explicitly approved direct URLs.")
parser.add_argument("--dataset", required=True)
parser.add_argument("--confirm", action="store_true")
args = parser.parse_args()
items = json.loads((ROOT / "dataset_registry.json").read_text(encoding="utf-8"))
item = next((x for x in items if x["id"] == args.dataset), None)
if not item:
    raise SystemExit("Unknown dataset ID.")
if not args.confirm:
    raise SystemExit("Refusing to download without --confirm.")
if item.get("license_review") != "approved" or item.get("access_status") != "granted":
    raise SystemExit("Licence review must be approved and access_status must be granted first.")
url = item.get("direct_download_url")
if not url:
    raise SystemExit("No provider-approved direct_download_url recorded. Follow the provider's official download procedure.")
dest = PROJECT / "data" / "raw" / item["id"]
dest.mkdir(parents=True, exist_ok=True)
name = url.split("?")[0].rstrip("/").split("/")[-1] or f"{item['id']}.download"
target = dest / name
with requests.get(url, stream=True, timeout=60) as response:
    response.raise_for_status()
    with target.open("wb") as f:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
print(f"Downloaded to {target}")
