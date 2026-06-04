"""
Celery tasks for the video generation pipeline.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from app.celery_app import celery_app
from app.config import settings
from app.models import VideoScript


def _redis_set_json(key: str, payload: dict[str, Any]) -> None:
    celery_app.backend.set(key, json.dumps(payload, ensure_ascii=False))
    try:
        celery_app.backend.client.expire(key, settings.job_meta_ttl_seconds)
    except Exception:
        pass


def _redis_get_json(key: str) -> dict[str, Any] | None:
    raw = celery_app.backend.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️ Redis JSON corrupt at {key}: {e}")
        try:
            celery_app.backend.delete(key)
        except Exception:
            pass
        return None


def update_job_progress(
    job_id: str,
    progress: int,
    message: str,
    status: str = "processing",
    extra: dict | None = None,
) -> None:
    """Store job progress in Redis with a TTL."""
    payload = {
        "status": status,
        "progress": progress,
        "message": message,
    }
    if extra:
        payload.update(extra)

    _redis_set_json(f"job_meta:{job_id}", payload)


def _checkpoint_key(job_id: str) -> str:
    return f"job_checkpoint:{job_id}"


def _get_checkpoint(job_id: str) -> dict[str, Any]:
    return _redis_get_json(_checkpoint_key(job_id)) or {"steps": {}, "artifacts": {}}


def _save_checkpoint(job_id: str, step: str, artifacts: dict[str, Any] | None = None) -> None:
    checkpoint = _get_checkpoint(job_id)
    checkpoint.setdefault("steps", {})[step] = {
        "status": "done",
        "completed_at": time.time(),
    }
    if artifacts:
        checkpoint.setdefault("artifacts", {}).update(artifacts)
    _redis_set_json(_checkpoint_key(job_id), checkpoint)


def _valid_file(path: str | None, min_size: int = 1_000) -> bool:
    return bool(path and os.path.exists(path) and os.path.getsize(path) >= min_size)


def _all_valid(paths: list[str | None], min_size: int = 1_000) -> bool:
    return bool(paths) and all(_valid_file(path, min_size=min_size) for path in paths)


def _script_path(job_id: str) -> Path:
    return Path(settings.assets_dir) / "audio" / job_id / "script.json"


def _media_manifest_path(job_id: str) -> Path:
    return Path(settings.assets_dir) / "video" / job_id / "media_manifest.json"


def _build_pipeline_inputs(script: VideoScript, topic: str) -> dict[str, list]:
    return {
        "texts": [script.hook] + [seg.text for seg in script.segments] + [script.call_to_action],
        "part_types": ["hook"] + ["body"] * len(script.segments) + ["cta"],
        "visual_prompts": (
            [f"{topic} dramatic opening"]
            + [seg.visual_prompt for seg in script.segments]
            + [f"{topic} call to action"]
        ),
        "durations": [2.4] + [seg.duration for seg in script.segments] + [2.8],
    }


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
    Main task: orchestrate the full video generation workflow.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _run_pipeline(
                job_id,
                topic,
                style,
                language,
                auto_upload_youtube,
                youtube_privacy,
                media_source,
            )
        )
        return result
    except Exception as e:
        update_job_progress(job_id, 0, f"❌ Lỗi: {str(e)}", "failed")
        raise
    finally:
        loop.close()


async def _step_generate_script(
    job_id: str,
    topic: str,
    style: str,
    language: str,
    media_source: str,
) -> VideoScript:
    from app.services.script_service import generate_script

    path = _script_path(job_id)
    if path.exists():
        print(f"[{job_id}] Reusing checkpoint: script")
        return VideoScript.model_validate_json(path.read_text(encoding="utf-8"))

    update_job_progress(job_id, 5, "🤖 Đang viết kịch bản với AI...")
    try:
        script = await generate_script(topic, style, language, media_source)
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise RuntimeError(
                "AI provider đang hết quota hoặc bị rate limit. "
                "Hãy kiểm tra API key/quota hoặc thử lại sau."
            )
        raise

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script.model_dump_json(indent=2), encoding="utf-8")
    _save_checkpoint(job_id, "script", {"script_path": str(path)})
    return script


async def _step_generate_seo(
    job_id: str,
    topic: str,
    script: VideoScript,
    language: str,
) -> dict:
    cached = _redis_get_json(f"seo_meta:{job_id}")
    if cached:
        print(f"[{job_id}] Reusing checkpoint: seo")
        return cached

    update_job_progress(job_id, 15, "🔍 Đang tối ưu SEO cho YouTube...")
    from app.services.seo_service import generate_ab_test_titles, generate_youtube_seo

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
    _redis_set_json(f"seo_meta:{job_id}", seo_data)
    _save_checkpoint(job_id, "seo")
    return seo_data


async def _step_generate_tts(
    job_id: str,
    texts: list[str],
    part_types: list[str],
    language: str,
    style: str,
) -> list[str]:
    from app.services.tts_service import generate_full_narration

    audio_paths = [
        str(Path(settings.assets_dir) / "audio" / job_id / f"segment_{i:02d}.mp3")
        for i in range(len(texts))
    ]
    if _all_valid(audio_paths, min_size=1_000):
        print(f"[{job_id}] Reusing checkpoint: tts")
        _save_checkpoint(job_id, "tts", {"audio_paths": audio_paths})
        return audio_paths

    engine_name = "ElevenLabs" if settings.tts_engine == "elevenlabs" else "Microsoft Edge TTS"
    update_job_progress(job_id, 25, f"🎙️ Đang tạo giọng đọc ({engine_name})...")
    audio_paths = await generate_full_narration(
        texts,
        job_id,
        language=language,
        style=style,
        part_types=part_types,
    )
    _save_checkpoint(job_id, "tts", {"audio_paths": audio_paths})
    return audio_paths


async def _step_generate_media(
    job_id: str,
    visual_prompts: list[str],
    durations: list[float],
    style: str,
    media_source: str,
    script: VideoScript,
    topic: str,
) -> list[str | None]:
    from app.services.media_service import fetch_media_for_segments

    manifest_path = _media_manifest_path(job_id)
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            video_files = data.get("video_files", [])
            if _all_valid(video_files, min_size=10_000):
                print(f"[{job_id}] Reusing checkpoint: media")
                _save_checkpoint(job_id, "media", {"video_files": video_files})
                return video_files
        except json.JSONDecodeError as e:
            print(f"⚠️ Media manifest corrupt for {job_id}, regenerating media: {e}")

    source_label = {
        "pexels": "Pexels stock",
        "ai_image": "AI image + motion",
        "ai_image_sd": "Stable Diffusion AI",
        "hybrid": "Pexels + AI fallback",
        "slide": "Slide bài giảng",
    }.get(media_source or settings.media_source, "media")
    update_job_progress(job_id, 45, f"🎨 Đang tạo hình ảnh/video ({source_label})...")

    video_files = await fetch_media_for_segments(
        visual_prompts=visual_prompts,
        job_id=job_id,
        durations=durations,
        style=style,
        media_source=media_source,
        script=script,
        topic=topic,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"video_files": video_files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _save_checkpoint(job_id, "media", {"video_files": video_files})
    return video_files


def _step_render_video(
    job_id: str,
    video_files: list[str | None],
    audio_files: list[str],
    durations: list[float],
    texts: list[str],
    caption_mode: str = "full",
) -> str:
    from app.services.video_service import compose_video

    output_path = str(Path(settings.output_dir) / f"{job_id}.mp4")
    if _valid_file(output_path, min_size=50_000):
        print(f"[{job_id}] Reusing checkpoint: render")
        _save_checkpoint(job_id, "render", {"video_path": output_path})
        return output_path

    update_job_progress(job_id, 70, "🎞️ Đang render video...")
    music_dir = Path(settings.assets_dir) / "music"
    music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    music_path = str(music_files[0]) if music_files else None

    compose_video(
        video_clips_paths=video_files,
        audio_paths=audio_files,
        durations=durations,
        script_texts=texts,
        output_path=output_path,
        music_path=music_path,
        use_dynamic_captions=True,
        caption_mode=caption_mode,
    )
    _save_checkpoint(job_id, "render", {"video_path": output_path})
    return output_path


async def _step_upload_youtube(
    job_id: str,
    output_path: str,
    topic: str,
    script: VideoScript,
    seo_data: dict,
    youtube_privacy: str,
) -> dict | None:
    update_job_progress(job_id, 90, "📤 Đang upload lên YouTube Shorts...")
    try:
        from app.services.youtube_service import is_youtube_connected, upload_video_to_youtube

        if not is_youtube_connected():
            update_job_progress(job_id, 90, "⚠️ Chưa kết nối YouTube — bỏ qua upload tự động")
            return None

        yt_title = seo_data.get("title") or script.suggested_title or f"{topic} #Shorts"
        yt_desc = seo_data.get("description") or script.suggested_description or topic
        yt_tags = seo_data.get("tags") or script.keywords or [topic]
        result = await upload_video_to_youtube(
            video_path=output_path,
            title=yt_title,
            description=yt_desc,
            tags=yt_tags,
            privacy=youtube_privacy,
        )
        _save_checkpoint(job_id, "youtube", {"youtube": result})
        return result
    except Exception as e:
        print(f"⚠️ YouTube upload failed: {e}")
        return {"error": str(e)}


async def _run_pipeline(
    job_id: str,
    topic: str,
    style: str,
    language: str,
    auto_upload_youtube: bool,
    youtube_privacy: str,
    media_source: str,
) -> dict:
    """Run the pipeline with resumable checkpoints."""
    from app.services.artifact_service import cleanup_old_artifacts

    cleanup_old_artifacts()
    timings: dict[str, float] = {}
    total_start = time.time()

    step_start = time.time()
    script = await _step_generate_script(job_id, topic, style, language, media_source)
    timings["script"] = round(time.time() - step_start, 2)

    step_start = time.time()
    seo_data = await _step_generate_seo(job_id, topic, script, language)
    timings["seo"] = round(time.time() - step_start, 2)

    inputs = _build_pipeline_inputs(script, topic)

    step_start = time.time()
    audio_files = await _step_generate_tts(
        job_id,
        inputs["texts"],
        inputs["part_types"],
        language,
        style,
    )
    timings["tts"] = round(time.time() - step_start, 2)

    step_start = time.time()
    video_files = await _step_generate_media(
        job_id,
        inputs["visual_prompts"],
        inputs["durations"],
        style,
        media_source,
        script,
        topic,
    )
    timings["media"] = round(time.time() - step_start, 2)

    step_start = time.time()
    output_path = _step_render_video(
        job_id,
        video_files,
        audio_files,
        inputs["durations"],
        inputs["texts"],
        caption_mode="keyword_only" if media_source == "slide" else "full",
    )
    timings["render"] = round(time.time() - step_start, 2)

    youtube_result = None
    if auto_upload_youtube:
        youtube_result = await _step_upload_youtube(
            job_id,
            output_path,
            topic,
            script,
            seo_data,
            youtube_privacy,
        )

    timings["total"] = round(time.time() - total_start, 2)
    done_message = f"✅ Video đã sẵn sàng! (Tổng: {int(timings['total'])}s)"
    extra: dict[str, Any] = {"timings": timings}

    if youtube_result and "youtube_url" in youtube_result:
        done_message = f"✅ Video đã đăng YouTube! (Tổng: {int(timings['total'])}s)"
        extra.update({
            "youtube_url": youtube_result["youtube_url"],
            "youtube_video_id": youtube_result["video_id"],
        })

    update_job_progress(job_id, 100, done_message, "completed", extra)
    cleanup_old_artifacts()

    return {
        "job_id": job_id,
        "status": "completed",
        "video_path": output_path,
        "script": script.model_dump(),
        "youtube": youtube_result,
        "seo": seo_data,
    }
