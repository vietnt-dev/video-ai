"""
Text-to-Speech service.

Engine ưu tiên:
1. edge-tts (Microsoft Azure, MIỄN PHÍ) — giọng Việt rất tự nhiên
   - vi-VN-HoaiMyNeural  : giọng nữ miền Nam, trẻ trung
   - vi-VN-NamMinhNeural : giọng nam miền Nam, trầm ấm
2. ElevenLabs (trả phí) — chất lượng cao hơn, cần API key
"""
import asyncio
import httpx
from pathlib import Path
from app.config import settings


# ─── edge-tts (Microsoft, miễn phí) ─────────────────────────────────────────


MALE_VOICE_STYLES = {
    "co_nhan",
    "lich_su",
    "kinh_doanh",
    "lam_giau",
    "educational",
}

STYLE_PROSODY = {
    "su_that": {"rate": "+30%", "pitch": "+8Hz"},
    "engaging": {"rate": "+28%", "pitch": "+6Hz"},
    "funny": {"rate": "+26%", "pitch": "+10Hz"},
    "tu_vi": {"rate": "+20%", "pitch": "-2Hz"},
    "co_nhan": {"rate": "+20%", "pitch": "-5Hz"},
    "lich_su": {"rate": "+22%", "pitch": "-4Hz"},
    "kinh_doanh": {"rate": "+24%", "pitch": "-2Hz"},
    "lam_giau": {"rate": "+25%", "pitch": "-2Hz"},
    "educational": {"rate": "+24%", "pitch": "+0Hz"},
    "tam_ly": {"rate": "+24%", "pitch": "+2Hz"},
    "suc_khoe": {"rate": "+22%", "pitch": "+1Hz"},
    "tinh_cam": {"rate": "+21%", "pitch": "+2Hz"},
}

PART_PROSODY = {
    "hook": {"rate_delta": 8, "pitch_delta": 3},
    "body": {"rate_delta": 0, "pitch_delta": 0},
    "cta": {"rate_delta": -2, "pitch_delta": -1},
}


def _parse_percent(value: str, default: int = 0) -> int:
    try:
        return int(value.replace("%", "").replace("+", ""))
    except ValueError:
        return default


def _parse_hz(value: str, default: int = 0) -> int:
    try:
        return int(value.replace("Hz", "").replace("+", ""))
    except ValueError:
        return default


def _format_percent(value: int) -> str:
    value = max(-50, min(50, value))
    return f"{value:+d}%"


def _format_hz(value: int) -> str:
    value = max(-20, min(20, value))
    # edge-tts CLI không chấp nhận "+0Hz", dùng "0Hz" khi value = 0
    if value == 0:
        return "0Hz"
    return f"{value:+d}Hz"


def select_edge_voice(language: str = "vi", style: str | None = None) -> str:
    """Chọn voice theo ngôn ngữ và phong cách nội dung."""
    use_male_voice = style in MALE_VOICE_STYLES

    if language == "vi":
        return (
            settings.edge_tts_voice_vi_male
            if use_male_voice
            else settings.edge_tts_voice_vi
        )

    return (
        settings.edge_tts_voice_en_male
        if use_male_voice
        else settings.edge_tts_voice_en
    )


def select_edge_prosody(style: str | None = None, part: str = "body") -> tuple[str, str]:
    prosody = STYLE_PROSODY.get(style or "", {})
    base_rate = prosody.get("rate", settings.edge_tts_rate)
    base_pitch = prosody.get("pitch", settings.edge_tts_pitch)
    part_prosody = PART_PROSODY.get(part, PART_PROSODY["body"])

    rate = _parse_percent(base_rate) + part_prosody["rate_delta"]
    pitch = _parse_hz(base_pitch) + part_prosody["pitch_delta"]
    return _format_percent(rate), _format_hz(pitch)


async def tts_edge(
    text: str,
    output_path: str,
    language: str = "vi",
    style: str | None = None,
    part: str = "body",
) -> str:
    """
    Dùng edge-tts Python API để tạo giọng đọc tiếng Việt tự nhiên.
    Không cần API key, hoàn toàn miễn phí.
    """
    import edge_tts

    voice = select_edge_voice(language, style)
    rate, pitch = select_edge_prosody(style, part)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

    return output_path


# ─── ElevenLabs (trả phí, chất lượng cao hơn) ────────────────────────────────

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


async def tts_elevenlabs(text: str, output_path: str, voice_id: str = None) -> str:
    """Dùng ElevenLabs API để tạo giọng đọc."""
    voice_id = voice_id or settings.elevenlabs_voice_id

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.elevenlabs_api_key,
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)

    return output_path


# ─── Public API ───────────────────────────────────────────────────────────────

async def text_to_speech(
    text: str,
    output_path: str,
    language: str = "vi",
    voice_id: str = None,
    style: str | None = None,
    part: str = "body",
) -> str:
    """
    Chuyển text thành audio. Tự động chọn engine theo config.

    Nếu engine là 'elevenlabs' nhưng không có API key → fallback sang edge-tts.
    """
    engine = settings.tts_engine

    # Fallback nếu ElevenLabs chưa config
    if engine == "elevenlabs" and not settings.elevenlabs_api_key:
        print("⚠️  ElevenLabs API key chưa set, dùng edge-tts thay thế")
        engine = "edge-tts"

    if engine == "elevenlabs":
        return await tts_elevenlabs(text, output_path, voice_id)
    else:
        return await tts_edge(text, output_path, language, style, part)


async def generate_full_narration(
    script_parts: list[str],
    job_id: str,
    language: str = "vi",
    style: str | None = None,
    part_types: list[str] | None = None,
) -> list[str]:
    """
    Tạo audio cho từng đoạn script song song để tăng tốc.
    Returns: danh sách đường dẫn file audio (MP3/WAV)
    """
    audio_dir = f"{settings.assets_dir}/audio/{job_id}"
    Path(audio_dir).mkdir(parents=True, exist_ok=True)

    # Tạo audio tuần tự để tránh bị Microsoft block (gây lỗi NoAudioReceived)
    output_paths = []
    for i, text in enumerate(script_parts):
        part = part_types[i] if part_types and i < len(part_types) else "body"
        output_path = f"{audio_dir}/segment_{i:02d}.mp3"
        output_paths.append(output_path)
        # Thêm retry logic đơn giản
        try:
            await text_to_speech(text, output_path, language, style=style, part=part)
        except Exception as e:
            print(f"Lỗi TTS lần 1, thử lại: {e}")
            await asyncio.sleep(2)
            await text_to_speech(text, output_path, language, style=style, part=part)
            
    return output_paths
