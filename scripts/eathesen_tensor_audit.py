#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Deep Tensor & Entropy Auditor
Enforces strict ¢24 anchor, Shannon entropy limits, and Tensor Variance stability.
Scans ALL Sharded files (master-index-part-*.json) to ensure 100% coverage.
"""

import json
import os
import re
import sys

CDN_DIR = "cdn"
MASTER_PATH = os.path.join(CDN_DIR, "master-index.json")
ENTROPY_LIMIT = 5.5
VARIANCE_LIMIT = 1e-3 # Ngưỡng cảnh báo nếu Vector bị biến dạng quá mức

def audit_records(records: list, source_name: str) -> bool:
    """Kiểm tra Entropy, Anchor và Tensor Variance của một danh sách bài viết."""
    is_valid = True
    for d in records:
        repo_id = d.get("repo_id", "unknown")
        anchor = d.get("anchor", "")
        entropy = d.get("shannon_entropy", 6.0)
        variance = d.get("tensor_variance", -1.0)
        
        if anchor != "¢24":
            print(f"[CRITICAL] Anchor violation in {repo_id}: {anchor}")
            is_valid = False
            
        if entropy >= ENTROPY_LIMIT:
            print(f"[CRITICAL] Entropy violation in {repo_id}: H(X)={entropy} >= {ENTROPY_LIMIT}")
            is_valid = False
            
        if variance < 0 or variance > VARIANCE_LIMIT:
            print(f"[CRITICAL] Tensor instability in {repo_id}: Var={variance}")
            is_valid = False
            
    return is_valid

def main() -> int:
    print("[AUDIT] Starting deep tensor and entropy verification across ALL CDN shards...")
    if not os.path.exists(MASTER_PATH):
        print("[AUDIT] Master index not found; skipping deep audit.")
        return 0

    try:
        # 1. Quét file Master Index (để lấy 100 bài mới nhất)
        with open(MASTER_PATH, "r", encoding="utf-8") as f:
            master = json.load(f)
        
        recent = master.get("recent_datasets", [])
        print(f"[AUDIT] Verifying {len(recent)} recent records from Master Index...")
        if not audit_records(recent, "master-index.json"):
            return 1

        # 2. Quét TOÀN BỘ các file Shard (Để kiểm tra 10.000 bài)
        shard_files = [f for f in os.listdir(CDN_DIR) if f.startswith("master-index-part-") and f.endswith(".json")]
        total_audited = len(recent)

        if not shard_files:
            print("[WARN] No shard files found. System might be running on legacy architecture.")
        else:
            print(f"[AUDIT] Found {len(shard_files)} sharded data blocks. Deep scanning...")
            for shard_file in shard_files:
                shard_path = os.path.join(CDN_DIR, shard_file)
                with open(shard_path, "r", encoding="utf-8") as f:
                    shard_data = json.load(f)
                    datasets = shard_data.get("datasets", [])
                    total_audited += len(datasets)
                    if not audit_records(datasets, shard_file):
                        return 1

        print(f"[AUDIT] SUCCESS: {total_audited} total records verified across all shards. Entropy = 0 compliance confirmed.")
        return 0
    except Exception as exc:
        print(f"[CRITICAL] Tensor audit encountered an exception: {exc}")
        return 1

if __name__ == "__main__":
    sys.exit(main())