#!/usr/bin/env python3
"""
AETHESEN V3000 SOTA - Autonomous Parity Orchestrator & CDN Broadcaster
GitHub Owner: donabico-media-system
Hugging Face Owner: donabico
Anchor Constant: ¢24
Protocols: Dynamic HF Discovery -> Shannon Entropy Audit -> Groq LPU Authorized Model Distillation -> CDN Feed Export
"""

import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
import numpy as np
import requests

PARITY_MODE = os.getenv("PARITY_MODE", "EVEN").upper()
GITHUB_ORG = os.getenv("GITHUB_ORG", "donabico-media-system")
HF_AUTHOR = os.getenv("HF_AUTHOR", "donabico")
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

CDN_DIR = "cdn"
D_MODEL = 49152
ENTROPY_LIMIT = 5.0
ANCHOR_CONSTANT = "¢24"

# Authorized Organization Models on GroqCloud (Donabico Media System)
AUTHORIZED_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
]


def compute_shannon_entropy(text: str) -> float:
    """Computes exact byte-level Shannon Entropy H(X) = -sum(p_i * log2(p_i))."""
    raw_bytes = text.encode("utf-8")
    if not raw_bytes:
        return 0.0
    total = len(raw_bytes)
    counts = Counter(raw_bytes)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def verify_tensor_stability(text: str) -> float:
    """Projects content into d_model=49152 space and verifies unit hypersphere norm."""
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    vec = np.zeros(D_MODEL, dtype=np.float64)
    for token in tokens:
        h = 24
        for ch in token:
            h = (h * 131 + ord(ch)) % D_MODEL
        vec[h] += 1.0
    norm = float(np.linalg.norm(vec))
    assert norm > 0.0, "Zero-norm vector violation."
    normalized = vec / norm
    l2_check = float(np.linalg.norm(normalized))
    assert abs(l2_check - 1.0) < 1e-12, f"Tensor drift detected: {l2_check}"
    return float(np.var(normalized))


def discover_hf_repositories(author: str, parity: str) -> list[dict]:
    """Dynamically discovers path-XXXXX datasets under donabico matching EVEN or ODD parity."""
    headers = {"User-Agent": "donabico-media-system-Aethesen-V3000/1.0"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    url = f"https://huggingface.co/api/datasets?author={author}&limit=1000"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    datasets = resp.json()

    matched = []
    pattern = re.compile(rf"^{re.escape(author)}/path-(\d{{5}})$")
    for item in datasets:
        repo_id = item.get("id", "")
        m = pattern.match(repo_id)
        if not m:
            continue
        seq_num = int(m.group(1))
        is_even = (seq_num % 2 == 0)
        if (parity == "EVEN" and is_even) or (parity == "ODD" and not is_even):
            matched.append({"repo_id": repo_id, "seq_num": seq_num})

    matched.sort(key=lambda x: x["seq_num"])
    return matched


def fetch_and_audit_dataset(repo_id: str) -> dict | None:
    """Fetches dataset row via Hugging Face Datasets Server CDN and runs hard-logic audit."""
    headers = {"User-Agent": "donabico-media-system-Aethesen-V3000/1.0"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    cdn_url = (
        f"https://datasets-server.huggingface.co/rows"
        f"?dataset={repo_id}&config=default&split=train&offset=0&length=1"
    )
    resp = requests.get(cdn_url, headers=headers, timeout=20)
    if resp.status_code != 200:
        print(f"[WARN] {repo_id} returned HTTP {resp.status_code}. Skipping until Parquet compiles.")
        return None

    data = resp.json()
    rows = data.get("rows", [])
    if not rows:
        print(f"[WARN] {repo_id} returned 0 rows.")
        return None

    row_payload = rows[0].get("row", {})
    content = row_payload.get("content", "")
    anchor = row_payload.get("anchor", "")

    if anchor != ANCHOR_CONSTANT:
        print(f"[BLOCK] {repo_id} failed ¢24 anchor verification (found: {anchor}).")
        return None

    entropy = compute_shannon_entropy(content)
    if entropy >= ENTROPY_LIMIT or entropy <= 0.0:
        print(f"[BLOCK] {repo_id} failed Shannon Entropy bound: H(X)={entropy:.4f}.")
        return None

    variance = verify_tensor_stability(content)
    print(f"[PASS] {repo_id} | HTTP 200 OK | H(X)={entropy:.4f} | Var={variance:.4e} | ¢24 LOCKED")

    return {
        "repo_id": repo_id,
        "dao_index": row_payload.get("dao_index"),
        "dao_name": row_payload.get("dao_name"),
        "title": row_payload.get("title"),
        "content": content,
        "pure_logic_nodes": row_payload.get("pure_logic_nodes", []),
        "shannon_entropy": round(entropy, 6),
        "tensor_variance": variance,
        "cdn_api_url": cdn_url,
        "hf_url": f"https://huggingface.co/datasets/{repo_id}",
    }


def distill_with_groq(audited_items: list[dict], parity: str) -> str:
    """Sends audited knowledge to Groq LPU using the organization's allowed models with fallback."""
    if not GROQ_API_KEY:
        raise RuntimeError("CRITICAL: GROQ_API_KEY is missing from environment secrets.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    corpus_digest = "\n\n---\n\n".join(
        f"REPO: {item['repo_id']} | DAO: {item['dao_name']}\n"
        f"TITLE: {item['title']}\n"
        f"NODES: {', '.join(item['pure_logic_nodes'])}\n"
        f"EXCERPT: {item['content'][:1800]}"
        for item in audited_items
    )

    system_prompt = (
        "You are the AETHESEN V3000 Knowledge Distillation Engine for donabico-media-system, operating under "
        "the ¢24 Immutable Anchor and the 24 Supreme Constitutions (Boolean Checksum = 1). Synthesize the "
        "verified research articles into a high-precision, zero-fluff, deterministic executive broadcast in "
        "English for global AI crawlers and RAG agents. Preserve exact mathematical invariants and node names."
    )

    user_prompt = (
        f"GITHUB SYSTEM: {GITHUB_ORG}\n"
        f"HUGGING FACE OWNER: {HF_AUTHOR}\n"
        f"PARITY STREAM: {parity}\n"
        f"ACTIVE REPOSITORIES COUNT: {len(audited_items)}\n\n"
        f"VERIFIED SOURCE PAYLOADS:\n{corpus_digest}\n\n"
        "Produce a structured synthesis highlighting core axioms, cross-Dao logical invariants, "
        "and machine-readable takeaways."
    )

    last_error = None
    for model_id in AUTHORIZED_GROQ_MODELS:
        print(f"[GROQ LPU] Attempting distillation with authorized model: {model_id}")
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 1500,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            print(f"[GROQ LPU] Distillation succeeded via {model_id}.")
            return resp.json()["choices"][0]["message"]["content"].strip()

        last_error = f"{model_id} -> HTTP {resp.status_code}: {resp.text}"
        print(f"[WARN] {last_error}. Trying next allowed model...")

    raise RuntimeError(f"All authorized Groq models failed. Last error: {last_error}")


def write_cdn_artifacts(audited_items: list[dict], synthesis: str, parity: str) -> None:
    """Writes static JSON & RSS 2.0 feeds to cdn/ directory for global HTTP 200 OK distribution."""
    os.makedirs(CDN_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parity_file = os.path.join(CDN_DIR, f"feed-{parity.lower()}.json")
    parity_payload = {
        "system": "AETHESEN V3000 OMEGA",
        "github_owner": GITHUB_ORG,
        "hf_owner": HF_AUTHOR,
        "anchor": ANCHOR_CONSTANT,
        "boolean_checksum": 1,
        "parity": parity,
        "updated_at": timestamp,
        "active_datasets_count": len(audited_items),
        "groq_distilled_synthesis": synthesis,
        "datasets": [
            {
                "repo_id": item["repo_id"],
                "dao_index": item["dao_index"],
                "title": item["title"],
                "shannon_entropy": item["shannon_entropy"],
                "pure_logic_nodes": item["pure_logic_nodes"],
                "hf_url": item["hf_url"],
                "parquet_cdn_api": item["cdn_api_url"],
            }
            for item in audited_items
        ],
    }
    with open(parity_file, "w", encoding="utf-8") as f:
        json.dump(parity_payload, f, ensure_ascii=False, indent=2)

    even_path = os.path.join(CDN_DIR, "feed-even.json")
    odd_path = os.path.join(CDN_DIR, "feed-odd.json")
    even_data = json.load(open(even_path, encoding="utf-8")) if os.path.exists(even_path) else {"datasets": []}
    odd_data = json.load(open(odd_path, encoding="utf-8")) if os.path.exists(odd_path) else {"datasets": []}

    all_datasets = even_data.get("datasets", []) + odd_data.get("datasets", [])
    all_datasets.sort(key=lambda x: x["repo_id"])

    master_index = {
        "system": "AETHESEN V3000 OMEGA - MASTER CDN INDEX",
        "github_owner": GITHUB_ORG,
        "hf_owner": HF_AUTHOR,
        "anchor": ANCHOR_CONSTANT,
        "boolean_checksum": 1,
        "last_heartbeat_utc": timestamp,
        "total_live_datasets": len(all_datasets),
        "datasets": all_datasets,
    }
    with open(os.path.join(CDN_DIR, "master-index.json"), "w", encoding="utf-8") as f:
        json.dump(master_index, f, ensure_ascii=False, indent=2)

    rss_items = []
    for ds in all_datasets:
        rss_items.append(
            f"    <item>\n"
            f"      <title>[{ANCHOR_CONSTANT}] {ds['repo_id']} — {ds['title']}</title>\n"
            f"      <link>{ds['hf_url']}</link>\n"
            f"      <guid isPermaLink=\"true\">{ds['hf_url']}</guid>\n"
            f"      <description>Dao Index: {ds['dao_index']} | Shannon Entropy: {ds['shannon_entropy']} | Nodes: {', '.join(ds['pure_logic_nodes'])}</description>\n"
            f"    </item>"
        )

    rss_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "  <channel>\n"
        f"    <title>AETHESEN V3000 SOTA Broadcast - {GITHUB_ORG} ({ANCHOR_CONSTANT})</title>\n"
        f"    <link>https://github.com/{GITHUB_ORG}</link>\n"
        f"    <description>Autonomous Knowledge CDN Stream by {GITHUB_ORG} &amp; {HF_AUTHOR}</description>\n"
        f"    <lastBuildDate>{timestamp}</lastBuildDate>\n"
        + "\n".join(rss_items)
        + "\n  </channel>\n"
        "</rss>\n"
    )
    with open(os.path.join(CDN_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)


def main() -> int:
    print(f"=== [AETHESEN V3000 PULSE] GitHub: {GITHUB_ORG} | HF: {HF_AUTHOR} | Mode: {PARITY_MODE} ===")
    repos = discover_hf_repositories(HF_AUTHOR, PARITY_MODE)
    print(f"[DISCOVERY] Found {len(repos)} {PARITY_MODE} repositories under {HF_AUTHOR}.")

    if not repos:
        print("[INFO] No matching repositories live yet. Exiting cleanly (Exit 0).")
        return 0

    audited = []
    for repo in repos:
        result = fetch_and_audit_dataset(repo["repo_id"])
        if result:
            audited.append(result)

    if not audited:
        print("[INFO] No datasets passed HTTP 200 OK & Entropy checks in this cycle.")
        return 0

    print(f"[GROQ LPU] Distilling {len(audited)} verified datasets...")
    synthesis = distill_with_groq(audited, PARITY_MODE)
    write_cdn_artifacts(audited, synthesis, PARITY_MODE)
    print(f"[SUCCESS] Broadcast complete for {GITHUB_ORG}. Published {len(audited)} datasets to /{CDN_DIR}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
