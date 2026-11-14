#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Global Matrix Reindexer & Cache Purge
Rebuilds the entire Sharded Architecture from the Even/Odd parity feeds.
Ensures master-index.json only contains the latest 100 items + shard endpoints.
"""

import datetime
import json
import os
import sys
import xml.etree.ElementTree as ET

CDN_DIR = "cdn"
EVEN_PATH = os.path.join(CDN_DIR, "feed-even.json")
ODD_PATH = os.path.join(CDN_DIR, "feed-odd.json")
MASTER_PATH = os.path.join(CDN_DIR, "master-index.json")
RSS_FEED_FILE = os.path.join(CDN_DIR, "feed.xml")

GITHUB_OWNER = "donabico-media-system"
GITHUB_REPO = "donabico-media-system"
HF_ORG = "donabico"


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
    merged_list = sorted(unique_datasets.values(), key=lambda x: x.get("sequence", 0))

    print(f"[REINDEX] Found {len(merged_list)} unique datasets in parity caches.")

    # =========================================================================
    # NÂNG CẤP: XÂY DỰNG LẠI CẤU TRÚC SHARDING (1000 BÀI / SHARD)
    # =========================================================================
    SHARD_SIZE = 1000
    total_shards = (len(merged_list) + SHARD_SIZE - 1) // SHARD_SIZE
    shard_endpoints = {}

    # Dọn dẹp sạch sẽ các file part cũ trước khi tạo mới (Cache Purge)
    for f in os.listdir(CDN_DIR):
        if f.startswith("master-index-part-") and f.endswith(".json"):
            os.remove(os.path.join(CDN_DIR, f))
            print(f"[PURGE] Removed old shard: {f}")

    for i in range(total_shards):
        part_data = merged_list[i * SHARD_SIZE : (i + 1) * SHARD_SIZE]
        part_name = f"master-index-part-{i+1:04d}.json"
        part_file = os.path.join(CDN_DIR, part_name)
        
        with open(part_file, "w", encoding="utf-8") as f:
            json.dump({"total": len(part_data), "datasets": part_data}, f, ensure_ascii=False, indent=2)
            
        shard_endpoints[f"shard_{i+1:04d}"] = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/cdn/{part_name}"
        print(f"[SHARD] Created {part_name} with {len(part_data)} items.")

    # =========================================================================
    # NÂNG CẤP: CẬP NHẬT MASTER INDEX (CHỈ CHỨA 100 BÀI MỚI NHẤT + ENDPOINTS)
    # =========================================================================
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    master_payload = {
        "system": "EATHESEN V3000 SOTA — Master Global Index (Rebuilt)",
        "anchor": "¢24", 
        "boolean_checksum": 1, 
        "updated_at": now_iso,
        "total_repositories": len(merged_list), 
        "total_shards": total_shards,
        "shard_endpoints": shard_endpoints,
        "recent_datasets": merged_list[-100:], # Chỉ lưu 100 bài mới nhất
    }
    
    with open(MASTER_PATH, "w", encoding="utf-8") as f: 
        json.dump(master_payload, f, ensure_ascii=False, indent=2)

    print(f"[REINDEX] Master index successfully rebuilt with {total_shards} shards.")

    # =========================================================================
    # NÂNG CẤP: XÂY DỰNG LẠI RSS FEED (50 BÀI MỚI NHẤT)
    # =========================================================================
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "EATHESEN V3000 SOTA — Autonomous Knowledge Stream [¢24]"
    ET.SubElement(channel, "link").text = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
    ET.SubElement(channel, "description").text = "Deterministic, low-entropy mathematical and philosophical datasets verified under Anchor ¢24."
    ET.SubElement(channel, "lastBuildDate").text = now_iso

    for item_data in reversed(merged_list[-50:]):
        item_el = ET.SubElement(channel, "item")
        ET.SubElement(item_el, "title").text = f"[¢24][Dao {item_data.get('dao_index', 1)}] {item_data.get('title', '')}"
        ET.SubElement(item_el, "link").text = item_data.get("hf_url", "")
        ET.SubElement(item_el, "guid").text = item_data["repo_id"]
        ET.SubElement(item_el, "pubDate").text = item_data.get("audited_at", now_iso)
        ET.SubElement(item_el, "description").text = f"Repo: {item_data['repo_id']} | Shannon Entropy H(X)={item_data.get('shannon_entropy', 0.0)} | Anchor: ¢24"

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(RSS_FEED_FILE, encoding="utf-8", xml_declaration=True)
    
    print("[REINDEX] RSS Feed regenerated successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())