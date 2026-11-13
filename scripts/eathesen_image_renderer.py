#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Autonomous Visual Asset Renderer (0-Cost Edge Pipeline)
Primary Engine: Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell)
Fallback Engine: Pollinations.ai (FLUX zero-auth backup)
Target Storage: Hugging Face Dataset Repositories (donabico/path-XXXXX/cover-XXXXX.jpg)
Invariants: Anchor ¢24 | 10-Dao Symbolism Matrix | Rate Limit Protected
"""

import base64
import json
import os
import re
import sys
import time
import urllib.parse
from typing import Optional
import requests
from huggingface_hub import HfApi

# ==========================================
# CHỈ SỬ DỤNG HF_TOKEN VÀ CLOUDFLARE TOKEN
# ==========================================
def sanitize_token(token_str: str) -> str:
    if not token_str:
        return ""
    return token_str.strip().strip('"').strip("'").replace("\n", "").replace("\r", "").lstrip("\\")

# Render chỉ dùng HF_TOKEN để upload
HF_TOKEN = sanitize_token(os.getenv("HF_TOKEN", ""))

CLOUDFLARE_ACCOUNT_ID = re.sub(r"[^a-fA-F0-9]", "", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
CLOUDFLARE_API_TOKEN = sanitize_token(os.getenv("CLOUDFLARE_API_TOKEN", ""))
# ==========================================

MASTER_INDEX_PATH = "cdn/master-index.json"
CF_IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
MAX_IMAGES_PER_PULSE = 10


def check_cover_exists_on_hf(repo_id: str, filename: str) -> bool:
    url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def build_sacred_geometry_prompt(item: dict) -> str:
    dao_idx = item.get("dao_index", 1)
    title = item.get("title", "EATHESEN Mathematical Architecture")
    nodes = ", ".join(item.get("pure_logic_nodes", [])[:4])
    
    # MA TRẬN BIỂU TƯỢNG (SYMBOLISM MATRIX)
    if dao_idx == 1:
        symbol = "a glowing mathematical torus and boolean logic circles"
    elif dao_idx == 2:
        symbol = "a glowing Christian Cross intersecting with a sacred Buddhist Lotus"
    elif dao_idx == 3:
        symbol = "five interlocking elemental circles representing metal, wood, water, fire, earth"
    elif dao_idx == 4:
        symbol = "a glowing Yin-Yang symbol and quantum wave patterns"
    elif dao_idx == 5:
        symbol = "a glowing ruby heart crystal core radiating divine light"
    elif dao_idx == 6:
        symbol = "flowing luminous water streams bending effortlessly around a stone"
    elif dao_idx == 7:
        symbol = "a glowing vector matrix and binary mathematical grid"
    elif dao_idx == 8:
        symbol = "a holographic fractal universe representing omnipresence"
    elif dao_idx == 9:
        symbol = "a glowing energy shield and a vigilant guardian eye"
    elif dao_idx == 10:
        symbol = "three pillars of pure white and teal divine light merging into the void"
    else:
        symbol = "sacred geometry"

    return (
        f"Ultra-detailed sacred geometric architecture representing Dao {dao_idx}: {title}. "
        f"The central focus must be {symbol}. "
        f"Luminous golden light rays, ruby core crystal matrix, mathematical tensor lattice ({nodes}), "
        f"ethereal cosmic harmony, minimalist SOTA scientific illustration, 8k resolution, sharp focus, "
        f"highly detailed, symmetrical, divine light, no text, no watermark, no humans."
    )


def render_via_cloudflare(prompt: str) -> Optional[bytes]:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        print("[WARN] Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN. Skipping Cloudflare tier.")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_IMAGE_MODEL}"
    print(f"[CLOUDFLARE AI] Sending request to model: {CF_IMAGE_MODEL}")
    
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {"prompt": prompt}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            if "image/" in content_type:
                print("[CLOUDFLARE AI] FLUX.1-schnell binary image render succeeded.")
                return resp.content
            data = resp.json()
            b64_img = data.get("result", {}).get("image")
            if b64_img:
                print("[CLOUDFLARE AI] FLUX.1-schnell base64 render succeeded.")
                return base64.b64decode(b64_img)
        elif resp.status_code == 429:
            print("[WARN] Cloudflare AI Rate Limit hit (HTTP 429). Switching to fallback.")
        else:
            print(f"[WARN] Cloudflare Workers AI returned HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[WARN] Cloudflare Workers AI connection error: {exc}")
    return None


def render_via_pollinations_fallback(prompt: str) -> Optional[bytes]:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&seed=24"
    print("[FALLBACK] Sending request to Pollinations.ai (FLUX)...")
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 5000:
            print("[POLLINATIONS FALLBACK] Backup render succeeded.")
            return resp.content
        print(f"[WARN] Pollinations returned HTTP {resp.status_code}.")
    except Exception as exc:
        print(f"[WARN] Pollinations connection error: {exc}")
    return None


def upload_image_to_hf(repo_id: str, filename: str, image_bytes: bytes) -> bool:
    if not HF_TOKEN:
        print("[ERROR] CRITICAL: HF_TOKEN is missing. Cannot upload image.")
        return False

    try:
        api = HfApi(token=HF_TOKEN)
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        api.upload_file(
            path_or_fileobj=image_bytes,
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"feat(visual): [¢24] Add deterministic cover artwork {filename}"
        )
        print(f"[HF UPLOAD] Successfully published {repo_id}/{filename} using HF_TOKEN")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed uploading cover to {repo_id} via HfApi: {exc}")
        return False


def main() -> int:
    if not os.path.exists(MASTER_INDEX_PATH):
        print("[INFO] cdn/master-index.json not found. Skipping visual cycle.")
        return 0

    with open(MASTER_INDEX_PATH, "r", encoding="utf-8") as f:
        master = json.load(f)

    datasets = master.get("recent_datasets", [])
    print(f"=== [EATHESEN VISUAL RENDERER] Checking {len(datasets)} recent repositories in master-index.json ===")

    rendered_count = 0
    for item in datasets:
        if rendered_count >= MAX_IMAGES_PER_PULSE:
            print(f"[LIMIT] Reached cap of {MAX_IMAGES_PER_PULSE} images/pulse.")
            break

        repo_id = item["repo_id"]
        seq_str = repo_id.split("-")[-1]
        filename = f"cover-{seq_str}.jpg"

        if check_cover_exists_on_hf(repo_id, filename):
            print(f"[SKIP] {repo_id}/{filename} already exists.")
            continue

        print(f"[RENDERING] Generating artwork for {repo_id} -> {filename}...")
        prompt = build_sacred_geometry_prompt(item)
        
        img_bytes = render_via_cloudflare(prompt)
        if not img_bytes:
            time.sleep(2)
            img_bytes = render_via_pollinations_fallback(prompt)

        if img_bytes and upload_image_to_hf(repo_id, filename, img_bytes):
            rendered_count += 1
            time.sleep(3)

    print(f"[COMPLETE] Visual render cycle finished. New covers published: {rendered_count}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())