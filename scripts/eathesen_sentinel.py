#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Health Sentinel & CDN Endpoint Validator
Validates master index integrity, verifies shard endpoints, and probes global CDN availability.
"""

import json
import sys
import requests

MASTER_INDEX_PATH = "cdn/master-index.json"

def check_url(name: str, url: str) -> bool:
    """Kiểm tra một URL và trả về True nếu HTTP 200 OK."""
    print(f"[SENTINEL] Probing endpoint [{name}]: {url}")
    try:
        resp = requests.head(url, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            print(f"[SENTINEL] Endpoint [{name}] status: HTTP 200 OK")
            return True
        else:
            print(f"[WARN] Endpoint [{name}] returned non-success code: HTTP {resp.status_code}")
            return False
    except Exception as exc:
        print(f"[ERROR] Endpoint [{name}] connection failed: {exc}")
        return False

def main() -> int:
    print("[SENTINEL] Auditing cdn/master-index.json integrity...")
    try:
        with open(MASTER_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        total = data.get("total_repositories", 0)
        anchor = data.get("anchor", "")
        shards_count = data.get("total_shards", 0)
        
        # 1. Kiểm tra ADN ¢24
        if anchor != "¢24":
            print(f"[CRITICAL] Anchor violation in master index: {anchor}")
            return 1
            
        print(f"[SENTINEL] Master Index verified under ¢24. Total repos: {total} | Total shards: {shards_count}")
        
        # 2. Kiểm tra sự tồn tại của 100 bài mới nhất (recent_datasets)
        recent = data.get("recent_datasets", [])
        if not recent:
            print("[WARN] No recent datasets found in master index.")
        
        # 3. Kiểm tra các file Shard (master-index-part-XXXX.json)
        endpoints = data.get("shard_endpoints", {})
        if not endpoints:
            print("[WARN] No shard_endpoints found in master index. System might be using legacy index.")
            
        failed_count = 0
        for name, url in endpoints.items():
            if not check_url(name, url):
                failed_count += 1
                
        if failed_count > 0:
            print(f"[CRITICAL] {failed_count} shard endpoints failed validation.")
            return 1 # Trả về mã lỗi để GitHub Actions báo X đỏ
                
        print("[SENTINEL] All health checks passed successfully. CDN Matrix is healthy.")
        return 0
    except Exception as exc:
        print(f"[CRITICAL] Sentinel audit failed: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())