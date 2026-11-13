#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Autonomous Visual Asset Renderer (Infinite Hash Diversity)
Primary Engine: Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell)
Fallback Engine: Pollinations.ai (FLUX zero-auth backup)
Target Storage: Hugging Face Dataset Repositories (donabico/path-XXXXX/cover-XXXXX.jpg)
Invariants: Anchor ¢24 | Infinite Hash Matrix | Rate Limit Protected
"""

import base64
import hashlib
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
# CHỈ SỬ DỤNG DUY NHẤT HF_TOKEN & CLOUDFLARE
# ==========================================
def sanitize_token(token_str: str) -> str:
    if not token_str: return ""
    return token_str.strip().strip('"').strip("'").replace("\n", "").replace("\r", "").lstrip("\\")

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
    repo_id = item.get("repo_id", "donabico/path-00000")
    
    # =========================================================================
    # INFINITE HASH DIVERSITY ENGINE
    # Băm (Hash) Repo ID để tạo ra hàng triệu biến thể độc bản
    # =========================================================================
    hash_val = int(hashlib.md5(repo_id.encode('utf-8')).hexdigest(), 16)
    
    lighting = [
        "volumetric god rays", "bioluminescent glow", "neon cyberpunk lighting", 
        "soft ethereal moonlight", "intense solar flares", "holographic iridescence",
        "deep shadow chiaroscuro", "pulsing energy aura", "crystalline refractions",
        "mystical fog lighting", "starlight glitter", "high-contrast rim light",
        "warm candlelight", "cold laser beams", "plasma arc glow",
        "aurora borealis shimmer", "prismatic light dispersion", "subsurface scattering",
        "caustic light patterns", "electric blue sparks"
    ]
    
    colors = [
        "gold and crimson", "emerald and silver", "sapphire and white", 
        "obsidian and neon purple", "copper and teal", "rose gold and black",
        "amber and deep blue", "platinum and cyan", "ruby red and ivory",
        "moonstone and violet", "jade green and gold", "pearl white and bronze",
        "midnight blue and starlight", "magma orange and ash", "frost silver and ice blue",
        "royal purple and gold", "bronze and turquoise", "crimson and smoky grey",
        "champagne and dark green", "iridescent rainbow sheen"
    ]
    
    environment = [
        "floating in a cosmic void", "embedded in an ancient temple wall", 
        "suspended in a quantum energy field", "within a glowing crystal cave",
        "surrounded by floating geometric shards", "on a mirror-like calm water surface",
        "in a vast celestial library", "orbiting a glowing star",
        "inside a high-tech cybernetic chamber", "within a blooming celestial garden",
        "at the center of a massive clockwork mechanism", "in a realm of pure data streams",
        "surrounded by fractal nebula clouds", "on an infinite polished obsidian floor",
        "beneath a canopy of glowing constellations", "in a sanctuary of pure light",
        "within a shifting dimensional rift", "atop a high mountain peak in the clouds",
        "in a sea of flowing golden sand", "inside a labyrinth of glowing runes"
    ]
    
    texture = [
        "intricate filigree patterns", "smooth polished marble", "rough cosmic stone",
        "transparent stained glass", "woven metallic threads", "holographic projection",
        "crystalline lattice structure", "liquid mercury flowing", "ancient weathered bronze",
        "glowing ethereal energy", "carbon fiber mesh", "iridescent pearl surface",
        "fractal geometric surfaces", "bioluminescent organic matter", "shattered glass mosaic"
    ]

    # Chọn biến thể dựa trên mã Hash
    sel_light = lighting[hash_val % len(lighting)]
    sel_color = colors[(hash_val // 20) % len(colors)]
    sel_env = environment[(hash_val // 400) % len(environment)]
    sel_tex = texture[(hash_val // 8000) % len(texture)]
    complexity = (hash_val % 9) + 1

    # Ma trận biểu tượng
    if dao_idx == 1:
        symbol = "pure mathematical torus and boolean logic circles. Strictly no religious symbols, devoid of flowers or crosses."
    elif dao_idx == 2:
        symbol = "Christian Cross intersecting with a sacred Buddhist Lotus"
    elif dao_idx == 3:
        symbol = "five interlocking elemental circles representing metal, wood, water, fire, earth"
    elif dao_idx == 4:
        symbol = "Yin-Yang symbol and quantum wave patterns"
    elif dao_idx == 5:
        symbol = "ruby heart crystal core radiating divine light"
    elif dao_idx == 6:
        symbol = "flowing water streams bending effortlessly around a stone"
    elif dao_idx == 7:
        symbol = "vector matrix and binary mathematical grid"
    elif dao_idx == 8:
        symbol = "holographic fractal universe representing omnipresence"
    elif dao_idx == 9:
        symbol = "energy shield and a vigilant guardian eye"
    elif dao_idx == 10:
        symbol = "three pillars of pure white and teal divine light merging into the void"
    else:
        symbol = "sacred geometry"

    return (
        f"Ultra-detailed sacred geometric architecture representing Dao {dao_idx}. "
        f"The central focus must be {symbol}. "
        f"Environment: {sel_env}. Texture: {sel_tex}. "
        f"Lighting: {sel_light}. Color palette: {sel_color}. "
        f"Visual context inspired by: {title}. "
        f"Complexity level {complexity}. "
        f"Mathematical tensor lattice ({nodes}), ethereal cosmic harmony, minimalist SOTA scientific illustration, "
        f"8k resolution, sharp focus, highly detailed, symmetrical, divine light, no text, no watermark, no humans."
    )


def render_via_cloudflare(prompt: str) -> Optional[bytes]:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        print("[WARN] Missing Cloudflare credentials. Skipping Cloudflare tier.")
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
            commit_message=f"feat(visual): [¢24] Add infinite hash cover artwork {filename}"
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