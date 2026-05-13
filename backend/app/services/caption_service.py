"""
Caption rendering service dùng Pillow.

Lý do dùng Pillow thay MoviePy TextClip:
- MoviePy TextClip dùng ImageMagick → không render được dấu tiếng Việt
- Pillow hỗ trợ Unicode đầy đủ, chỉ cần font TTF có dấu Việt
- Tạo frame PNG → dùng làm ImageClip trong MoviePy

Font được dùng: Roboto Bold (Google Fonts, miễn phí, hỗ trợ tiếng Việt hoàn hảo)
"""
import os
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip

from app.config import settings

W = settings.video_width   # 1080
H = settings.video_height  # 1920

# Đường dẫn font
FONT_DIR = Path(settings.assets_dir) / "fonts"
FONT_BOLD_PATH = FONT_DIR / "Roboto-Bold.ttf"
FONT_BLACK_PATH = FONT_DIR / "Roboto-Black.ttf"


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Load font có hỗ trợ tiếng Việt."""
    font_path = FONT_BLACK_PATH if bold else FONT_BOLD_PATH

    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)

    # Fallback: tìm font hệ thống hỗ trợ Unicode
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Linux
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",       # macOS
        "/System/Library/Fonts/Helvetica.ttc",                     # macOS fallback
        "C:/Windows/Fonts/arialbd.ttf",                            # Windows
    ]
    for fp in system_fonts:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)

    # Last resort: default font (không có dấu Việt nhưng không crash)
    return ImageFont.load_default()


def _draw_text_with_stroke(
    draw: ImageDraw.Draw,
    text: str,
    position: tuple,
    font: ImageFont.FreeTypeFont,
    text_color: tuple = (255, 255, 255),
    stroke_color: tuple = (0, 0, 0),
    stroke_width: int = 6,
) -> None:
    """Vẽ text với stroke (viền đen) để dễ đọc trên mọi nền."""
    x, y = position
    draw.text(
        (x, y), 
        text, 
        font=font, 
        fill=text_color, 
        stroke_width=stroke_width, 
        stroke_fill=stroke_color
    )


def create_caption_frame(
    text: str,
    highlight_word: Optional[str] = None,
    fontsize: int = 80,
    max_chars_per_line: int = 18,
) -> np.ndarray:
    """
    Tạo frame RGBA chứa caption text.
    Nền trong suốt, text trắng + viền đen.

    Args:
        text: Nội dung caption
        highlight_word: Từ được highlight màu vàng (word-by-word mode)
        fontsize: Cỡ chữ
        max_chars_per_line: Số ký tự tối đa mỗi dòng

    Returns: numpy array RGBA (H, W, 4)
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = _get_font(fontsize, bold=True)
    font_highlight = _get_font(int(fontsize * 1.1), bold=True)

    # Wrap text
    lines = textwrap.wrap(text, width=max_chars_per_line)
    if not lines:
        return np.array(img)

    line_height = fontsize + 16
    total_height = len(lines) * line_height

    # Vị trí bắt đầu: giữa màn hình theo chiều dọc
    start_y = (H - total_height) // 2

    for line in lines:
        # Tính chiều rộng dòng để căn giữa
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        y = start_y

        if highlight_word and highlight_word.upper() in line.upper():
            # Vẽ từ thường trước, highlight từ đặc biệt
            words_in_line = line.split()
            cursor_x = x
            for word in words_in_line:
                is_highlight = word.upper() == highlight_word.upper()
                w_font = font_highlight if is_highlight else font
                w_color = (255, 230, 0) if is_highlight else (255, 255, 255)  # vàng vs trắng

                _draw_text_with_stroke(
                    draw,
                    word + " ",
                    (cursor_x, y - (4 if is_highlight else 0)),
                    w_font,
                    text_color=w_color,
                    stroke_width=5 if is_highlight else 4,
                )
                w_bbox = draw.textbbox((0, 0), word + " ", font=w_font)
                cursor_x += w_bbox[2] - w_bbox[0]
        else:
            _draw_text_with_stroke(draw, line, (x, y), font)

        start_y += line_height

    return np.array(img)


def make_static_caption_clip(
    text: str,
    duration: float,
    start_time: float,
    fontsize: int = 78,
) -> ImageClip:
    """Caption tĩnh hiện cả đoạn text trong suốt duration."""
    frame = create_caption_frame(text, fontsize=fontsize)
    clip = (
        ImageClip(frame, ismask=False)
        .set_duration(duration)
        .set_start(start_time)
    )
    return clip


def make_word_by_word_clips(
    text: str,
    audio_duration: float,
    start_time: float,
    fontsize: int = 85,
) -> list:
    """
    Tạo 1 clip duy nhất xử lý word-by-word kiểu TikTok.
    Dùng VideoClip + cache thay vì tạo hàng trăm ImageClip.
    """
    words = text.split()
    if not words:
        return []

    # Trừ hao khoảng lặng (silence) ở cuối audio của TTS, thường chiếm 10-15%.
    # Giúp chữ nhảy nhanh hơn một chút, khớp với tiếng đọc thực tế hơn.
    reading_duration = audio_duration * 0.9 
    time_per_word = reading_duration / len(words)
    frame_cache = {}

    from moviepy.editor import VideoClip

    def get_cached_frames(t):
        idx = min(int(t / time_per_word), len(words) - 1)
        if idx not in frame_cache:
            rgba = create_caption_frame(text, highlight_word=words[idx], fontsize=fontsize)
            rgb = rgba[:, :, :3]
            mask = rgba[:, :, 3] / 255.0
            frame_cache[idx] = (rgb, mask)
        return frame_cache[idx]

    def make_rgb_frame(t):
        return get_cached_frames(t)[0]

    def make_mask_frame(t):
        return get_cached_frames(t)[1]

    clip = VideoClip(make_rgb_frame, duration=audio_duration)
    mask = VideoClip(make_mask_frame, duration=audio_duration, ismask=True)
    clip = clip.set_mask(mask).set_start(start_time)

    return [clip]
