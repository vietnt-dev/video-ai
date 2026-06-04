"""
Slide Generation Service.

Sử dụng Pillow để vẽ các slide dạng Infographic/Trình bày đẹp mắt ở tỷ lệ 9:16.
Sau đó dùng FFmpeg để convert ảnh slide tĩnh thành video mp4 cực nhanh.
"""
import os
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Optional, List
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip

from app.config import settings
from app.models import SlideContent

W = settings.video_width   # 1080
H = settings.video_height  # 1920

# Đường dẫn font
FONT_DIR = Path(settings.assets_dir) / "fonts"
FONT_BOLD_PATH = FONT_DIR / "Roboto-Bold.ttf"
FONT_BLACK_PATH = FONT_DIR / "Roboto-Black.ttf"

WHITE = (255, 255, 255, 255)
MUTED = (226, 232, 240, 255)
DIM = (148, 163, 184, 255)
YELLOW = (250, 204, 21, 255)
RED = (248, 113, 113, 255)
CYAN = (34, 211, 238, 255)
GREEN = (52, 211, 153, 255)
PURPLE = (192, 132, 252, 255)
BLACK = (2, 6, 23, 255)

NEGATIVE_KEYWORDS = {
    "sai", "mất", "phí", "đừng", "không", "lỗi", "nguy", "cũ", "fail",
}
TECH_KEYWORDS = {
    "ai", "prompt", "google", "gemini", "chatgpt", "data", "dữ", "liệu",
}
CTA_KEYWORDS = {
    "comment", "bình", "luận", "share", "gửi", "lưu", "save", "phần",
}


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Load font Roboto hoặc font fallback hệ thống."""
    font_path = FONT_BLACK_PATH if bold else FONT_BOLD_PATH

    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)

    # Fallback fonts
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for fp in system_fonts:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)

    return ImageFont.load_default()


def _draw_soft_glow(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Vẽ các hình tròn đồng tâm có độ mờ giảm dần để tạo hiệu ứng phát sáng mịn."""
    steps = 40
    for i in range(steps):
        curr_r = r * (steps - i) / steps
        alpha = int(7 * (i / steps))  # Rất mờ để làm nền sang trọng
        if alpha > 0:
            draw.ellipse(
                [cx - curr_r, cy - curr_r, cx + curr_r, cy + curr_r],
                fill=color + (alpha,)
            )


def _draw_neon_background(img: Image.Image):
    """Tạo nền tối có chiều sâu, ít giống presentation template."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    
    color_top = (4, 8, 18)
    color_bottom = (0, 0, 0)
    for y in range(h):
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * y / h)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * y / h)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
        
    _draw_soft_glow(draw, w // 2 - 160, 470, 360, (34, 211, 238))
    _draw_soft_glow(draw, w // 2 + 190, 1120, 420, (250, 204, 21))

    # Subtle creator-style texture/grid, enough to avoid flat PowerPoint frames.
    for x in range(0, w, 54):
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 9), width=1)
    for y in range(0, h, 54):
        draw.line([(0, y), (w, y)], fill=(255, 255, 255, 7), width=1)
    draw.rectangle([0, 0, w, h], outline=(255, 255, 255, 28), width=18)


def _draw_glowing_card(
    draw: ImageDraw.ImageDraw,
    xy: list,
    radius: int,
    fill_color: tuple,
    glow_color: tuple,
    border_width: int = 3
):
    """Vẽ card bán trong suốt với viền kép hoặc viền neon phát sáng (glassmorphism)."""
    # Glow viền ngoài
    for w in range(border_width + 5, border_width, -1):
        alpha = int(35 / (w - border_width))
        draw.rounded_rectangle(
            xy,
            radius=radius,
            fill=None,
            outline=glow_color + (alpha,),
            width=w
        )
    # Card chính
    draw.rounded_rectangle(
        xy,
        radius=radius,
        fill=fill_color,
        outline=glow_color + (240,),
        width=border_width
    )


def _draw_checkmark(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple):
    """Vẽ dấu checkmark ✓ sắc nét trong ô vuông check-box."""
    draw.line([(x + 8, y + 17), (x + 14, y + 23)], fill=color, width=3)
    draw.line([(x + 14, y + 23), (x + 24, y + 10)], fill=color, width=3)


def _wrap_text_by_width(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Tự động xuống dòng dựa trên kích thước pixel thực tế."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _semantic_color(word: str, default: tuple = WHITE) -> tuple:
    token = re.sub(r"[^\w%]+", "", word.lower())
    if re.search(r"\d", token) or token in {"triệu", "tỷ", "usd", "vnd", "%"}:
        return YELLOW
    if token in NEGATIVE_KEYWORDS:
        return RED
    if token in TECH_KEYWORDS:
        return CYAN
    if token in CTA_KEYWORDS:
        return GREEN
    if token in {"cú", "lật", "payoff"}:
        return PURPLE
    return default


def _fit_font_size(text: str, max_width: int, start_size: int, min_size: int, draw: ImageDraw.ImageDraw) -> int:
    size = start_size
    while size > min_size:
        font = _get_font(size, bold=True)
        lines = _wrap_text_by_width(text, font, max_width, draw)
        if lines and max(draw.textbbox((0, 0), line, font=font)[2] for line in lines) <= max_width:
            return size
        size -= 4
    return min_size


def _draw_centered_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    default_color: tuple = WHITE,
    stroke_width: int = 3,
) -> int:
    words = text.split()
    if not words:
        return y

    widths = []
    total_width = 0
    for word in words:
        token = word + " "
        bbox = draw.textbbox((0, 0), token, font=font)
        width = bbox[2] - bbox[0]
        widths.append(width)
        total_width += width

    x = (W - total_width) // 2
    for word, width in zip(words, widths):
        color = _semantic_color(word, default_color)
        draw.text(
            (x, y),
            word + " ",
            font=font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 180),
        )
        x += width

    return y + int(font.size * 1.18)


def _draw_left_rich_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    default_color: tuple = WHITE,
    stroke_width: int = 2,
) -> int:
    cursor_x = x
    for word in text.split():
        token = word + " "
        color = _semantic_color(word, default_color)
        draw.text(
            (cursor_x, y),
            token,
            font=font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 155),
        )
        bbox = draw.textbbox((0, 0), token, font=font)
        cursor_x += bbox[2] - bbox[0]
    return cursor_x


def _draw_centered_multiline(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_y: int,
    max_width: int,
    font_size: int,
    min_size: int = 38,
    default_color: tuple = WHITE,
) -> None:
    size = _fit_font_size(text, max_width, font_size, min_size, draw)
    font = _get_font(size, bold=True)
    lines = _wrap_text_by_width(text, font, max_width, draw)[:4]
    line_height = int(size * 1.2)
    y = center_y - (len(lines) * line_height) // 2
    for line in lines:
        _draw_centered_line(draw, line, y, font, default_color=default_color, stroke_width=4)
        y += line_height


def _draw_top_badge(draw: ImageDraw.ImageDraw, text: str) -> None:
    font_header = _get_font(22, bold=True)
    header_text = text.upper() if text else "SHORTS"
    if len(header_text) > 28:
        header_text = header_text[:25] + "..."

    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    width = bbox[2] - bbox[0]
    pill_xy = [68, 74, 68 + width + 34, 118]
    draw.rounded_rectangle(pill_xy, radius=12, fill=(15, 23, 42, 155), outline=(255, 255, 255, 55), width=1)
    draw.text((85, 88), header_text, font=font_header, fill=(203, 213, 225, 230))


def _draw_micro_label(draw: ImageDraw.ImageDraw, text: str, color: tuple = YELLOW) -> None:
    font = _get_font(30, bold=True)
    safe = text.upper()[:18]
    draw.text((72, 240), safe, font=font, fill=color)
    draw.rectangle([72, 286, 230, 294], fill=color)


def _draw_full_bleed_keyword(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_y: int = 705,
    color: tuple = WHITE,
    max_width: int = W - 110,
    font_size: int = 154,
) -> None:
    _draw_centered_multiline(
        draw,
        text.upper(),
        center_y=center_y,
        max_width=max_width,
        font_size=font_size,
        min_size=76,
        default_color=color,
    )


def _progress(t: float, start: float, duration: float) -> float:
    if t <= start:
        return 0.0
    if duration <= 0:
        return 1.0
    return max(0.0, min(1.0, (t - start) / duration))


def _ease_out_cubic(x: float) -> float:
    return 1 - (1 - x) ** 3


def _pop_scale(x: float) -> float:
    if x <= 0:
        return 0.0
    eased = _ease_out_cubic(x)
    overshoot = 0.08 * max(0.0, 1.0 - abs(x - 0.68) / 0.32)
    return min(1.1, eased + overshoot)


def _draw_pop_multiline(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_y: int,
    t: float,
    start: float,
    color: tuple,
    font_size: int,
    max_width: int = W - 130,
    min_size: int = 46,
) -> None:
    p = _progress(t, start, 0.34)
    if p <= 0:
        return
    scale = _pop_scale(p)
    live_size = max(min_size, int(font_size * (0.74 + 0.26 * scale)))
    live_y = int(center_y + (1 - scale) * 48)
    _draw_centered_multiline(
        draw,
        text.upper(),
        center_y=live_y,
        max_width=max_width,
        font_size=live_size,
        min_size=min_size,
        default_color=color,
    )


def _draw_motion_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    t: float,
    start: float,
    color: tuple,
) -> None:
    p = _progress(t, start, 0.25)
    if p <= 0:
        return
    x = int(72 - (1 - _ease_out_cubic(p)) * 170)
    font = _get_font(30, bold=True)
    safe = text.upper()[:18]
    draw.text((x, 240), safe, font=font, fill=color)
    draw.rectangle([x, 286, x + 158, 294], fill=color)


def _draw_motion_card(
    draw: ImageDraw.ImageDraw,
    xy: list[int],
    t: float,
    start: float,
    fill: tuple,
    outline: tuple,
    radius: int = 18,
    width: int = 4,
) -> bool:
    p = _progress(t, start, 0.28)
    if p <= 0:
        return False
    eased = _ease_out_cubic(p)
    cx = (xy[0] + xy[2]) // 2
    cy = (xy[1] + xy[3]) // 2
    half_w = int((xy[2] - xy[0]) * (0.75 + 0.25 * eased) / 2)
    half_h = int((xy[3] - xy[1]) * (0.75 + 0.25 * eased) / 2)
    live_xy = [cx - half_w, cy - half_h, cx + half_w, cy + half_h]
    draw.rounded_rectangle(live_xy, radius=radius, fill=fill, outline=outline, width=width)
    return p >= 0.35


def _draw_motion_background(base: Image.Image, t: float) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    offset = int((t * 36) % 54)
    for x in range(-54 + offset, W, 54):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 5), width=1)
    if t < 0.12:
        alpha = int(46 * (1 - t / 0.12))
        overlay = Image.new("RGBA", (W, H), (255, 255, 255, alpha))
        img.alpha_composite(overlay)
    return img


def _draw_transition_overlay(img: Image.Image, t: float, duration: float) -> None:
    """Fast editorial wipes so segments feel cut, not paged."""
    draw = ImageDraw.Draw(img)
    intro = _progress(t, 0.0, 0.22)
    if 0 < intro < 1:
        x = int(W * _ease_out_cubic(intro))
        draw.rectangle([x, 0, W, H], fill=(0, 0, 0, int(220 * (1 - intro))))
        draw.rectangle([max(0, x - 18), 0, x, H], fill=(34, 211, 238, int(150 * (1 - intro))))

    outro = _progress(t, max(0.0, duration - 0.28), 0.28)
    if outro > 0:
        x = int(W * _ease_out_cubic(outro))
        draw.rectangle([0, 0, x, H], fill=(255, 255, 255, int(34 * outro)))
        draw.rectangle([max(0, x - 28), 0, x, H], fill=(250, 204, 21, int(185 * outro)))


def _draw_kinetic_words(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_y: int,
    t: float,
    start: float,
    color: tuple,
    font_size: int,
    max_width: int = W - 120,
    min_size: int = 48,
    word_gap: float = 0.11,
) -> None:
    """Reveal words individually with pop timing, closer to polished tech shorts."""
    if not text:
        return
    base_font = _get_font(font_size, bold=True)
    lines = _wrap_text_by_width(text.upper(), base_font, max_width, draw)[:3]
    line_height = int(font_size * 1.05)
    y0 = center_y - (len(lines) * line_height) // 2
    word_index = 0

    for line_idx, line in enumerate(lines):
        words = line.split()
        total_width = 0
        word_parts = []
        for word in words:
            p = _progress(t, start + word_index * word_gap, 0.28)
            live_size = max(min_size, int(font_size * (0.78 + 0.22 * _pop_scale(p))))
            font = _get_font(live_size, bold=True)
            token = word + " "
            bbox = draw.textbbox((0, 0), token, font=font)
            width = bbox[2] - bbox[0]
            total_width += width
            word_parts.append((word, token, font, width, p))
            word_index += 1

        x = (W - total_width) // 2
        y = y0 + line_idx * line_height
        for word, token, font, width, p in word_parts:
            if p <= 0:
                x += width
                continue
            eased = _ease_out_cubic(p)
            live_y = int(y + (1 - eased) * 32)
            fill = _semantic_color(word, color)
            draw.text(
                (x, live_y),
                token,
                font=font,
                fill=fill,
                stroke_width=5,
                stroke_fill=(0, 0, 0, int(190 * eased)),
            )
            x += width


def _draw_browser_mock(draw: ImageDraw.ImageDraw, t: float, start: float, lines: list[str]) -> None:
    if not _draw_motion_card(draw, [82, 350, W - 82, 1085], t, start, (15, 23, 42, 230), (34, 211, 238, 235), radius=18, width=4):
        return
    chrome_y = 395
    draw.rounded_rectangle([125, chrome_y, W - 125, chrome_y + 72], radius=18, fill=(2, 6, 23, 245), outline=(148, 163, 184, 95), width=2)
    for idx, color in enumerate([RED, YELLOW, GREEN]):
        draw.ellipse([150 + idx * 34, chrome_y + 25, 166 + idx * 34, chrome_y + 41], fill=color)
    draw.text((255, chrome_y + 19), "AI SHORTS / PROOF", font=_get_font(24, bold=True), fill=DIM)

    y = 540
    for idx, line in enumerate(lines[:4]):
        if t < start + 0.42 + idx * 0.28:
            continue
        label_color = [CYAN, YELLOW, GREEN, PURPLE][idx % 4]
        draw.rounded_rectangle([145, y, W - 145, y + 86], radius=14, fill=(255, 255, 255, 18), outline=(255, 255, 255, 42), width=1)
        draw.rectangle([168, y + 24, 178, y + 62], fill=label_color)
        _draw_left_rich_line(draw, line[:36], 205, y + 19, _get_font(42, bold=True), default_color=WHITE, stroke_width=2)
        y += 112


def _draw_terminal_mock(draw: ImageDraw.ImageDraw, t: float, start: float, lines: list[str]) -> None:
    if not _draw_motion_card(draw, [92, 370, W - 92, 1035], t, start, (1, 8, 18, 238), (52, 211, 153, 235), radius=18, width=4):
        return
    draw.text((142, 420), "terminal", font=_get_font(28, bold=True), fill=GREEN)
    y = 515
    for idx, line in enumerate(lines[:4]):
        if t < start + 0.45 + idx * 0.26:
            continue
        prefix = "$ " if idx == 0 else ">"
        draw.text((145, y), prefix, font=_get_font(42, bold=True), fill=GREEN)
        _draw_left_rich_line(draw, line[:34], 195, y, _get_font(42, bold=True), default_color=WHITE, stroke_width=2)
        y += 96


def _split_motion_tech_content(content: list[str], title: str, topic: str) -> dict[str, str]:
    headline = content[0] if len(content) > 0 else title
    accent = content[1] if len(content) > 1 else "Đáng thử"
    badges = content[2] if len(content) > 2 else "Nhanh · Riêng tư · Dễ dùng"
    command = content[3] if len(content) > 3 else "$ pnpm run web"
    insight = content[4] if len(content) > 4 else topic[:42]
    cta = content[5] if len(content) > 5 else "Lưu video lại"
    return {
        "headline": headline,
        "accent": accent,
        "badges": badges,
        "command": command,
        "insight": insight,
        "cta": cta,
    }


def _draw_motion_tech_badge(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: tuple, t: float, start: float) -> int:
    p = _progress(t, start, 0.22)
    if p <= 0:
        return 0
    font = _get_font(28, bold=True)
    safe = text.strip()[:26]
    bbox = draw.textbbox((0, 0), safe, font=font)
    width = bbox[2] - bbox[0] + 34
    x, y = xy
    live_y = int(y + (1 - _ease_out_cubic(p)) * 22)
    draw.rounded_rectangle([x, live_y, x + width, live_y + 52], radius=18, fill=(15, 34, 39, 220), outline=color[:3] + (145,), width=2)
    draw.text((x + 17, live_y + 12), safe, font=font, fill=color)
    return width + 12


def _draw_motion_tech_command(draw: ImageDraw.ImageDraw, command: str, t: float, start: float, y: int = 1180) -> None:
    if not _draw_motion_card(draw, [105, y, W - 105, y + 86], t, start, (1, 8, 18, 245), (245, 158, 11, 155), radius=12, width=2):
        return
    font = _get_font(38, bold=True)
    visible = command[: max(1, int(len(command) * _progress(t, start + 0.26, 0.78)))]
    draw.text((142, y + 24), visible, font=font, fill=(251, 146, 60, 255))
    if int(t * 4) % 2 == 0:
        bbox = draw.textbbox((0, 0), visible, font=font)
        cx = 142 + bbox[2] - bbox[0] + 6
        draw.rectangle([cx, y + 23, cx + 9, y + 61], fill=(251, 146, 60, 255))


def _draw_motion_tech_frame(draw: ImageDraw.ImageDraw, data: dict[str, str], topic: str, t: float, duration: float) -> None:
    # Generic brand and section badge.
    brand_font = _get_font(34, bold=True)
    draw.text((W - 285, 86), "AI Short", font=brand_font, fill=(251, 146, 60, 245))
    _draw_motion_tech_badge(draw, (84, 238), "TECH SHORT", (251, 146, 60, 255), t, 0.06)

    # Main headline stack.
    _draw_kinetic_words(draw, data["headline"], 475, t, 0.2, WHITE, 126, max_width=W - 180, min_size=72, word_gap=0.07)
    _draw_kinetic_words(draw, data["accent"], 690, t, 0.72, (251, 146, 60, 255), 104, max_width=W - 180, min_size=64, word_gap=0.07)

    # Badges row, split by dots.
    x = 92
    for idx, badge in enumerate(re.split(r"\s*[·|]\s*", data["badges"])[:3]):
        color = [YELLOW, CYAN, (251, 146, 60, 255)][idx % 3]
        x += _draw_motion_tech_badge(draw, (x, 805), badge, color, t, 1.08 + idx * 0.12)

    # Proof strip.
    p = _progress(t, 1.42, 0.28)
    if p > 0:
        y = int(895 + (1 - _ease_out_cubic(p)) * 24)
        draw.rounded_rectangle([92, y, W - 92, y + 60], radius=12, fill=(62, 33, 10, 210), outline=(251, 146, 60, 170), width=2)
        _draw_left_rich_line(draw, "🔥 " + data["insight"][:42], 122, y + 13, _get_font(30, bold=True), default_color=(251, 146, 60, 255), stroke_width=1)

    _draw_motion_tech_command(draw, data["command"], t, 1.72, y=1090)

    # Save CTA button.
    if _draw_motion_card(draw, [300, 1305, 780, 1380], t, 2.38, (20, 16, 42, 238), (167, 139, 250, 230), radius=16, width=3):
        draw.text((345, 1324), "▮ " + data["cta"][:22], font=_get_font(36, bold=True), fill=(196, 181, 253, 255))


def render_motion_slide_video(
    slide: SlideContent,
    duration: float,
    output_path: str,
    topic: str = "",
) -> str:
    """
    Render một slide thành motion graphic clip frame-by-frame.
    Khác với zoompan, nội dung xuất hiện theo beat để giảm cảm giác PowerPoint.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fps = 30

    base = Image.new("RGBA", (W, H))
    _draw_neon_background(base)

    layout = (slide.layout or "card").lower()
    title = (slide.title or "SHORTS").upper()
    content = [line for line in (slide.content or []) if line]

    def make_frame(t: float) -> np.ndarray:
        img = _draw_motion_background(base, t)
        draw = ImageDraw.Draw(img)
        _draw_top_badge(draw, topic or "SHORTS")

        if layout == "motion_tech":
            data = _split_motion_tech_content(content, title, topic)
            _draw_motion_tech_frame(draw, data, topic, t, duration)

        elif layout in {"big_number", "number"}:
            _draw_motion_label(draw, title, t, 0.05, YELLOW)
            _draw_kinetic_words(draw, content[0] if content else title, 700, t, 0.18, YELLOW, 174, word_gap=0.08)
            if len(content) > 1:
                _draw_kinetic_words(draw, content[1], 1035, t, 0.92, WHITE, 62, max_width=W - 210, word_gap=0.08)

        elif layout in {"one_word", "keyword", "title"}:
            main_text = content[0] if content else title
            accent = _semantic_color(main_text.split()[0], CYAN)
            _draw_soft_glow(draw, W // 2, 690, 365, accent[:3])
            _draw_motion_label(draw, title, t, 0.04, accent)
            _draw_kinetic_words(draw, main_text, 690, t, 0.14, accent, 168, word_gap=0.07)
            if len(content) > 1:
                _draw_kinetic_words(draw, content[1], 980, t, 1.02, WHITE, 52, max_width=W - 260, word_gap=0.08)

        elif layout in {"wrong_right", "wrongright", "myth_fact", "compare"}:
            is_myth_fact = layout == "myth_fact"
            _draw_motion_label(draw, title, t, 0.04, YELLOW)
            left_text = content[0] if len(content) > 0 else "Cách cũ"
            right_text = content[1] if len(content) > 1 else "Cách mới"
            if _draw_motion_card(draw, [74, 350, W - 74, 650], t, 0.22, (127, 29, 29, 214), (248, 113, 113, 240), width=5):
                draw.text((122, 392), "TƯỞNG" if is_myth_fact else "SAI", font=_get_font(44, bold=True), fill=(254, 202, 202, 255))
                _draw_kinetic_words(draw, left_text, 535, t, 0.46, WHITE, 66, max_width=W - 220, min_size=44, word_gap=0.08)
            if _draw_motion_card(draw, [74, 780, W - 74, 1120], t, 1.12, (6, 78, 59, 224), (52, 211, 153, 255), width=5):
                draw.text((122, 830), "THẬT RA" if is_myth_fact else "ĐÚNG", font=_get_font(44, bold=True), fill=(187, 247, 208, 255))
                _draw_kinetic_words(draw, right_text, 970, t, 1.36, WHITE, 72, max_width=W - 220, min_size=46, word_gap=0.08)

        elif layout in {"timeline", "list"}:
            _draw_motion_label(draw, title, t, 0.04, CYAN)
            items = content[:3]
            y_positions = [420, 650, 880]
            colors = [RED, YELLOW, GREEN]
            for idx, item in enumerate(items):
                start = 0.26 + idx * 0.52
                p = _progress(t, start, 0.25)
                if p <= 0:
                    continue
                y = y_positions[idx]
                x_offset = int((1 - _ease_out_cubic(p)) * -120)
                draw.ellipse([110 + x_offset, y, 172 + x_offset, y + 62], fill=(15, 23, 42, 235), outline=colors[idx], width=4)
                draw.text((132 + x_offset, y + 12), str(idx + 1), font=_get_font(34, bold=True), fill=colors[idx])
                _draw_left_rich_line(draw, item, 210 + x_offset, y + 8, _get_font(58, bold=True), default_color=WHITE, stroke_width=3)
                if idx > 0:
                    draw.line([(141, y_positions[idx - 1] + 76), (141, y - 12)], fill=(148, 163, 184, 120), width=4)

        elif layout == "receipt":
            _draw_motion_label(draw, title, t, 0.04, YELLOW)
            if any(token in " ".join(content).lower() for token in TECH_KEYWORDS):
                _draw_terminal_mock(draw, t, 0.16, content)
            else:
                _draw_browser_mock(draw, t, 0.16, content)

        elif layout in {"comment_cta", "cta"}:
            _draw_motion_label(draw, title, t, 0.04, CYAN)
            if _draw_motion_card(draw, [80, 345, W - 80, 1075], t, 0.18, (10, 30, 40, 205), (34, 211, 238), radius=24, width=4):
                _draw_kinetic_words(draw, content[0] if content else "BÌNH LUẬN", 720, t, 0.55, YELLOW, 86, max_width=W - 190, word_gap=0.08)
                if len(content) > 1:
                    _draw_kinetic_words(draw, content[1], 945, t, 1.25, WHITE, 46, max_width=W - 250, word_gap=0.08)

        else:
            _draw_motion_label(draw, title, t, 0.04, PURPLE)
            main_text = content[0] if content else title
            if len(content) > 1:
                _draw_browser_mock(draw, t, 0.18, content)
            else:
                _draw_kinetic_words(draw, main_text, 700, t, 0.2, WHITE, 86, max_width=W - 220, word_gap=0.09)

        _draw_transition_overlay(img, t, duration)
        return np.array(img.convert("RGB"))

    clip = VideoClip(make_frame, duration=duration).set_fps(fps)
    try:
        clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            bitrate="2600k",
            preset="ultrafast",
            threads=max(1, int(settings.ffmpeg_threads or 2)),
            audio=False,
            logger=None,
        )
    finally:
        clip.close()

    return output_path


def draw_slide_image(slide: SlideContent, output_path: str, topic: str = "") -> str:
    """
    Vẽ ảnh slide 1080x1920 theo cấu trúc SlideContent và lưu vào output_path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (W, H))
    
    # 1. Vẽ nền gradient kết hợp neon glow
    _draw_neon_background(img)
    
    draw = ImageDraw.Draw(img)
    
    # 2. Vẽ badge nhỏ phía trên. Punchline chính luôn phải nổi hơn topic.
    _draw_top_badge(draw, topic or "SHORTS")
    
    # Load fonts
    font_title = _get_font(48, bold=True)
    font_body = _get_font(42, bold=True)
    font_body_bold = _get_font(44, bold=True)

    layout = slide.layout.lower()

    # ─── LAYOUT: BIG NUMBER / BIG FACT ───
    if layout == "motion_tech":
        data = _split_motion_tech_content(slide.content or [], slide.title or "TECH SHORT", topic)
        _draw_motion_tech_frame(draw, data, topic, t=99.0, duration=4.0)

    # ─── LAYOUT: BIG NUMBER / BIG FACT ───
    elif layout in {"big_number", "number"}:
        title_text = slide.title.upper() if slide.title else "CON SỐ"
        main_text = slide.content[0] if slide.content else ""
        sub_text = slide.content[1] if len(slide.content) > 1 else ""

        _draw_micro_label(draw, title_text, YELLOW)
        _draw_full_bleed_keyword(draw, main_text, center_y=700, color=YELLOW, font_size=172)
        if sub_text:
            _draw_centered_multiline(draw, sub_text, center_y=1030, max_width=W - 200, font_size=62, min_size=44, default_color=WHITE)

    # ─── LAYOUT: ONE WORD / KEYWORD PUNCH ───
    elif layout in {"one_word", "keyword"}:
        title_text = slide.title.upper() if slide.title else "CÚ LẬT"
        main_text = slide.content[0] if slide.content else title_text
        accent = _semantic_color(main_text.split()[0], CYAN)
        _draw_soft_glow(draw, W // 2, 690, 360, accent[:3])
        _draw_micro_label(draw, title_text, accent)
        _draw_full_bleed_keyword(draw, main_text, center_y=690, color=accent, font_size=166)
        if len(slide.content) > 1:
            _draw_centered_multiline(draw, slide.content[1], center_y=970, max_width=W - 260, font_size=50, min_size=38, default_color=WHITE)

    # ─── LAYOUT: WRONG / RIGHT ───
    elif layout in {"wrong_right", "wrongright", "myth_fact"}:
        is_myth_fact = layout == "myth_fact"
        title_text = slide.title.upper() if slide.title else ("TƯỞNG VẬY?" if is_myth_fact else "SAI Ở ĐÂU?")
        left_text = slide.content[0] if len(slide.content) > 0 else "Cách cũ"
        right_text = slide.content[1] if len(slide.content) > 1 else "Cách mới"

        _draw_micro_label(draw, title_text, YELLOW)
        left_card = [74, 350, W - 74, 650]
        right_card = [74, 780, W - 74, 1120]
        draw.rounded_rectangle(left_card, radius=18, fill=(127, 29, 29, 214), outline=(248, 113, 113, 240), width=5)
        draw.rounded_rectangle(right_card, radius=18, fill=(6, 78, 59, 224), outline=(52, 211, 153, 255), width=5)
        draw.text((122, 392), "TƯỞNG" if is_myth_fact else "SAI", font=_get_font(44, bold=True), fill=(254, 202, 202, 255))
        draw.text((122, 830), "THẬT RA" if is_myth_fact else "ĐÚNG", font=_get_font(44, bold=True), fill=(187, 247, 208, 255))
        _draw_centered_multiline(draw, left_text, center_y=535, max_width=W - 220, font_size=68, min_size=46, default_color=WHITE)
        _draw_centered_multiline(draw, right_text, center_y=970, max_width=W - 220, font_size=74, min_size=48, default_color=WHITE)

    # ─── LAYOUT: TIMELINE / 3 STEP REVEAL ───
    elif layout == "timeline":
        title_text = slide.title.upper() if slide.title else "3 MỐC"
        _draw_micro_label(draw, title_text, CYAN)
        y_positions = [405, 650, 895]
        colors = [RED, YELLOW, GREEN]
        for idx, item in enumerate(slide.content[:3]):
            y = y_positions[idx]
            draw.ellipse([110, y, 172, y + 62], fill=(15, 23, 42, 235), outline=colors[idx], width=4)
            draw.text((132, y + 12), str(idx + 1), font=_get_font(34, bold=True), fill=colors[idx])
            if idx < 2:
                draw.line([(141, y + 72), (141, y_positions[idx + 1] - 12)], fill=(148, 163, 184, 150), width=4)
            _draw_left_rich_line(draw, item, 210, y + 8, _get_font(58, bold=True), default_color=WHITE, stroke_width=3)

    # ─── LAYOUT: RECEIPT / CHAT / NOTE ───
    elif layout == "receipt":
        title_text = slide.title.upper() if slide.title else "BẰNG CHỨNG"
        _draw_micro_label(draw, title_text, YELLOW)
        card_xy = [115, 335, W - 115, 1085]
        draw.rounded_rectangle(card_xy, radius=18, fill=(245, 245, 240, 242), outline=(250, 204, 21, 230), width=4)
        draw.line([(165, 455), (W - 165, 455)], fill=(30, 41, 59, 90), width=3)
        receipt_font = _get_font(48, bold=True)
        small_font = _get_font(32, bold=True)
        draw.text((165, 385), "NOTE", font=small_font, fill=(15, 23, 42, 230))
        y = 515
        for item in slide.content[:4]:
            safe_item = item[:42]
            color = (15, 23, 42, 255)
            draw.text((165, y), safe_item, font=receipt_font, fill=color)
            y += 112

    # ─── LAYOUT: COMMENT CTA ───
    elif layout in {"comment_cta", "cta"}:
        title_text = slide.title.upper() if slide.title else "BÌNH LUẬN"
        main_text = slide.content[0] if slide.content else "MUỐN PHẦN 2?"
        sub_text = slide.content[1] if len(slide.content) > 1 else ""
        _draw_glowing_card(draw, [80, 345, W - 80, 1075], radius=24, fill_color=(10, 30, 40, 205), glow_color=(34, 211, 238), border_width=4)
        _draw_centered_multiline(draw, title_text, center_y=470, max_width=W - 220, font_size=64, min_size=48, default_color=CYAN)
        _draw_centered_multiline(draw, main_text, center_y=720, max_width=W - 190, font_size=86, min_size=56, default_color=YELLOW)
        if sub_text:
            _draw_centered_multiline(draw, sub_text, center_y=945, max_width=W - 250, font_size=46, min_size=36, default_color=WHITE)
    
    # ─── LAYOUT: TITLE (Slide tiêu đề to mở đầu) ───
    elif layout == "title":
        font_sub = _get_font(34, bold=True)
        title_text = slide.title.upper() if slide.title else "GIỚI THIỆU"
        draw.text((74, 245), title_text, font=font_sub, fill=CYAN)
        draw.rectangle([74, 296, 260, 306], fill=CYAN)
        
        main_text = slide.content[0] if slide.content else ""
        font_main = _get_font(86, bold=True)
        wrapped_lines = _wrap_text_by_width(main_text, font_main, W - 280, draw)
        
        line_height = 104
        total_text_height = len(wrapped_lines) * line_height
        y_text = 640 - total_text_height // 2
        
        for line in wrapped_lines:
            _draw_centered_line(draw, line, y_text, font_main, default_color=WHITE, stroke_width=4)
            y_text += line_height

    # ─── LAYOUT: COMPARE (So sánh 2 bên Cũ vs Mới, Con người vs AI) ───
    elif layout == "compare":
        # Tiêu đề slide ở trên container (Y: 230)
        _draw_micro_label(draw, slide.title.upper(), YELLOW)
        
        # Chia 2 cột: Cột Trái (X: 80 -> 500), Cột Phải (X: 580 -> 1000)
        left_text = slide.content[0] if len(slide.content) > 0 else "Cách cũ"
        right_text = slide.content[1] if len(slide.content) > 1 else "Cách mới"
        
        # Vẽ Cột Trái (Cũ/Sai) - Neon Red/Slate
        left_card = [70, 340, 510, 1110]
        draw.rounded_rectangle(left_card, radius=18, fill=(70, 16, 24, 220), outline=(239, 68, 68, 240), width=4)
        
        # Title badge cột trái
        draw.text((110, 360), "CÁCH CŨ", font=font_body_bold, fill=(239, 68, 68, 255))
        draw.line([(110, 415), (470, 415)], fill=(127, 29, 29, 150), width=2)
        
        # Wrap nội dung cột trái
        left_lines = _wrap_text_by_width(left_text, font_body, 350, draw)
        y_l = 450
        for line in left_lines[:4]:
            if y_l + 45 > 1150:
                break
            _draw_left_rich_line(draw, line, 110, y_l, font_body, default_color=MUTED)
            y_l += 58
            
        # Vẽ Cột Phải (Mới/AI) - Neon Emerald
        right_card = [570, 340, 1010, 1110]
        draw.rounded_rectangle(right_card, radius=18, fill=(6, 57, 44, 230), outline=(16, 185, 129, 255), width=5)
        
        # Title badge cột phải
        draw.text((610, 360), "DÙNG AI", font=font_body_bold, fill=(16, 185, 129, 255))
        draw.line([(610, 415), (970, 415)], fill=(6, 95, 70, 150), width=2)
        
        # Wrap nội dung cột phải
        right_lines = _wrap_text_by_width(right_text, font_body, 350, draw)
        y_r = 450
        for line in right_lines[:4]:
            if y_r + 45 > 1150:
                break
            _draw_left_rich_line(draw, line, 610, y_r, font_body, default_color=WHITE)
            y_r += 58
            
        # Vẽ badge "VS" tròn ở giữa cột ranh giới
        vs_x, vs_y = W // 2, 750
        vs_r = 50
        # Glow cho VS
        for r_offset in range(vs_r + 5, vs_r, -1):
            alpha = int(50 / (r_offset - vs_r))
            draw.ellipse([vs_x - r_offset, vs_y - r_offset, vs_x + r_offset, vs_y + r_offset], fill=None, outline=(249, 115, 22, alpha), width=2)
        # Circle chính
        draw.ellipse([vs_x - vs_r, vs_y - vs_r, vs_x + vs_r, vs_y + vs_r], fill=(15, 23, 42, 255), outline=(249, 115, 22), width=3)
        
        # Chữ VS
        font_vs = _get_font(36, bold=True)
        bbox_vs = draw.textbbox((0, 0), "VS", font=font_vs)
        w_vs = bbox_vs[2] - bbox_vs[0]
        h_vs = bbox_vs[3] - bbox_vs[1]
        draw.text((vs_x - w_vs // 2, vs_y - h_vs // 2 - 2), "VS", font=font_vs, fill=(249, 115, 22, 255))

    # ─── LAYOUT: LIST (Slide danh sách gạch đầu dòng) ───
    elif layout == "list":
        # Tiêu đề slide ở trên container
        _draw_micro_label(draw, slide.title.upper(), CYAN)
        
        # Card lớn bo góc chứa danh sách
        card_xy = [86, 330, W - 86, 1160]
        draw.rounded_rectangle(card_xy, radius=20, fill=(15, 23, 42, 205), outline=(139, 92, 246, 210), width=4)
        
        y_item = 370
        for item in slide.content[:3]:  # Giới hạn tối đa 3 gạch đầu dòng
            if y_item + 50 > 1150:
                break
                
            # Vẽ check-box bo góc neon
            box_xy = [140, y_item + 4, 172, y_item + 36]
            draw.rounded_rectangle(box_xy, radius=6, fill=(6, 21, 18, 200), outline=(16, 185, 129), width=2)
            _draw_checkmark(draw, 140, y_item + 4, (16, 185, 129, 255))
            
            # Wrap nội dung item
            item_lines = _wrap_text_by_width(item, font_body, W - 320, draw)
            x_text = 195
            for i, line in enumerate(item_lines):
                if y_item + (i * 45) + 40 > 1150:
                    break
                _draw_left_rich_line(draw, line, x_text, y_item + (i * 58), font_body, default_color=WHITE)
            
            y_item += len(item_lines) * 58 + 42

    # ─── LAYOUT: CARD (Slide quote, sự thật nổi bật) ───
    else:
        # Tiêu đề slide ở trên container
        _draw_micro_label(draw, slide.title.upper(), PURPLE)
        
        # Vẽ nội dung chính
        main_text = slide.content[0] if slide.content else ""
        font_card_text = _get_font(82, bold=True)
        wrapped_lines = _wrap_text_by_width(main_text, font_card_text, W - 280, draw)
        
        # Căn giữa theo chiều dọc
        line_height = 100
        total_h = len(wrapped_lines) * line_height
        y_start = 700 - total_h // 2
        
        for line in wrapped_lines:
            bbox_l = draw.textbbox((0, 0), line, font=font_card_text)
            w_l = bbox_l[2] - bbox_l[0]
            _draw_centered_line(draw, line, y_start, font_card_text, default_color=WHITE, stroke_width=4)
            y_start += line_height

    # Lưu file dưới dạng RGB để tương thích
    img.convert("RGB").save(output_path, "PNG")
    return output_path


def convert_slide_image_to_video(image_path: str, duration: float, output_path: str) -> str:
    """
    Dùng FFmpeg chuyển ảnh tĩnh thành clip có punch zoom/pan nhẹ.
    Slide phải có cảm giác motion graphic, không phải PowerPoint đứng yên.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fps = 30
    frames = max(1, int(duration * fps))
    zoom_filter = (
        "scale=1220:2169:force_original_aspect_ratio=increase,"
        "crop=1220:2169,"
        f"zoompan="
        f"z='min(1.02+0.11*on/{frames}+0.018*sin(on/4),1.16)':"
        f"x='iw/2-(iw/zoom/2)+24*sin(on/9)':"
        f"y='ih/2-(ih/zoom/2)+20*cos(on/11)':"
        f"d={frames}:s=1080x1920:fps={fps},"
        "eq=contrast=1.08:saturation=1.12,"
        "unsharp=5:5:0.55:3:3:0.25,"
        "format=yuv420p"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", zoom_filter,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-preset", "ultrafast",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg slide convert error: {e.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("FFmpeg image loop fail")

    return output_path
