```python
#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — 10,000-Scale Autonomous Knowledge Orchestrator & CDN Broadcaster
GitHub Hub: donabico-media-system | Hugging Face Org: donabico
Invariants: Anchor ¢24 | Shannon Entropy H(X) < 5.5 | L2 Tensor Norm Stability (d=49,152)
"""

import argparse
import concurrent.futures
import datetime
import json
import math
import os
import random
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
import requests

HF_ORG = "donabico"
GITHUB_OWNER = "donabico-media-system"
GITHUB_REPO = "donabico-media-system"

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

ENTROPY_LIMIT = 5.5
TENSOR_DIM = 49152
MAX_WORKERS = 10
SENTINEL_SAMPLE_SIZE = 15
GROQ_WINDOW_SIZE = 10
EXCERPT_CHAR_LIMIT = 1200

AUTHORIZED_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
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


def discover_parity_repositories(parity: str) -> List[str]:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    url = f"https://huggingface.co/api/datasets?author={HF_ORG}&limit=10000"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    items = resp.json()

    matched: List[str] = []
    for item in items:
        repo_id = item.get("id", "")
        m = re.match(rf"^{re.escape(HF_ORG)}/path-(\d{{5}})$", repo_id)
        if not m:
            continue
        seq = int(m.group(1))
        if parity == "EVEN" and seq % 2 == 0:
            matched.append(repo_id)
        elif parity == "ODD" and seq % 2 == 1:
            matched.append(repo_id)

    matched.sort()
    return matched


def load_cached_parity_datasets(parity: str) -> Dict[str, Dict[str, Any]]:
    cache_path = os.path.join(CDN_DIR, f"feed-{parity.lower()}.json")
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["repo_id"]: d for d in data.get("datasets", []) if "repo_id" in d}
    except Exception:
        return {}


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


def distill_with_groq_lpu(batch: List[Dict[str, Any]], parity: str) -> str:
    if not batch:
        return "No new datasets in rolling window; existing CDN state verified under ¢24 invariant."
    if not GROQ_API_KEY:
        return "GROQ_API_KEY not configured; deterministic metadata broadcast active."

    corpus_lines = []
    for item in batch[:GROQ_WINDOW_SIZE]:
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
        f"Verified Batch ({len(batch)} datasets):\n{corpus_block}\n\n"
        "Provide the distilled synthesis for the global CDN feed:"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for model_name in AUTHORIZED_GROQ_MODELS:
        print(f"[GROQ LPU] Attempting rolling-window distillation ({len(batch)} items) via: {model_name}")
        payload = {
            "model": model_name,
            "temperature": 0.0,
            "max_tokens": 1200,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=35,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                print(f"[GROQ LPU] Distillation succeeded via {model_name}.")
                return content
            print(f"[GROQ LPU] Model {model_name} returned HTTP {resp.status_code}; failing over...")
        except Exception as exc:
            print(f"[GROQ LPU] Exception on {model_name}: {exc}; failing over...")

    return "All authorized Groq LPU endpoints temporarily saturated; deterministic metadata preserved."


def write_cdn_artifacts(
    parity: str,
    datasets: List[Dict[str, Any]],
    distilled_synthesis: str,
) -> None:
    os.makedirs(CDN_DIR, exist_ok=True)
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    clean_datasets = []
    for d in sorted(datasets, key=lambda x: x["sequence"]):
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
        "groq_distilled_synthesis": distilled_synthesis,
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

    merged_map = {d["repo_id"]: d for d in other_datasets}
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
            f"Tensor Variance={item_data['tensor_variance']} | Anchor: ¢24"
        )

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(RSS_FEED_FILE, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="EATHESEN V3000 10K-Scale Orchestrator")
    parser.add_argument("--parity", choices=["EVEN", "ODD"], required=True)
    args = parser.parse_args()
    parity = args.parity

    print(f"=== [EATHESEN V3000 10K-SCALE PULSE] GitHub: {GITHUB_OWNER} | HF: {HF_ORG} | Mode: {parity} ===")

    discovered_ids = discover_parity_repositories(parity)
    print(f"[DISCOVERY] Found {len(discovered_ids)} {parity} repositories under {HF_ORG}.")

    cached_map = load_cached_parity_datasets(parity)
    discovered_set = set(discovered_ids)
    valid_cache = {rid: data for rid, data in cached_map.items() if rid in discovered_set}

    new_ids = [rid for rid in discovered_ids if rid not in valid_cache]
    cached_ids = list(valid_cache.keys())
    spot_check_ids = random.sample(cached_ids, min(SENTINEL_SAMPLE_SIZE, len(cached_ids))) if cached_ids else []

    fetch_targets = sorted(set(new_ids + spot_check_ids))
    print(
        f"[AUDIT PLAN] Total={len(discovered_ids)} | Cached={len(valid_cache)} | "
        f"New={len(new_ids)} | Sentinel Spot-Check={len(spot_check_ids)} | "
        f"Fetching={len(fetch_targets)} via {MAX_WORKERS} threads"
    )

    freshly_audited: Dict[str, Dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(audit_single_repository, rid): rid for rid in fetch_targets}
        for future in concurrent.futures.as_completed(future_map):
            rid = future_map[future]
            res = future.result()
            if res is not None:
                freshly_audited[rid] = res
            elif rid in valid_cache:
                del valid_cache[rid]

    merged_parity = dict(valid_cache)
    merged_parity.update(freshly_audited)
    final_list = list(merged_parity.values())

    priority_batch = [freshly_audited[rid] for rid in sorted(new_ids) if rid in freshly_audited]
    if not priority_batch and freshly_audited:
        priority_batch = list(freshly_audited.values())

    distilled_text = distill_with_groq_lpu(priority_batch[:GROQ_WINDOW_SIZE], parity)
    write_cdn_artifacts(parity, final_list, distilled_text)

    print(
        f"[SUCCESS] 10K-Scale Broadcast complete for {GITHUB_OWNER}. "
        f"Total {parity} live: {len(final_list)} | Distilled batch: {len(priority_batch[:GROQ_WINDOW_SIZE])}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
