"""
YouTube Upload Service — dùng YouTube Data API v3.

Flow OAuth2:
1. User click "Kết nối YouTube" → redirect đến Google OAuth
2. Google callback về /api/youtube/oauth/callback với ?code=...
3. Backend đổi code lấy access_token + refresh_token → lưu vào file
4. Từ đó về sau dùng refresh_token để tự động renew, không cần login lại

Upload flow:
- Dùng resumable upload (hỗ trợ file lớn, tự retry nếu mạng yếu)
- Set #Shorts trong title/description để YouTube nhận diện là Short
- Privacy: public (có thể đổi thành unlisted để review trước)
"""
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

# Google OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# YouTube API
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

# OAuth2 scopes cần thiết
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


# ─── Token Management ─────────────────────────────────────────────────────────

def _load_token() -> Optional[dict]:
    """Load token từ file."""
    token_file = Path(settings.youtube_token_file)
    if not token_file.exists():
        return None
    try:
        with open(token_file, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _save_token(token_data: dict) -> None:
    """Lưu token vào file."""
    token_file = Path(settings.youtube_token_file)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)


def _is_token_expired(token_data: dict) -> bool:
    """Kiểm tra token có hết hạn chưa (buffer 5 phút)."""
    expires_at = token_data.get("expires_at", 0)
    return time.time() > (expires_at - 300)


async def _refresh_access_token(refresh_token: str) -> dict:
    """Dùng refresh_token để lấy access_token mới."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

    token_data = _load_token() or {}
    token_data.update({
        "access_token": data["access_token"],
        "expires_at": time.time() + data.get("expires_in", 3600),
    })
    _save_token(token_data)
    return token_data


async def get_valid_access_token() -> str:
    """
    Lấy access_token hợp lệ, tự động refresh nếu hết hạn.
    Raise nếu chưa authorize.
    """
    token_data = _load_token()
    if not token_data:
        raise ValueError("Chưa kết nối YouTube. Vui lòng authorize trước.")

    if _is_token_expired(token_data):
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("Refresh token không tồn tại. Cần authorize lại.")
        token_data = await _refresh_access_token(refresh_token)

    return token_data["access_token"]


def is_youtube_connected() -> bool:
    """Kiểm tra đã kết nối YouTube chưa."""
    token_data = _load_token()
    return token_data is not None and "refresh_token" in token_data


# ─── OAuth2 Flow ──────────────────────────────────────────────────────────────

def get_authorization_url(state: str = "") -> str:
    """Tạo URL để redirect user đến Google OAuth2."""
    import urllib.parse

    params = {
        "client_id": settings.youtube_client_id,
        "redirect_uri": settings.youtube_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",   # Quan trọng: để nhận refresh_token
        "prompt": "consent",        # Luôn hiện consent screen để nhận refresh_token
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Đổi authorization code lấy access_token + refresh_token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.youtube_client_id,
                "client_secret": settings.youtube_client_secret,
                "code": code,
                "redirect_uri": settings.youtube_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

    token_data = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": time.time() + data.get("expires_in", 3600),
        "token_type": data.get("token_type", "Bearer"),
        "scope": data.get("scope", ""),
    }
    _save_token(token_data)
    return token_data


async def get_channel_info() -> dict:
    """Lấy thông tin channel YouTube đã kết nối."""
    access_token = await get_valid_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{YOUTUBE_API_URL}/channels",
            params={"part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()

    items = data.get("items", [])
    if not items:
        return {}

    channel = items[0]
    snippet = channel.get("snippet", {})
    stats = channel.get("statistics", {})

    return {
        "id": channel.get("id"),
        "title": snippet.get("title"),
        "description": snippet.get("description", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url"),
        "subscriber_count": stats.get("subscriberCount", "0"),
        "video_count": stats.get("videoCount", "0"),
    }


def disconnect_youtube() -> None:
    """Xóa token file để ngắt kết nối."""
    token_file = Path(settings.youtube_token_file)
    if token_file.exists():
        token_file.unlink()


# ─── Upload Video ─────────────────────────────────────────────────────────────

def _build_video_metadata(
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "public",
) -> dict:
    """
    Tạo metadata cho video YouTube Shorts.
    Tự động thêm #Shorts vào title và description.
    """
    # Đảm bảo title có #Shorts (YouTube dùng để nhận diện Shorts)
    shorts_title = title if "#Shorts" in title else f"{title} #Shorts"
    # Giới hạn title 100 ký tự
    if len(shorts_title) > 100:
        shorts_title = shorts_title[:97] + "..."

    # Description với hashtags
    hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:10]])
    full_description = f"{description}\n\n{hashtags}\n\n#Shorts #YouTubeShorts"

    return {
        "snippet": {
            "title": shorts_title,
            "description": full_description,
            "tags": tags + ["Shorts", "YouTubeShorts"],
            "categoryId": "22",  # People & Blogs (phù hợp nhất cho content Việt)
            "defaultLanguage": "vi",
            "defaultAudioLanguage": "vi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }


async def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "public",
    on_progress=None,
) -> dict:
    """
    Upload video lên YouTube dùng Resumable Upload API.

    Args:
        video_path  : đường dẫn file MP4
        title       : tiêu đề video
        description : mô tả video
        tags        : danh sách tags
        privacy     : "public" | "unlisted" | "private"
        on_progress : callback(bytes_sent, total_bytes) để track tiến trình

    Returns: dict chứa video_id và youtube_url
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video không tồn tại: {video_path}")

    access_token = await get_valid_access_token()
    metadata = _build_video_metadata(title, description, tags, privacy)
    file_size = os.path.getsize(video_path)

    # ── Bước 1: Khởi tạo resumable upload session ────────────────────
    async with httpx.AsyncClient(timeout=30.0) as client:
        init_response = await client.post(
            YOUTUBE_UPLOAD_URL,
            params={
                "uploadType": "resumable",
                "part": "snippet,status",
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(file_size),
            },
            json=metadata,
        )
        init_response.raise_for_status()

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        raise ValueError("Không nhận được upload URL từ YouTube")

    # ── Bước 2: Upload file theo chunks (5MB mỗi chunk) ──────────────
    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
    bytes_sent = 0
    video_id = None

    with open(video_path, "rb") as f:
        async with httpx.AsyncClient(timeout=300.0) as client:
            while bytes_sent < file_size:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                chunk_end = bytes_sent + len(chunk) - 1
                content_range = f"bytes {bytes_sent}-{chunk_end}/{file_size}"

                upload_response = await client.put(
                    upload_url,
                    content=chunk,
                    headers={
                        "Content-Range": content_range,
                        "Content-Type": "video/mp4",
                    },
                )

                if upload_response.status_code in (200, 201):
                    # Upload hoàn tất
                    data = upload_response.json()
                    video_id = data.get("id")
                    break
                elif upload_response.status_code == 308:
                    # Resume Incomplete — tiếp tục chunk tiếp theo
                    range_header = upload_response.headers.get("Range", "")
                    if range_header:
                        bytes_sent = int(range_header.split("-")[1]) + 1
                    else:
                        bytes_sent += len(chunk)
                else:
                    upload_response.raise_for_status()

                if on_progress:
                    on_progress(bytes_sent, file_size)

    if not video_id:
        raise ValueError("Upload thất bại: không nhận được video ID")

    youtube_url = f"https://www.youtube.com/shorts/{video_id}"
    return {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "title": metadata["snippet"]["title"],
        "privacy": privacy,
    }
