"""
Celery tasks cho video generation pipeline.
Xử lý bất đồng bộ toàn bộ workflow tạo video + YouTube upload.
"""
import asyncio
import json
import os
import time
from pathlib import Path

from app.celery_app import celery_app
from app.config import settings
from app.models import VideoScript


def update_job_progress(
    job_id: str,
    progress: int,
    message: str,
    status: str = "processing",
    extra: dict = None,
):
    """Lưu trạng thái job vào Redis."""
    payload = {
        "status": status,
        "progress": progress,
        "message": message,
    }
    if extra:
        payload.update(extra)

    celery_app.backend.set(
        f"job_meta:{job_id}",
        json.dumps(payload),
    )


@celery_app.task(bind=True, name="generate_video")
def generate_video_task(
    self,
    job_id: str,
    topic: str,
    style: str = "engaging",
    language: str = "vi",
    auto_upload_youtube: bool = False,
    youtube_privacy: str = "public",
    media_source: str = "hybrid",
):
    """
    Main task: Orchestrate toàn bộ pipeline tạo video.

    Pipeline:
    1. Generate script (GPT-4o)
    2. Generate TTS audio (edge-tts / ElevenLabs)
    3. Fetch stock videos (Pexels)
    4. Compose final video (MoviePy)
    5. [Optional] Upload lên YouTube Shorts
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _run_pipeline(
                self, job_id, topic, style, language,
                auto_upload_youtube, youtube_privacy, media_source
            )
        )
        return result
    except Exception as e:
        update_job_progress(job_id, 0, f"❌ Lỗi: {str(e)}", "failed")
        raise
    finally:
        loop.close()


async def _run_pipeline(
    task,
    job_id: str,
    topic: str,
    style: str,
    language: str,
    auto_upload_youtube: bool,
    youtube_privacy: str,
    media_source: str,
) -> dict:
    """Async pipeline chính."""
    from app.services.script_service import generate_script
    from app.services.tts_service import generate_full_narration
    from app.services.media_service import fetch_media_for_segments
    from app.services.video_service import compose_video

    # ── Step 1: Generate Script ──────────────────────────────────────
    update_job_progress(job_id, 5, "🤖 Đang viết kịch bản với GPT-4o...")
    t0 = time.time()
    try:
        script: VideoScript = await generate_script(topic, style, language, media_source)
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise RuntimeError(
                "OpenAI API hết quota. Vui lòng nạp tiền tại platform.openai.com/settings/billing "
                "hoặc đổi sang gpt-4o-mini trong file .env (OPENAI_MODEL=gpt-4o-mini)"
            )
        raise

    # Lưu script để debug + dùng cho YouTube title
    script_path = f"{settings.assets_dir}/audio/{job_id}/script.json"
    Path(script_path).parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script.model_dump_json(indent=2))

    # ── Step 1b: Generate YouTube SEO Metadata ───────────────────────
    t1 = time.time()
    print(f"⏱️ [Step 1] Generate Script took: {t1 - t0:.2f}s")
    
    update_job_progress(job_id, 15, "🔍 Đang tối ưu SEO cho YouTube...")
    from app.services.seo_service import generate_youtube_seo, generate_ab_test_titles

    # Tóm tắt nội dung từ các segment
    script_summary = " ".join([seg.text for seg in script.segments[:3]])

    seo_data, ab_titles = await asyncio.gather(
        generate_youtube_seo(
            topic=topic,
            script_hook=script.hook,
            script_summary=script_summary,
            keywords=script.keywords,
            language=language,
        ),
        generate_ab_test_titles(
            topic=topic,
            script_hook=script.hook,
            keywords=script.keywords,
            count=3,
        ),
    )
    seo_data["ab_test_titles"] = ab_titles

    # Lưu SEO data vào Redis để frontend lấy
    celery_app.backend.set(
        f"seo_meta:{job_id}",
        json.dumps(seo_data, ensure_ascii=False),
    )

    # Chuẩn bị danh sách text cho TTS
    all_texts = [script.hook] + [seg.text for seg in script.segments] + [script.call_to_action]
    part_types = ["hook"] + ["body"] * len(script.segments) + ["cta"]
    all_visual_prompts = (
        [f"{topic} dramatic opening"]
        + [seg.visual_prompt for seg in script.segments]
        + [f"{topic} call to action"]
    )
    all_durations = (
        [2.4]
        + [seg.duration for seg in script.segments]
        + [2.8]
    )

    # ── Step 2: Text-to-Speech ───────────────────────────────────────
    t2 = time.time()
    print(f"⏱️ [Step 1b] Generate SEO took: {t2 - t1:.2f}s")
    
    engine_name = "ElevenLabs" if settings.tts_engine == "elevenlabs" else "Microsoft Edge TTS"
    update_job_progress(job_id, 20, f"🎙️ Đang tạo giọng đọc ({engine_name})...")
    audio_files = await generate_full_narration(
        all_texts,
        job_id,
        language=language,
        style=style,
        part_types=part_types,
    )

    # ── Step 3: Fetch / Generate Media ──────────────────────────────
    t3 = time.time()
    print(f"⏱️ [Step 2] Text-to-Speech took: {t3 - t2:.2f}s")
    
    source_label = {
        "pexels": "Pexels stock",
        "ai_image": "AI image + motion",
        "ai_image_sd": "Stable Diffusion AI",
        "hybrid": "Pexels + AI fallback",
        "slide": "Slide bài giảng",
    }.get(media_source or settings.media_source, "media")
    update_job_progress(job_id, 45, f"🎨 Đang tạo hình ảnh/video ({source_label})...")

    video_files = await fetch_media_for_segments(
        visual_prompts=all_visual_prompts,
        job_id=job_id,
        durations=all_durations,
        style=style,
        media_source=media_source,
        script=script,
        topic=topic,
    )

    # ── Step 4: Compose Video ────────────────────────────────────────
    t4 = time.time()
    print(f"⏱️ [Step 3] Fetch Media took: {t4 - t3:.2f}s")
    
    update_job_progress(job_id, 65, "🎞️ Đang render video (1-3 phút)...")

    output_path = f"{settings.output_dir}/{job_id}.mp4"

    music_dir = Path(f"{settings.assets_dir}/music")
    music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    music_path = str(music_files[0]) if music_files else None

    compose_video(
        video_clips_paths=video_files,
        audio_paths=audio_files,
        durations=all_durations,
        script_texts=all_texts,
        output_path=output_path,
        music_path=music_path,
        use_dynamic_captions=True,
    )

    # ── Step 5: YouTube Upload (optional) ───────────────────────────
    youtube_result = None
    if auto_upload_youtube:
        update_job_progress(job_id, 90, "📤 Đang upload lên YouTube Shorts...")
        try:
            from app.services.youtube_service import (
                upload_video_to_youtube,
                is_youtube_connected,
            )

            if not is_youtube_connected():
                update_job_progress(
                    job_id, 90,
                    "⚠️ Chưa kết nối YouTube — bỏ qua upload tự động",
                )
            else:
                # Dùng SEO title thay vì suggested_title cơ bản
                yt_title = seo_data.get("title") or script.suggested_title or f"{topic} #Shorts"
                yt_desc = seo_data.get("description") or script.suggested_description or topic
                yt_tags = seo_data.get("tags") or script.keywords or [topic]

                youtube_result = await upload_video_to_youtube(
                    video_path=output_path,
                    title=yt_title,
                    description=yt_desc,
                    tags=yt_tags,
                    privacy=youtube_privacy,
                )
        except Exception as e:
            # Không fail toàn bộ job nếu YouTube upload lỗi
            print(f"⚠️ YouTube upload failed: {e}")
            youtube_result = {"error": str(e)}

    # ── Done ─────────────────────────────────────────────────────────
    t5 = time.time()
    print(f"⏱️ [Step 4] Compose Video took: {t5 - t4:.2f}s")
    print(f"⏱️ [TOTAL] Entire pipeline took: {t5 - t0:.2f}s")
    
    done_message = f"✅ Video đã sẵn sàng! (Tổng: {int(t5 - t0)}s)"
    extra = {
        "timings": {
            "script": round(t1 - t0, 2),
            "seo": round(t2 - t1, 2),
            "tts": round(t3 - t2, 2),
            "media": round(t4 - t3, 2),
            "render": round(t5 - t4, 2),
            "total": round(t5 - t0, 2),
        }
    }

    if youtube_result and "youtube_url" in youtube_result:
        done_message = f"✅ Video đã đăng YouTube! (Tổng: {int(t5 - t0)}s)"
        extra.update({
            "youtube_url": youtube_result["youtube_url"],
            "youtube_video_id": youtube_result["video_id"],
        })

    update_job_progress(job_id, 100, done_message, "completed", extra)

    return {
        "job_id": job_id,
        "status": "completed",
        "video_path": output_path,
        "script": script.model_dump(),
        "youtube": youtube_result,
        "seo": seo_data,
    }
