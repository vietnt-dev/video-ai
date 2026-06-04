"""
Media Service — Hybrid pipeline tạo video cho từng segment.

Thứ tự ưu tiên (theo config MEDIA_SOURCE):
1. "pexels"      → chỉ dùng Pexels stock
2. "ai_image"    → tạo ảnh AI + Ken Burns, bám sát nội dung hơn
3. "ai_image_sd" → chỉ dùng Stable Diffusion + Ken Burns
4. "hybrid"      → Pexels trước, fallback sang AI image
"""
import asyncio
import httpx
import os
import re
from pathlib import Path
from app.config import settings

PEXELS_BASE_URL = "https://api.pexels.com/videos"

FALLBACK_KEYWORDS = [
    "documentary close up", "person working", "hands close up",
    "Vietnam street", "office desk", "family home",
    "healthy food", "science experiment",
]

QUERY_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "with", "by", "in",
    "on", "at", "from", "into", "about", "through", "visualizing", "showing",
    "representing", "illustrating", "concept", "scene", "video", "footage",
    "cinematic", "dramatic", "beautiful", "realistic", "high", "quality",
}


# ─── Pexels ───────────────────────────────────────────────────────────────────

def _is_valid_file(path: str, min_size: int = 10_000) -> bool:
    if not path or not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size:
        os.remove(path)
        return False
    return True


def build_pexels_queries(prompt: str) -> list[str]:
    """Tạo vài query ngắn nhưng giữ đúng chủ thể chính của visual prompt."""
    cleaned = re.sub(r"[^a-zA-Z0-9,\s-]", " ", prompt).strip()
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    queries = []
    if parts:
        queries.append(" ".join(parts[0].split()[:5]))
    if len(parts) > 1:
        queries.append(" ".join((parts[0] + " " + parts[1]).split()[:6]))

    words = [
        word.lower()
        for word in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", cleaned)
        if word.lower() not in QUERY_STOPWORDS
    ]
    if words:
        queries.append(" ".join(words[:5]))

    unique_queries = []
    for query in queries:
        query = " ".join(query.split())
        if query and query.lower() not in {q.lower() for q in unique_queries}:
            unique_queries.append(query)

    return unique_queries[:3] or ["documentary close up"]


async def search_pexels_videos(query: str, per_page: int = 5) -> list[dict]:
    if not settings.pexels_api_key or settings.pexels_api_key in ("...", ""):
        return []

    short_query = " ".join(query.split()[:6])
    headers = {
        "Authorization": settings.pexels_api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {"query": short_query, "per_page": per_page, "size": "medium"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{PEXELS_BASE_URL}/search", headers=headers, params=params)
            if resp.status_code in (401, 403):
                print("❌ Pexels API key không hợp lệ")
                return []
            if resp.status_code == 429:
                await asyncio.sleep(2)
                return []
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"⚠️  Pexels error: {e}")
        return []

    videos = []
    for video in data.get("videos", []):
        files = video.get("video_files", [])
        if not files:
            continue
        # Ưu tiên HD portrait → HD landscape → bất kỳ
        chosen = (
            next((f for f in files if f.get("quality") == "hd" and f.get("height", 0) > f.get("width", 0)), None)
            or next((f for f in files if f.get("quality") == "hd"), None)
            or files[0]
        )
        if chosen and chosen.get("link"):
            videos.append({"id": video["id"], "url": chosen["link"], "duration": video.get("duration", 10)})

    print(f"  📹 Pexels '{short_query}': {len(videos)} kết quả")
    return videos


async def _download_file(url: str, output_path: str) -> bool:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=5.0),
            follow_redirects=True,
        ) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                bytes_written = 0
                with open(output_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 512):
                        if not chunk:
                            continue
                        f.write(chunk)
                        bytes_written += len(chunk)
            if bytes_written < 10_000:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
        return True
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


async def _try_pexels(prompt: str, output_path: str, segment_index: int) -> bool:
    """Thử tải video từ Pexels với fallback keywords."""
    for query in build_pexels_queries(prompt):
        videos = await search_pexels_videos(query, per_page=6)
        if videos:
            for v in videos[:3]:
                if await _download_file(v["url"], output_path) and _is_valid_file(output_path):
                    return True

    # Fallback keyword
    kw = FALLBACK_KEYWORDS[segment_index % len(FALLBACK_KEYWORDS)]
    print(f"  🔄 Pexels fallback: '{kw}'")
    videos = await search_pexels_videos(kw, per_page=5)
    if videos:
        for v in videos[:2]:
            if await _download_file(v["url"], output_path) and _is_valid_file(output_path):
                return True

    return False


# ─── AI Image → Ken Burns Video ───────────────────────────────────────────────

async def _try_ai_image(
    prompt: str,
    video_output_path: str,
    duration: float,
    segment_index: int,
    style: str = "engaging",
    engine: str = "dalle3",
) -> bool:
    """Tạo ảnh AI rồi convert sang video với Ken Burns effect."""
    from app.services.ai_image_service import generate_image
    from app.services.ken_burns_service import image_to_video

    # Lưu ảnh tạm
    img_dir = Path(settings.assets_dir) / "images" / Path(video_output_path).parent.name
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = str(img_dir / f"img_{segment_index:02d}.jpg")

    # Tạo ảnh AI
    result = await generate_image(prompt, img_path, style=style, engine=engine)
    if not result or not _is_valid_file(img_path, min_size=5_000):
        return False

    # Convert ảnh → video với Ken Burns
    try:
        await asyncio.to_thread(
            image_to_video,
            image_path=img_path,
            output_path=video_output_path,
            duration=duration,
            effect="auto",
            style=style,
        )
        return _is_valid_file(video_output_path)
    except Exception as e:
        print(f"  ❌ Ken Burns error: {e}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

async def fetch_media_for_segments(
    visual_prompts: list[str],
    job_id: str,
    durations: list[float] = None,
    style: str = "engaging",
    media_source: str = "hybrid",
    script = None,
    topic: str = "",
) -> list[str | None]:
    """
    Tải/tạo video cho từng segment theo strategy được cấu hình.

    Args:
        visual_prompts: danh sách mô tả hình ảnh (tiếng Anh)
        job_id        : ID job để tạo thư mục riêng
        durations     : thời lượng mỗi segment (cần cho Ken Burns)
        style         : phong cách video (ảnh hưởng AI image prompt)
        media_source  : nguồn video (hybrid, pexels, ai_image, slide)
        script        : kịch bản đầy đủ (chứa dữ liệu slide)
        topic         : chủ đề của video (để viết tiêu đề slide)

    Returns: danh sách đường dẫn file video (None nếu thất bại)
    """
    video_dir = Path(settings.assets_dir) / "video" / job_id
    video_dir.mkdir(parents=True, exist_ok=True)

    if durations is None:
        durations = [8.0] * len(visual_prompts)

    source = media_source or settings.media_source
    concurrency = max(1, int(settings.media_concurrency or 1))
    semaphore = asyncio.Semaphore(concurrency)

    async def process_segment(i: int, prompt: str, duration: float) -> str | None:
        output_path = str(video_dir / f"clip_{i:02d}.mp4")
        print(f"\n[Segment {i+1}/{len(visual_prompts)}] '{prompt[:50]}...' ({duration:.1f}s)")

        if _is_valid_file(output_path):
            print(f"  ♻️ Segment {i+1}: dùng lại media đã có")
            return output_path

        success = False

        if source == "slide":
            from app.services.slide_service import (
                render_motion_slide_video,
            )
            from app.models import SlideContent

            slide_data = None
            if i == 0 and script:
                if style == "motion_tech":
                    slide_data = SlideContent(
                        layout="motion_tech",
                        title="TECH SHORT",
                        content=[
                            script.hook,
                            "Đáng thử",
                            "Nhanh · Rõ · Có proof",
                            "$ pnpm run web",
                            topic,
                            "Lưu video lại",
                        ],
                    )
                else:
                    slide_data = SlideContent(layout="title", title="DỪNG LẠI", content=[script.hook])
            elif i == len(visual_prompts) - 1 and script:
                slide_data = SlideContent(layout="comment_cta", title="BẠN NGHĨ SAO?", content=[script.call_to_action])
            elif script and (i - 1) < len(script.segments):
                seg = script.segments[i - 1]
                if hasattr(seg, "slide") and seg.slide:
                    slide_data = seg.slide
                else:
                    slide_data = SlideContent(layout="card", title="THÔNG TIN", content=[seg.text])
            else:
                slide_data = SlideContent(layout="card", title="THÔNG TIN", content=[prompt])

            try:
                await asyncio.to_thread(
                    render_motion_slide_video,
                    slide_data,
                    duration,
                    output_path,
                    topic,
                )
                success = True
            except Exception as e:
                raise RuntimeError(f"Motion slide render failed at segment {i+1}: {e}") from e

        elif source == "pexels":
            success = await _try_pexels(prompt, output_path, i)

        elif source == "ai_image":
            success = await _try_ai_image(prompt, output_path, duration, i, style, "auto")
            if not success:
                print("  🔄 AI image thất bại → thử Pexels")
                success = await _try_pexels(prompt, output_path, i)

        elif source == "ai_image_sd":
            success = await _try_ai_image(prompt, output_path, duration, i, style, "sdxl")

        elif source == "hybrid":
            # 1. Thử Pexels trước (miễn phí, nhanh)
            if settings.pexels_api_key and settings.pexels_api_key not in ("...", ""):
                success = await _try_pexels(prompt, output_path, i)

            # 2. Fallback sang AI image nếu Pexels thất bại
            if not success:
                print(f"  🎨 Pexels thất bại → dùng AI image")
                success = await _try_ai_image(prompt, output_path, duration, i, style, "auto")

        if success:
            return output_path

        raise RuntimeError(
            f"Không tạo được media cho segment {i+1}/{len(visual_prompts)}. "
            f"source={source}. Hãy kiểm tra PEXELS_API_KEY/GEMINI image/OpenAI image "
            "hoặc chọn 'Slide Trình Chiếu' để render bằng motion text."
        )

    async def bounded_process(i: int, prompt: str, duration: float) -> str | None:
        async with semaphore:
            result = await process_segment(i, prompt, duration)
            await asyncio.sleep(0.5)
            return result

    video_files = await asyncio.gather(
        *[
            bounded_process(i, prompt, duration)
            for i, (prompt, duration) in enumerate(zip(visual_prompts, durations))
        ]
    )
    success_count = sum(1 for path in video_files if path)

    print(f"\n📊 Media: {success_count}/{len(visual_prompts)} segments có video/ảnh")
    return video_files
