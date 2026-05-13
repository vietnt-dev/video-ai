from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # OpenAI (optional nếu dùng Gemini)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Google Gemini (FREE tier: 1500 req/ngày)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"        # script + SEO
    gemini_image_model: str = "imagen-4.0-generate-001"  # tạo ảnh miễn phí (chuẩn 2026)

    # AI Provider: "openai" hoặc "gemini" (KHUYẾN NGHỊ: gemini vì free)
    ai_provider: str = "gemini"

    # ElevenLabs (optional - edge-tts miễn phí)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    pexels_api_key: str = ""

    # Replicate (Stable Diffusion, optional)
    replicate_api_token: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Paths
    output_dir: str = "./outputs"
    assets_dir: str = "./assets"

    # Video settings
    max_video_duration: int = 60
    video_width: int = 1080
    video_height: int = 1920

    # TTS Engine
    tts_engine: str = "edge-tts"
    edge_tts_voice_vi: str = "vi-VN-HoaiMyNeural"
    edge_tts_voice_vi_male: str = "vi-VN-NamMinhNeural"
    edge_tts_voice_en: str = "en-US-AriaNeural"
    edge_tts_voice_en_male: str = "en-US-GuyNeural"
    edge_tts_rate: str = "+25%"
    edge_tts_pitch: str = "0Hz"

    # YouTube OAuth2
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = "http://localhost:8000/api/youtube/oauth/callback"
    youtube_token_file: str = "./assets/youtube_token.json"

    # Media source
    # "pexels"      → stock video miễn phí
    # "ai_image"    → AI image + Ken Burns, bám nội dung hơn cho Shorts kiến thức
    # "hybrid"      → Pexels trước, fallback AI image
    media_source: str = "hybrid"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure directories exist
for sub in ["audio", "video", "images", "music", "fonts"]:
    Path(f"{settings.assets_dir}/{sub}").mkdir(parents=True, exist_ok=True)
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
