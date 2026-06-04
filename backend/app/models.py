from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateVideoRequest(BaseModel):
    topic: str
    style: Optional[str] = "engaging"  # engaging, educational, funny
    language: Optional[str] = "vi"     # vi, en
    media_source: Optional[str] = "hybrid"  # hybrid, pexels, ai_image, slide
    # Tự động upload YouTube sau khi render xong
    auto_upload_youtube: Optional[bool] = False
    youtube_privacy: Optional[str] = "public"  # public | unlisted | private


class SlideContent(BaseModel):
    layout: str  # title, compare, list, card, big_number, one_word, wrong_right, myth_fact, timeline, receipt, comment_cta, motion_tech
    title: str
    content: List[str]


class ScriptSegment(BaseModel):
    text: str
    visual_prompt: str
    duration: float
    slide: Optional[SlideContent] = None


class VideoScript(BaseModel):
    hook: str
    segments: List[ScriptSegment]
    call_to_action: str
    total_duration: float
    keywords: List[str]
    # GPT-4o tự đề xuất title và description cho YouTube
    suggested_title: Optional[str] = None
    suggested_description: Optional[str] = None


class YouTubeSEO(BaseModel):
    """Metadata SEO tối ưu cho YouTube Shorts."""
    title: str
    description: str
    tags: List[str]
    hashtags: List[str]
    ab_test_titles: Optional[List[str]] = None
    seo_explanation: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int  # 0-100
    message: str
    video_url: Optional[str] = None
    error: Optional[str] = None
    # YouTube upload result (nếu có)
    youtube_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    # SEO metadata để hiện trên UI
    seo: Optional["YouTubeSEO"] = None
