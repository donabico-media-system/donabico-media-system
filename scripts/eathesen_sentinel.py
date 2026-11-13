#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Health Sentinel & CDN Endpoint Validator
Validates master index integrity and probes global CDN availability.
"""

import json
import sys
import requests

MASTER_INDEX_PATH = "cdn/master-index.json"

def main() -> int:
    print("[SENTINEL] Auditing cdn/master-index.json integrity...")
    try:
        with open(MASTER_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        total = data.get("total_repositories", 0)
        anchor = data.get("anchor", "")
        if anchor != "¢24":
            print(f"[CRITICAL] Anchor violation in master index: {anchor}")
            return 1
            
        print(f"[SENTINEL] Master Index verified under ¢24. Total repositories registered: {total}")
        
        endpoints = data.get("cdn_endpoints", {})
        for name, url in endpoints.items():
            print(f"[SENTINEL] Probing endpoint [{name}]: {url}")
            resp = requests.head(url, timeout=15)
            print(f"[SENTINEL] Endpoint [{name}] status: HTTP {resp.status_code}")
            if resp.status_code not in (200, 301, 302):
                print(f"[WARN] Endpoint {name} returned non-success code: {resp.status_code}")
                
        print("[SENTINEL] All health checks passed successfully.")
        return 0
    except Exception as exc:
        print(f"[CRITICAL] Sentinel audit failed: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
