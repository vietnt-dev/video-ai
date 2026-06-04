"""
AI Image Generation Service.

Hỗ trợ 2 engine:
1. DALL-E 3 (OpenAI) — chất lượng cao, ~$0.04/ảnh 1024x1792
2. Stable Diffusion XL (Replicate) — rẻ hơn ~10x, ~$0.003/ảnh

Ảnh được tạo theo tỷ lệ 9:16 (portrait) để phù hợp Shorts.
Sau đó dùng Ken Burns effect (zoom + pan) để tạo chuyển động.
"""
import asyncio
import httpx
import os
import time
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


# ─── Prompt Enhancement ───────────────────────────────────────────────────────

def _enhance_prompt_for_shorts(visual_prompt: str, style: str = "engaging") -> str:
    """
    Tối ưu prompt cho ảnh dọc 9:16, phong cách cinematic.
    """
    style_modifiers = {
        "co_nhan":     "realistic Vietnamese wisdom scene, one elder scholar or one quiet study room, warm candlelight, reflective mood",
        "tu_vi":       "tasteful Vietnamese astrology scene, one table with compass and candlelight, mystical but realistic",
        "su_that":     "photorealistic documentary scene, dramatic lighting, high contrast",
        "tam_ly":      "minimalist modern Vietnamese lifestyle scene, one thoughtful person, soft natural lighting",
        "lam_giau":    "modern Vietnamese personal finance scene, one office desk with bills and charts, realistic modest success imagery",
        "suc_khoe":    "Vietnamese home kitchen scene with fresh herbs and vegetables, warm natural light",
        "tinh_cam":    "warm realistic Vietnamese family moment, one natural emotional scene, soft natural light",
        "engaging":    "cinematic realistic scene, dramatic lighting, high impact visual",
        "educational": "clean realistic educational scene, one clear subject, bright natural lighting",
        "funny":       "realistic relatable Vietnamese everyday scene, vibrant colors, natural composition",
    }

    modifier = style_modifiers.get(style, style_modifiers["engaging"])

    return (
        f"{visual_prompt}, {modifier}, "
        f"unexpected but realistic visual metaphor when appropriate, clear tension or contrast, "
        f"single full-frame scene, one continuous image, one main subject, "
        f"visible human action or concrete object, instantly understandable in one second, "
        f"vertical 9:16 portrait format, professional photography, sharp focus, vibrant colors, "
        f"authentic Vietnamese context when relevant, not generic stock-photo posing, "
        f"no collage, no split screen, no grid, no panels, no montage, no contact sheet, "
        f"no before and after layout, no multiple photos in one image, "
        f"no text, no subtitles, no logo, no watermark"
    )


# ─── DALL-E 3 ─────────────────────────────────────────────────────────────────

async def generate_image_dalle3(
    prompt: str,
    output_path: str,
    style: str = "engaging",
) -> Optional[str]:
    """
    Tạo ảnh bằng DALL-E 3.
    Size 1024x1792 = tỷ lệ 9:16 portrait.
    Chi phí: $0.04/ảnh (standard), $0.08/ảnh (HD)
    """
    enhanced = _enhance_prompt_for_shorts(prompt, style)

    try:
        response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=enhanced,
            size="1024x1792",   # 9:16 portrait
            quality="standard", # "hd" cho chất lượng cao hơn, giá gấp đôi
            n=1,
        )

        image_url = response.data[0].url
        return await _download_image(image_url, output_path)

    except Exception as e:
        print(f"  ❌ DALL-E 3 error: {e}")
        return None


# ─── Stable Diffusion XL (Replicate) ─────────────────────────────────────────

SDXL_MODEL = "stability-ai/sdxl:39ed52f2319f9b0b510d6f1c4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e4e"

async def generate_image_sdxl(
    prompt: str,
    output_path: str,
    style: str = "engaging",
) -> Optional[str]:
    """
    Tạo ảnh bằng Stable Diffusion XL qua Replicate API.
    Chi phí: ~$0.003/ảnh
    """
    if not settings.replicate_api_token:
        print("  ⚠️  REPLICATE_API_TOKEN chưa set")
        return None

    enhanced = _enhance_prompt_for_shorts(prompt, style)

    headers = {
        "Authorization": f"Token {settings.replicate_api_token}",
        "Content-Type": "application/json",
    }

    # Tạo prediction
    payload = {
        "version": "7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
        "input": {
            "prompt": enhanced,
            "negative_prompt": "blurry, low quality, distorted, watermark, text, logo",
            "width": 768,
            "height": 1344,  # ~9:16
            "num_inference_steps": 25,
            "guidance_scale": 7.5,
            "scheduler": "K_EULER",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            prediction = resp.json()

        prediction_id = prediction["id"]

        # Poll cho đến khi xong (tối đa 60 giây)
        for _ in range(30):
            await asyncio.sleep(2)
            async with httpx.AsyncClient(timeout=10.0) as client:
                poll = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers=headers,
                )
                data = poll.json()

            if data["status"] == "succeeded":
                image_url = data["output"][0]
                return await _download_image(image_url, output_path)
            elif data["status"] == "failed":
                print(f"  ❌ SDXL failed: {data.get('error')}")
                return None

        print("  ❌ SDXL timeout")
        return None

    except Exception as e:
        print(f"  ❌ SDXL error: {e}")
        return None


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _download_image(url: str, output_path: str) -> Optional[str]:
    """Download ảnh từ URL về file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

        size_kb = os.path.getsize(output_path) // 1024
        print(f"  ✅ AI image saved: {Path(output_path).name} ({size_kb}KB)")
        return output_path

    except Exception as e:
        print(f"  ❌ Image download error: {e}")
        return None


async def generate_image(
    prompt: str,
    output_path: str,
    style: str = "engaging",
    engine: str = "auto",
) -> Optional[str]:
    """
    Public API — tạo ảnh AI.

    Engine priority (auto):
    1. Imagen 3 (Gemini, MIỄN PHÍ) — nếu có GEMINI_API_KEY
    2. DALL-E 3 (OpenAI, $0.04/ảnh) — nếu có OPENAI_API_KEY
    3. SDXL (Replicate, $0.003/ảnh) — nếu có REPLICATE_API_TOKEN
    """
    from app.services.gemini_service import is_gemini_available, is_openai_available

    enhanced = _enhance_prompt_for_shorts(prompt, style)
    print(f"  🎨 Generating AI image: '{prompt[:50]}...'")

    # Auto-select engine
    if engine == "auto":
        if is_gemini_available():
            engine = "imagen3"
        elif is_openai_available():
            engine = "dalle3"
        elif settings.replicate_api_token:
            engine = "sdxl"
        else:
            print("  ❌ Không có API key nào để tạo ảnh AI")
            return None

    if engine == "imagen3":
        from app.services.gemini_service import imagen_generate
        result = await imagen_generate(enhanced, output_path, aspect_ratio="9:16")
        if result:
            return result
        print("  🔄 Imagen 3 failed, fallback to DALL-E 3")
        engine = "dalle3"

    if engine == "dalle3" and is_openai_available():
        result = await generate_image_dalle3(prompt, output_path, style)
        if result:
            return result
        print("  🔄 DALL-E 3 failed, fallback to SDXL")
        engine = "sdxl"

    if engine == "sdxl" and settings.replicate_api_token:
        return await generate_image_sdxl(prompt, output_path, style)

    return None
