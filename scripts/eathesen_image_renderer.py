#!/usr/bin/env python3
"""
EATHESEN V3000 SOTA — Autonomous Visual Asset Renderer (0-Cost Edge Pipeline)
Primary Engine: Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell)
Fallback Engine: Pollinations.ai (FLUX zero-auth backup)
Target Storage: Hugging Face Dataset Repositories (donabico/path-XXXXX/cover-XXXXX.jpg)
"""

import base64
import json
import os
import re
import sys
import urllib.parse
import requests

CF_ACCOUNT_ID = re.sub(r"[^a-fA-F0-9]", "", os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip().lstrip("\\")
HF_TOKEN = os.getenv("HF_TOKEN", "").strip().lstrip("\\")
MASTER_INDEX_PATH = "cdn/master-index.json"

MAX_IMAGES_PER_PULSE = 12


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
    return (
        f"Ultra-detailed sacred geometric architecture representing Dao {dao_idx}: {title}. "
        f"Luminous golden light rays, ruby core crystal matrix, mathematical tensor lattice ({nodes}), "
        f"ethereal cosmic harmony, minimalist SOTA scientific illustration, 8k resolution, sharp focus, no text."
    )


def render_via_cloudflare(prompt: str) -> bytes | None:
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        print("[WARN] Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN. Skipping Cloudflare tier.")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
    }

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
        print(f"[WARN] Cloudflare Workers AI returned HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[WARN] Cloudflare Workers AI connection error: {exc}")
    return None


def render_via_pollinations_fallback(prompt: str) -> bytes | None:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true"
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
        raise RuntimeError("CRITICAL: Missing HF_TOKEN for Hugging Face upload.")

    api_url = f"https://huggingface.co/api/datasets/{repo_id}/commit/main"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/x-ndjson",
    }

    b64_content = base64.b64encode(image_bytes).decode("ascii")
    ndjson_lines = [
        json.dumps({
            "key": "header",
            "value": {
                "summary": f"feat(visual): [¢24] Add deterministic cover artwork {filename}",
                "description": "Rendered autonomously via EATHESEN Visual Engine (Cloudflare Workers AI).",
            },
        }),
        json.dumps({
            "key": "file",
            "value": {
                "content": b64_content,
                "path": filename,
                "encoding": "base64",
            },
        }),
    ]
    payload = "\n".join(ndjson_lines) + "\n"

    resp = requests.post(api_url, headers=headers, data=payload.encode("utf-8"), timeout=45)
    if resp.status_code in (200, 201):
        print(f"[HF UPLOAD] Successfully published {repo_id}/{filename}")
        return True
    print(f"[ERROR] Failed uploading cover to {repo_id}: HTTP {resp.status_code} - {resp.text[:200]}")
    return False


def main() -> int:
    if not os.path.exists(MASTER_INDEX_PATH):
        print("[INFO] cdn/master-index.json not found. Skipping visual cycle.")
        return 0

    with open(MASTER_INDEX_PATH, "r", encoding="utf-8") as f:
        master = json.load(f)

    datasets = master.get("datasets", [])
    print(f"=== [EATHESEN VISUAL RENDERER] Checking {len(datasets)} repositories in master-index.json ===")

    rendered_count = 0
    for item in datasets:
        if rendered_count >= MAX_IMAGES_PER_PULSE:
            print(f"[LIMIT] Reached cap of {MAX_IMAGES_PER_PULSE} images/pulse to preserve daily Neurons.")
            break

        repo_id = item["repo_id"]
        seq_str = repo_id.split("-")[-1]
        filename = f"cover-{seq_str}.jpg"

        if check_cover_exists_on_hf(repo_id, filename):
            print(f"[SKIP] {repo_id}/{filename} already exists.")
            continue

        print(f"[RENDERING] Generating artwork for {repo_id} -> {filename}...")
        prompt = build_sacred_geometry_prompt(item)
        img_bytes = render_via_cloudflare(prompt) or render_via_pollinations_fallback(prompt)

        if img_bytes and upload_image_to_hf(repo_id, filename, img_bytes):
            rendered_count += 1

    print(f"[COMPLETE] Visual render cycle finished. New covers published: {rendered_count}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
