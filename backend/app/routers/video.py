"""
Video generation API endpoints.
"""
import json
import uuid
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models import GenerateVideoRequest, JobResponse, JobStatusResponse, JobStatus
from app.config import settings

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/generate", response_model=JobResponse)
async def generate_video(request: GenerateVideoRequest):
    """
    Khởi động job tạo video.
    Trả về job_id để theo dõi tiến trình.
    """
    from app.tasks.video_tasks import generate_video_task

    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic không được để trống")

    job_id = str(uuid.uuid4())

    # Dispatch Celery task
    generate_video_task.apply_async(
        args=[
            job_id,
            request.topic,
            request.style,
            request.language,
            request.auto_upload_youtube,
            request.youtube_privacy,
            request.media_source,
        ],
        task_id=job_id,
    )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Job đã được tạo, đang xử lý...",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Kiểm tra trạng thái job theo job_id.
    Poll endpoint này mỗi 3-5 giây từ frontend.
    """
    from app.celery_app import celery_app

    # Lấy metadata từ Redis
    meta_key = f"job_meta:{job_id}"
    meta_raw = celery_app.backend.get(meta_key)

    if meta_raw:
        meta = json.loads(meta_raw)
        status = JobStatus(meta.get("status", "processing"))
        progress = meta.get("progress", 0)
        message = meta.get("message", "Đang xử lý...")

        video_url = None
        if status == JobStatus.COMPLETED:
            video_path = f"{settings.output_dir}/{job_id}.mp4"
            if os.path.exists(video_path):
                video_url = f"/api/video/download/{job_id}"

        return JobStatusResponse(
            job_id=job_id,
            status=status,
            progress=progress,
            message=message,
            video_url=video_url,
            youtube_url=meta.get("youtube_url"),
            youtube_video_id=meta.get("youtube_video_id"),
        )
    # Kiểm tra Celery task state
    task = celery_app.AsyncResult(job_id)

    if task.state == "PENDING":
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            progress=0,
            message="Đang chờ worker xử lý...",
        )
    elif task.state == "FAILURE":
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus.FAILED,
            progress=0,
            message="Job thất bại",
            error=str(task.result),
        )

    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        progress=10,
        message="Đang khởi động...",
    )


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    """Tải file video đã render."""
    video_path = f"{settings.output_dir}/{job_id}.mp4"

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video chưa sẵn sàng hoặc không tồn tại")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"autoshorts_{job_id[:8]}.mp4",
    )


@router.get("/stream/{job_id}")
async def stream_video(job_id: str):
    """Stream video để xem trực tiếp trong browser."""
    video_path = f"{settings.output_dir}/{job_id}.mp4"

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video không tồn tại")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/styles")
async def get_styles():
    """Trả về danh sách tất cả phong cách nội dung."""
    from app.services.style_prompts import get_all_styles
    return {"styles": get_all_styles()}


@router.get("/debug/pexels")
async def debug_pexels():
    """Kiểm tra Pexels API key có hoạt động không."""
    from app.services.media_service import search_pexels_videos

    if not settings.pexels_api_key or settings.pexels_api_key in ("...", ""):
        return {
            "status": "error",
            "message": "PEXELS_API_KEY chưa được set trong .env",
            "fix": "Lấy API key miễn phí tại https://www.pexels.com/api/",
        }

    try:
        videos = await search_pexels_videos("nature", per_page=2)
        if videos:
            return {
                "status": "ok",
                "message": f"Pexels hoạt động tốt — tìm thấy {len(videos)} video",
                "sample": videos[0],
            }
        return {"status": "warning", "message": "API key hợp lệ nhưng không tìm thấy video"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/debug/media-config")
async def debug_media_config():
    """Kiểm tra cấu hình media source hiện tại."""
    from app.services.gemini_service import get_active_provider, is_gemini_available, is_openai_available
    provider = get_active_provider()
    return {
        "ai_provider_config": settings.ai_provider,
        "active_provider": provider,
        "gemini_configured": is_gemini_available(),
        "openai_configured": is_openai_available(),
        "replicate_configured": bool(settings.replicate_api_token),
        "pexels_configured": bool(settings.pexels_api_key and settings.pexels_api_key not in ("...", "")),
        "media_source": settings.media_source,
        "image_engine": "imagen3 (free)" if is_gemini_available() else ("dalle3" if is_openai_available() else "none"),
        "cost_per_video_estimate": "~$0 (Gemini free)" if is_gemini_available() else "~$0.05 (OpenAI)",
    }


@router.get("/debug/test-gemini")
async def test_gemini():
    """Test Gemini API key có hoạt động không."""
    from app.services.gemini_service import is_gemini_available, gemini_generate

    if not is_gemini_available():
        return {
            "status": "not_configured",
            "message": "GEMINI_API_KEY chưa set",
            "fix": "Lấy key miễn phí tại https://aistudio.google.com/apikey",
        }
    try:
        result = await gemini_generate(
            system_prompt="Trả lời bằng JSON",
            user_prompt='Trả về {"status": "ok", "message": "Gemini hoạt động tốt"}',
            json_mode=True,
        )
        import json
        data = json.loads(result)
        return {"status": "ok", "gemini_response": data, "model": settings.gemini_model}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/seo/{job_id}")
async def get_seo_metadata(job_id: str):
    """
    Lấy SEO metadata đã được tối ưu cho YouTube Shorts.
    Trả về title, description, tags, hashtags và A/B test titles.
    """
    from app.celery_app import celery_app

    raw = celery_app.backend.get(f"seo_meta:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="SEO data chưa sẵn sàng")

    return json.loads(raw)
