#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Global Matrix Reindexer
Merges and synchronizes Even and Odd parity feeds into the unified master index.
"""

import datetime
import json
import os
import sys

CDN_DIR = "cdn"
EVEN_PATH = os.path.join(CDN_DIR, "feed-even.json")
ODD_PATH = os.path.join(CDN_DIR, "feed-odd.json")
MASTER_PATH = os.path.join(CDN_DIR, "master-index.json")

def main() -> int:
    print("[REINDEX] Synchronizing parity feeds into global master matrix...")
    datasets = []
    
    if os.path.exists(EVEN_PATH):
        try:
            with open(EVEN_PATH, "r", encoding="utf-8") as f:
                datasets.extend(json.load(f).get("datasets", []))
        except Exception as e:
            print(f"[WARN] Could not load even feed: {e}")

    if os.path.exists(ODD_PATH):
        try:
            with open(ODD_PATH, "r", encoding="utf-8") as f:
                datasets.extend(json.load(f).get("datasets", []))
        except Exception as e:
            print(f"[WARN] Could not load odd feed: {e}")

    # Deduplicate and sort strictly by sequence
    unique_datasets = {d["repo_id"]: d for d in datasets if "repo_id" in d}
    sorted_datasets = sorted(unique_datasets.values(), key=lambda x: x.get("sequence", 0))

    if os.path.exists(MASTER_PATH):
        with open(MASTER_PATH, "r", encoding="utf-8") as f:
            master = json.load(f)
    else:
        master = {
            "system": "EATHESEN V3000 SOTA — Master Global Index",
            "anchor": "¢24",
            "boolean_checksum": 1,
            "cdn_endpoints": {}
        }

    master["total_repositories"] = len(sorted_datasets)
    master["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    master["datasets"] = sorted_datasets

    os.makedirs(CDN_DIR, exist_ok=True)
    with open(MASTER_PATH, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"[REINDEX] Master index successfully re-synced with {len(sorted_datasets)} total entries.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
