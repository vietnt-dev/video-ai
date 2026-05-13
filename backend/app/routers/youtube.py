"""
YouTube API Router.

Endpoints:
  GET  /api/youtube/status          → kiểm tra đã kết nối chưa + info channel
  GET  /api/youtube/oauth/authorize → lấy URL để redirect user đến Google
  GET  /api/youtube/oauth/callback  → Google redirect về đây sau khi user approve
  DELETE /api/youtube/disconnect    → ngắt kết nối (xóa token)
  POST /api/youtube/upload/{job_id} → upload video đã render lên YouTube
"""
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.services.youtube_service import (
    get_authorization_url,
    exchange_code_for_token,
    get_channel_info,
    is_youtube_connected,
    disconnect_youtube,
    upload_video_to_youtube,
)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


# ─── Models ───────────────────────────────────────────────────────────────────

class UploadRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    tags: Optional[list[str]] = []
    privacy: Optional[str] = "public"  # public | unlisted | private


class YouTubeStatusResponse(BaseModel):
    connected: bool
    channel: Optional[dict] = None
    authorize_url: Optional[str] = None


class UploadResponse(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    privacy: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status", response_model=YouTubeStatusResponse)
async def youtube_status():
    """
    Kiểm tra trạng thái kết nối YouTube.
    Nếu chưa kết nối → trả về authorize_url để frontend redirect.
    """
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        raise HTTPException(
            status_code=503,
            detail="YouTube chưa được cấu hình. Thêm YOUTUBE_CLIENT_ID và YOUTUBE_CLIENT_SECRET vào .env",
        )

    if not is_youtube_connected():
        return YouTubeStatusResponse(
            connected=False,
            authorize_url=f"/api/youtube/oauth/authorize",
        )

    try:
        channel = await get_channel_info()
        return YouTubeStatusResponse(connected=True, channel=channel)
    except Exception as e:
        # Token có thể hết hạn hoặc bị revoke
        disconnect_youtube()
        return YouTubeStatusResponse(
            connected=False,
            authorize_url=f"/api/youtube/oauth/authorize",
        )


@router.get("/oauth/authorize")
async def oauth_authorize():
    """Redirect user đến Google OAuth2 consent screen."""
    if not settings.youtube_client_id:
        raise HTTPException(status_code=503, detail="YouTube Client ID chưa được cấu hình")

    auth_url = get_authorization_url(state="autoshorts")
    return RedirectResponse(url=auth_url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
):
    """
    Google redirect về đây sau khi user approve.
    Đổi code lấy token rồi redirect về frontend.
    """
    if error:
        # User từ chối hoặc có lỗi
        return RedirectResponse(
            url=f"http://localhost:3000?youtube_error={error}"
        )

    if not code:
        raise HTTPException(status_code=400, detail="Thiếu authorization code")

    try:
        await exchange_code_for_token(code)
        # Redirect về frontend với thông báo thành công
        return RedirectResponse(
            url="http://localhost:3000?youtube_connected=true"
        )
    except Exception as e:
        return RedirectResponse(
            url=f"http://localhost:3000?youtube_error={str(e)}"
        )


@router.delete("/disconnect")
async def disconnect():
    """Ngắt kết nối YouTube (xóa token)."""
    disconnect_youtube()
    return {"message": "Đã ngắt kết nối YouTube"}


@router.post("/upload/{job_id}", response_model=UploadResponse)
async def upload_to_youtube(job_id: str, request: UploadRequest):
    """
    Upload video đã render lên YouTube Shorts.

    Yêu cầu:
    - Video phải đã render xong (job status = completed)
    - Đã kết nối YouTube (authorize trước)
    """
    # Kiểm tra file video tồn tại
    video_path = f"{settings.output_dir}/{job_id}.mp4"
    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail="Video chưa sẵn sàng. Hãy đợi render xong trước.",
        )

    # Kiểm tra đã kết nối YouTube chưa
    if not is_youtube_connected():
        raise HTTPException(
            status_code=401,
            detail="Chưa kết nối YouTube. Vui lòng authorize tại /api/youtube/oauth/authorize",
        )

    # Kiểm tra cấu hình
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        raise HTTPException(
            status_code=503,
            detail="YouTube chưa được cấu hình trong .env",
        )

    try:
        result = await upload_video_to_youtube(
            video_path=video_path,
            title=request.title,
            description=request.description or "",
            tags=request.tags or [],
            privacy=request.privacy or "public",
        )
        return UploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload thất bại: {str(e)}")
