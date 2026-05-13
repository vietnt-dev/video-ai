"""
Google Gemini Service — MIỄN PHÍ.

Free tier (tháng 5/2026):
- Gemini 2.0 Flash : 15 RPM, 1500 RPD — dùng cho script + SEO
- Imagen 3         : 15 RPM            — dùng để tạo ảnh AI

Lấy API key miễn phí tại: https://aistudio.google.com/apikey
"""
import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Optional

import httpx
from app.config import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
IMAGEN_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


# ─── Text Generation (Script + SEO) ──────────────────────────────────────────

async def gemini_generate(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.8,
    json_mode: bool = True,
) -> str:
    """
    Gọi Gemini API để generate text.
    Returns: raw text response
    """
    model = settings.gemini_model
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={settings.gemini_api_key}"

    payload: dict = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 4096,
        },
    }

    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)

        if resp.status_code == 429:
            # Rate limit — chờ và retry
            print("⚠️  Gemini rate limit, chờ 5 giây...")
            await asyncio.sleep(5)
            resp = await client.post(url, json=payload)

        if resp.status_code == 400:
            err = resp.json()
            raise ValueError(f"Gemini API error: {err.get('error', {}).get('message', resp.text)}")

        resp.raise_for_status()
        data = resp.json()

    # Extract text từ response
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Gemini response parse error: {data}") from e


# ─── Imagen 3 — Tạo ảnh AI miễn phí ─────────────────────────────────────────

async def imagen_generate(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "9:16",
) -> Optional[str]:
    """
    Tạo ảnh bằng Imagen 3 (Google, MIỄN PHÍ).

    Args:
        prompt      : mô tả ảnh tiếng Anh
        output_path : đường dẫn lưu file PNG
        aspect_ratio: "9:16" cho Shorts portrait

    Returns: đường dẫn file ảnh hoặc None nếu lỗi
    """
    if not settings.gemini_api_key:
        print("⚠️  GEMINI_API_KEY chưa set")
        return None

    model = settings.gemini_image_model
    url = f"{IMAGEN_BASE}/{model}:predict?key={settings.gemini_api_key}"

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "safetyFilterLevel": "block_few",
            "personGeneration": "allow_adult",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                print("⚠️  Imagen rate limit, chờ 5 giây...")
                await asyncio.sleep(5)
                resp = await client.post(url, json=payload)

            if resp.status_code in (400, 403):
                err = resp.json()
                msg = err.get("error", {}).get("message", "Unknown error")
                print(f"  ❌ Imagen error: {msg}")
                return None

            resp.raise_for_status()
            data = resp.json()

        # Decode base64 image
        predictions = data.get("predictions", [])
        if not predictions:
            print("  ❌ Imagen: không có kết quả")
            return None

        img_b64 = predictions[0].get("bytesBase64Encoded", "")
        if not img_b64:
            print("  ❌ Imagen: response không có image data")
            return None

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(img_b64))

        size_kb = os.path.getsize(output_path) // 1024
        print(f"  ✅ Imagen 3 image: {Path(output_path).name} ({size_kb}KB)")
        return output_path

    except Exception as e:
        print(f"  ❌ Imagen exception: {e}")
        return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def is_gemini_available() -> bool:
    """Kiểm tra Gemini API key đã được cấu hình chưa."""
    return bool(settings.gemini_api_key and settings.gemini_api_key not in ("", "your-key"))


def is_openai_available() -> bool:
    """Kiểm tra OpenAI API key đã được cấu hình chưa."""
    return bool(settings.openai_api_key and settings.openai_api_key not in ("", "sk-..."))


def get_active_provider() -> str:
    """Trả về provider đang active dựa trên config và key availability."""
    if settings.ai_provider == "gemini" and is_gemini_available():
        return "gemini"
    if settings.ai_provider == "openai" and is_openai_available():
        return "openai"
    # Auto-fallback
    if is_gemini_available():
        return "gemini"
    if is_openai_available():
        return "openai"
    return "none"
