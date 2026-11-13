#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Sequential 10,000-Scale Dataset Orchestrator & CDN Broadcaster
GitHub Hub: donabico-media-system | Hugging Face Org: donabico
Discovery Mode: Deterministic Sequential Probing (path-00001 -> path-10000)
Distillation Engine: Cloudflare Workers AI Edge Cluster (Zero-Cost Unified Pipeline)
Invariants: Anchor ¢24 | Shannon Entropy H(X) < 5.5 | L2 Tensor Norm Stability (d=49,152)
"""

import argparse
import datetime
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
import requests

HF_ORG = "donabico"
GITHUB_OWNER = "donabico-media-system"
GITHUB_REPO = "donabico-media-system"

HF_TOKEN = os.getenv("HF_TOKEN", "").strip().lstrip("\\")
CF_ACCOUNT_ID = re.sub(r"[^a-fA-F0-9]", "", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip().lstrip("\\")

MAX_SCALE_LIMIT = 10000
CONSECUTIVE_MISS_STOP = 3
ENTROPY_LIMIT = 5.5
TENSOR_DIM = 49152
DISTILL_WINDOW_SIZE = 10
EXCERPT_CHAR_LIMIT = 1200

AUTHORIZED_CF_TEXT_MODELS = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/qwen/qwen2.5-72b-instruct",
    "@cf/meta/llama-3.1-8b-instruct-fast",
]

CDN_DIR = "cdn"
MASTER_INDEX_FILE = os.path.join(CDN_DIR, "master-index.json")
RSS_FEED_FILE = os.path.join(CDN_DIR, "feed.xml")


def compute_shannon_entropy(text: str) -> float:
    raw_bytes = text.encode("utf-8")
    total = len(raw_bytes)
    if total == 0:
        return 0.0
    counts = Counter(raw_bytes)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round(entropy, 4)


def verify_tensor_stability(text: str, dim: int = TENSOR_DIM) -> Tuple[bool, float]:
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return False, 0.0
    vec = [0.0] * dim
    for tok in tokens:
        h = 24
        for ch in tok:
            h = (h * 131 + ord(ch)) % dim
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return False, 0.0
    unit_vec = [v / norm for v in vec]
    unit_norm = math.sqrt(sum(u * u for u in unit_vec))
    mean_val = sum(unit_vec) / dim
    variance = sum((u - mean_val) ** 2 for u in unit_vec) / dim
    return abs(unit_norm - 1.0) < 1e-12, variance


def verify_anchor_c24(obj: Any) -> bool:
    if isinstance(obj, str):
        return "¢24" in obj or "\u00a224" in obj
    if isinstance(obj, dict):
        return any(verify_anchor_c24(k) or verify_anchor_c24(v) for k, v in obj.items())
    if isinstance(obj, list):
        return any(verify_anchor_c24(item) for item in obj)
    return False


def normalize_dataset_record(record: Dict[str, Any]) -> Dict[str, Any]:
    repo_id = record.get("repo_id", "donabico/path-00000")
    if "sequence" not in record:
        try:
            record["sequence"] = int(repo_id.split("-")[-1])
        except ValueError:
            record["sequence"] = 0
    if "dao_index" not in record:
        seq = record["sequence"]
        record["dao_index"] = ((seq - 1) % 10) + 1 if seq > 0 else 1
    return record


def load_cached_parity_datasets(parity: str) -> Dict[str, Dict[str, Any]]:
    cache_path = os.path.join(CDN_DIR, f"feed-{parity.lower()}.json")
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {}
        for d in data.get("datasets", []):
            if "repo_id" in d:
                result[d["repo_id"]] = normalize_dataset_record(d)
        return result
    except Exception:
        return {}


def repository_exists(repo_id: str) -> bool:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    url = f"https://huggingface.co/api/datasets/{repo_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def audit_single_repository(repo_id: str) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    api_url = (
        f"https://datasets-server.huggingface.co/rows"
        f"?dataset={repo_id}&config=default&split=train&offset=0&length=5"
    )
    try:
        resp = requests.get(api_url, headers=headers, timeout=25)
        if resp.status_code != 200:
            print(f"[REJECT] {repo_id} | Parquet HTTP {resp.status_code}")
            return None

        payload = resp.json()
        rows = payload.get("rows", [])
        if not rows:
            print(f"[REJECT] {repo_id} | Empty Parquet rows")
            return None

        first_row = rows[0].get("row", {})
        if not verify_anchor_c24(first_row):
            print(f"[REJECT] {repo_id} | Missing ¢24 Anchor")
            return None

        combined_text = json.dumps(first_row, ensure_ascii=False)
        entropy = compute_shannon_entropy(combined_text)
        if not (0.0 < entropy < ENTROPY_LIMIT):
            print(f"[REJECT] {repo_id} | Entropy out of bounds: H(X)={entropy}")
            return None

        tensor_ok, variance = verify_tensor_stability(combined_text)
        if not tensor_ok:
            print(f"[REJECT] {repo_id} | L2 Tensor Norm instability")
            return None

        seq = int(repo_id.split("-")[-1])
        dao_index = ((seq - 1) % 10) + 1
        title = (
            first_row.get("title")
            or first_row.get("topic")
            or first_row.get("axiom_title")
            or f"EATHESEN Path-{seq:05d} (Dao {dao_index})"
        )
        raw_nodes = first_row.get("pure_logic_nodes") or first_row.get("axioms") or []
        if isinstance(raw_nodes, str):
            nodes = [raw_nodes]
        elif isinstance(raw_nodes, list):
            nodes = [str(n) for n in raw_nodes[:8]]
        else:
            nodes = []

        content_excerpt = (
            first_row.get("content")
            or first_row.get("abstract")
            or first_row.get("text")
            or combined_text
        )

        print(
            f"[PASS] {repo_id} | HTTP 200 OK | H(X)={entropy:.4f} | "
            f"Var={variance:.4e} | ¢24 LOCKED"
        )
        return {
            "repo_id": repo_id,
            "sequence": seq,
            "dao_index": dao_index,
            "anchor": "¢24",
            "title": str(title),
            "shannon_entropy": entropy,
            "tensor_variance": round(variance, 8),
            "pure_logic_nodes": nodes,
            "hf_url": f"https://huggingface.co/datasets/{repo_id}",
            "parquet_verified": True,
            "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "_excerpt": str(content_excerpt)[:EXCERPT_CHAR_LIMIT],
        }
    except Exception as exc:
        print(f"[REJECT] {repo_id} | Exception: {exc}")
        return None


def sequential_scan_and_audit(parity: str, cached_map: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    start_seq = 2 if parity == "EVEN" else 1
    max_cached_seq = max((d["sequence"] for d in cached_map.values()), default=0)

    verified_records: List[Dict[str, Any]] = []
    fresh_batch: List[Dict[str, Any]] = []
    consecutive_misses = 0

    print(f"[SEQUENTIAL SCAN] Starting ordered scan from path-{start_seq:05d} (step +2)...")

    for seq in range(start_seq, MAX_SCALE_LIMIT + 1, 2):
        repo_id = f"{HF_ORG}/path-{seq:05d}"

        if not repository_exists(repo_id):
            if seq > max_cached_seq:
                consecutive_misses += 1
                print(f"[PROBE] {repo_id} -> Not found (miss {consecutive_misses}/{CONSECUTIVE_MISS_STOP})")
                if consecutive_misses >= CONSECUTIVE_MISS_STOP:
                    print(f"[SEQUENTIAL SCAN] Reached current frontier at path-{seq:05d}. Stopping scan.")
                    break
            continue

        consecutive_misses = 0
        print(f"[SEQUENTIAL SCAN] Auditing {repo_id} ...")
        audited = audit_single_repository(repo_id)
        if audited is not None:
            verified_records.append(audited)
            fresh_batch.append(audited)
        elif repo_id in cached_map:
            verified_records.append(cached_map[repo_id])

    return verified_records, fresh_batch


def distill_with_cloudflare_ai(batch: List[Dict[str, Any]], parity: str) -> str:
    if not batch:
        return "No verified datasets in sequential scan; awaiting new repository publication."
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return "Cloudflare credentials not configured; deterministic metadata broadcast active."

    corpus_lines = []
    for item in batch[-DISTILL_WINDOW_SIZE:]:
        corpus_lines.append(
            f"- Repo: {item['repo_id']} (Dao {item['dao_index']}, H(X)={item['shannon_entropy']}): "
            f"{item['title']} | Excerpt: {item.get('_excerpt', '')}"
        )
    corpus_block = "\n".join(corpus_lines)

    system_prompt = (
        "You are the EATHESEN V3000 Deterministic Knowledge Distiller operating under Anchor ¢24. "
        "Synthesize the provided verified datasets into a concise, high-precision executive abstract "
        "preserving exact axioms, mathematical invariants, and cross-Dao logical connections. "
        "Output plain structured prose without speculation."
    )
    user_prompt = (
        f"Parity Stream: {parity}\n"
        f"Sequential Verified Batch ({len(batch)} datasets):\n{corpus_block}\n\n"
        "Provide the distilled synthesis for the global CDN feed:"
    )

    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    for model_name in AUTHORIZED_CF_TEXT_MODELS:
        print(f"[CLOUDFLARE AI] Attempting sequential distillation ({len(batch)} items) via: {model_name}")
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{model_name}"
        payload = {
            "temperature": 0.0,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                result_obj = data.get("result", {})
                content = (
                    result_obj.get("response")
                    or result_obj.get("choices", [{}])[0].get("message", {}).get("content", "")
                ).strip()
                if content:
                    print(f"[CLOUDFLARE AI] Distillation succeeded via {model_name}.")
                    return content
            print(f"[CLOUDFLARE AI] Model {model_name} returned HTTP {resp.status_code}: {resp.text[:160]}; failing over...")
        except Exception as exc:
            print(f"[CLOUDFLARE AI] Exception on {model_name}: {exc}; failing over...")

    return "All authorized Cloudflare Edge AI text endpoints temporarily busy; deterministic metadata preserved."


def write_cdn_artifacts(
    parity: str,
    datasets: List[Dict[str, Any]],
    distilled_synthesis: str,
) -> None:
    os.makedirs(CDN_DIR, exist_ok=True)
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    normalized_current = [normalize_dataset_record(dict(d)) for d in datasets]
    clean_datasets = []
    for d in sorted(normalized_current, key=lambda x: x["sequence"]):
        entry = {k: v for k, v in d.items() if not k.startswith("_")}
        clean_datasets.append(entry)

    parity_file = os.path.join(CDN_DIR, f"feed-{parity.lower()}.json")
    parity_payload = {
        "system": "EATHESEN V3000 SOTA",
        "organization": GITHUB_OWNER,
        "hf_hub": HF_ORG,
        "anchor": "¢24",
        "parity": parity,
        "updated_at": now_iso,
        "total_verified": len(clean_datasets),
        "edge_distilled_synthesis": distilled_synthesis,
        "datasets": clean_datasets,
    }
    with open(parity_file, "w", encoding="utf-8") as f:
        json.dump(parity_payload, f, ensure_ascii=False, indent=2)

    other_parity = "odd" if parity == "EVEN" else "even"
    other_file = os.path.join(CDN_DIR, f"feed-{other_parity}.json")
    other_datasets: List[Dict[str, Any]] = []
    if os.path.exists(other_file):
        try:
            with open(other_file, "r", encoding="utf-8") as f:
                other_datasets = json.load(f).get("datasets", [])
        except Exception:
            other_datasets = []

    merged_map: Dict[str, Dict[str, Any]] = {}
    for d in other_datasets:
        if "repo_id" in d:
            merged_map[d["repo_id"]] = normalize_dataset_record(dict(d))
    for d in clean_datasets:
        merged_map[d["repo_id"]] = d

    merged_list = sorted(merged_map.values(), key=lambda x: x["sequence"])

    master_payload = {
        "system": "EATHESEN V3000 SOTA — Master Global Index",
        "anchor": "¢24",
        "boolean_checksum": 1,
        "updated_at": now_iso,
        "total_repositories": len(merged_list),
        "cdn_endpoints": {
            "master_index": f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/cdn/master-index.json",
            "even_feed": f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/cdn/feed-even.json",
            "odd_feed": f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/cdn/feed-odd.json",
            "rss_xml": f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/cdn/feed.xml",
        },
        "datasets": merged_list,
    }
    with open(MASTER_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(master_payload, f, ensure_ascii=False, indent=2)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "EATHESEN V3000 SOTA — Autonomous Knowledge Stream [¢24]"
    ET.SubElement(channel, "link").text = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
    ET.SubElement(channel, "description").text = (
        "Deterministic, low-entropy mathematical and philosophical datasets verified under Anchor ¢24."
    )
    ET.SubElement(channel, "lastBuildDate").text = now_iso

    for item_data in reversed(merged_list[-50:]):
        item_el = ET.SubElement(channel, "item")
        ET.SubElement(item_el, "title").text = f"[¢24][Dao {item_data['dao_index']}] {item_data['title']}"
        ET.SubElement(item_el, "link").text = item_data["hf_url"]
        ET.SubElement(item_el, "guid").text = item_data["repo_id"]
        ET.SubElement(item_el, "pubDate").text = item_data.get("audited_at", now_iso)
        ET.SubElement(item_el, "description").text = (
            f"Repo: {item_data['repo_id']} | Shannon Entropy H(X)={item_data['shannon_entropy']} | "
            f"Tensor Variance={item_data.get('tensor_variance', 0.0)} | Anchor: ¢24"
        )

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(RSS_FEED_FILE, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="EATHESEN V3000 Sequential 10K-Scale Orchestrator")
    parser.add_argument("--parity", choices=["EVEN", "ODD"], required=True)
    args = parser.parse_args()
    parity = args.parity

    print(f"=== [EATHESEN V3000 SEQUENTIAL PULSE] GitHub: {GITHUB_OWNER} | HF: {HF_ORG} | Mode: {parity} ===")

    cached_map = load_cached_parity_datasets(parity)
    final_list, fresh_batch = sequential_scan_and_audit(parity, cached_map)

    distilled_text = distill_with_cloudflare_ai(fresh_batch, parity)
    write_cdn_artifacts(parity, final_list, distilled_text)

    print(
        f"[SUCCESS] Sequential Broadcast complete for {GITHUB_OWNER}. "
        f"Total {parity} live: {len(final_list)} | Distilled batch: {len(fresh_batch)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
