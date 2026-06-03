"""
Slide Generation Service.

Sử dụng Pillow để vẽ các slide dạng Infographic/Trình bày đẹp mắt ở tỷ lệ 9:16.
Sau đó dùng FFmpeg để convert ảnh slide tĩnh thành video mp4 cực nhanh.
"""
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.models import SlideContent

W = settings.video_width   # 1080
H = settings.video_height  # 1920

# Đường dẫn font
FONT_DIR = Path(settings.assets_dir) / "fonts"
FONT_BOLD_PATH = FONT_DIR / "Roboto-Bold.ttf"
FONT_BLACK_PATH = FONT_DIR / "Roboto-Black.ttf"


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
    """Tạo hình nền gradient đứng kết hợp các vệt sáng neon mờ ở tâm."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    
    # Nền tối sâu từ xanh xám (#0a0f1e) đến đen (#03050c)
    color_top = (10, 15, 30)
    color_bottom = (3, 5, 12)
    for y in range(h):
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * y / h)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * y / h)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
        
    # Vệt sáng Neon mờ (Cyan ở tâm và Tím ở góc dưới)
    _draw_soft_glow(draw, w // 2, h // 2 - 100, 480, (6, 182, 212))
    _draw_soft_glow(draw, w // 2 + 150, h // 2 + 150, 400, (139, 92, 246))


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


def draw_slide_image(slide: SlideContent, output_path: str, topic: str = "") -> str:
    """
    Vẽ ảnh slide 1080x1920 theo cấu trúc SlideContent và lưu vào output_path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (W, H))
    
    # 1. Vẽ nền gradient kết hợp neon glow
    _draw_neon_background(img)
    
    draw = ImageDraw.Draw(img)
    
    # 2. Vẽ header (phần tiêu đề nhỏ cố định ở trên)
    font_header = _get_font(34, bold=False)
    header_text = f"{topic.upper()}" if topic else "CHIA SẺ KIẾN THỨC"
    
    # Giới hạn độ dài header
    if len(header_text) > 42:
        header_text = header_text[:39] + "..."
        
    bbox_h = draw.textbbox((0, 0), header_text, font=font_header)
    w_h = bbox_h[2] - bbox_h[0]
    h_h = bbox_h[3] - bbox_h[1]
    
    # Capsule badge cho header
    pill_xy = [W // 2 - w_h // 2 - 25, 95, W // 2 + w_h // 2 + 25, 155]
    draw.rounded_rectangle(pill_xy, radius=18, fill=(30, 41, 59, 120), outline=(99, 102, 241, 150), width=2)
    draw.text((W // 2 - w_h // 2, 125 - h_h // 2 - 2), header_text, font=font_header, fill=(226, 232, 240, 255))
    
    # Đường phân cách mảnh mờ dưới header
    draw.line([(120, 185), (W - 120, 185)], fill=(30, 41, 59, 150), width=2)
    
    # Load fonts
    font_title = _get_font(44, bold=True)
    font_body = _get_font(30, bold=False)
    font_body_bold = _get_font(30, bold=True)

    layout = slide.layout.lower()
    
    # ─── LAYOUT: TITLE (Slide tiêu đề to mở đầu) ───
    if layout == "title":
        # Card bo góc ở giữa
        card_xy = [100, 360, W - 100, 1120]
        # Màu nền card: #1e293b với alpha 160. Viền neon cyan: #06b6d4
        _draw_glowing_card(draw, card_xy, radius=35, fill_color=(30, 41, 59, 160), glow_color=(6, 182, 212), border_width=3)
        
        # Capsule/Badge trên đầu card
        font_sub = _get_font(32, bold=True)
        title_text = slide.title.upper() if slide.title else "GIỚI THIỆU"
        bbox_sub = draw.textbbox((0, 0), title_text, font=font_sub)
        w_sub = bbox_sub[2] - bbox_sub[0]
        h_sub = bbox_sub[3] - bbox_sub[1]
        
        badge_xy = [W // 2 - w_sub // 2 - 25, 330, W // 2 + w_sub // 2 + 25, 390]
        draw.rounded_rectangle(badge_xy, radius=18, fill=(15, 23, 42, 230), outline=(6, 182, 212), width=2)
        draw.text((W // 2 - w_sub // 2, 360 - h_sub // 2 - 2), title_text, font=font_sub, fill=(6, 182, 212, 255))
        
        # Vẽ nội dung chính
        main_text = slide.content[0] if slide.content else ""
        font_main = _get_font(52, bold=True)
        wrapped_lines = _wrap_text_by_width(main_text, font_main, W - 280, draw)
        
        # Căn giữa theo chiều dọc trong card
        card_height = 1120 - 360
        line_height = 70
        total_text_height = len(wrapped_lines) * line_height
        y_text = 360 + (card_height - total_text_height) // 2 + 10
        
        for line in wrapped_lines:
            bbox_l = draw.textbbox((0, 0), line, font=font_main)
            w_l = bbox_l[2] - bbox_l[0]
            # Draw shadow
            draw.text(((W - w_l) // 2 + 2, y_text + 2), line, font=font_main, fill=(0, 0, 0, 150))
            draw.text(((W - w_l) // 2, y_text), line, font=font_main, fill=(255, 255, 255, 255))
            y_text += line_height

    # ─── LAYOUT: COMPARE (So sánh 2 bên Cũ vs Mới, Con người vs AI) ───
    elif layout == "compare":
        # Tiêu đề slide ở trên container (Y: 230)
        draw.text((80, 230), slide.title.upper(), font=font_title, fill=(245, 158, 11, 255))
        
        # Chia 2 cột: Cột Trái (X: 80 -> 500), Cột Phải (X: 580 -> 1000)
        left_text = slide.content[0] if len(slide.content) > 0 else "Cách cũ"
        right_text = slide.content[1] if len(slide.content) > 1 else "Cách mới"
        
        # Vẽ Cột Trái (Cũ/Sai) - Neon Red/Slate
        left_card = [80, 320, 500, 1180]
        _draw_glowing_card(draw, left_card, radius=25, fill_color=(28, 15, 20, 160), glow_color=(239, 68, 68), border_width=2)
        
        # Title badge cột trái
        draw.text((110, 360), "CÁCH CŨ", font=font_body_bold, fill=(239, 68, 68, 255))
        draw.line([(110, 415), (470, 415)], fill=(127, 29, 29, 150), width=2)
        
        # Wrap nội dung cột trái
        left_lines = _wrap_text_by_width(left_text, font_body, 360, draw)
        y_l = 450
        for line in left_lines[:9]:
            if y_l + 45 > 1150:
                break
            draw.text((110, y_l), line, font=font_body, fill=(226, 232, 240, 255))
            y_l += 45
            
        # Vẽ Cột Phải (Mới/AI) - Neon Emerald
        right_card = [580, 320, 1000, 1180]
        _draw_glowing_card(draw, right_card, radius=25, fill_color=(13, 37, 28, 170), glow_color=(16, 185, 129), border_width=3)
        
        # Title badge cột phải
        draw.text((610, 360), "DÙNG AI", font=font_body_bold, fill=(16, 185, 129, 255))
        draw.line([(610, 415), (970, 415)], fill=(6, 95, 70, 150), width=2)
        
        # Wrap nội dung cột phải
        right_lines = _wrap_text_by_width(right_text, font_body, 360, draw)
        y_r = 450
        for line in right_lines[:9]:
            if y_r + 45 > 1150:
                break
            draw.text((610, y_r), line, font=font_body, fill=(255, 255, 255, 255))
            y_r += 45
            
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
        draw.text((80, 230), slide.title.upper(), font=font_title, fill=(56, 189, 248, 255))
        
        # Card lớn bo góc chứa danh sách
        card_xy = [100, 320, W - 100, 1180]
        # Neon violet: #8b5cf6
        _draw_glowing_card(draw, card_xy, radius=30, fill_color=(15, 23, 42, 160), glow_color=(139, 92, 246), border_width=3)
        
        y_item = 370
        for item in slide.content[:4]:  # Giới hạn tối đa 4 gạch đầu dòng
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
                draw.text((x_text, y_item + (i * 45)), line, font=font_body, fill=(255, 255, 255, 255))
            
            y_item += len(item_lines) * 45 + 40

    # ─── LAYOUT: CARD (Slide quote, sự thật nổi bật) ───
    else:
        # Tiêu đề slide ở trên container
        draw.text((80, 230), slide.title.upper(), font=font_title, fill=(168, 85, 247, 255))
        
        # Card quote
        card_xy = [100, 320, W - 100, 1150]
        _draw_glowing_card(draw, card_xy, radius=30, fill_color=(18, 14, 46, 170), glow_color=(168, 85, 247), border_width=3)
        
        # Dấu ngoặc kép quote trang trí
        font_quote = _get_font(180, bold=True)
        draw.text((140, 350), "“", font=font_quote, fill=(168, 85, 247, 40))
        draw.text((W - 220, 950), "”", font=font_quote, fill=(168, 85, 247, 40))
        
        # Vẽ nội dung chính
        main_text = slide.content[0] if slide.content else ""
        font_card_text = _get_font(40, bold=False)
        wrapped_lines = _wrap_text_by_width(main_text, font_card_text, W - 280, draw)
        
        # Căn giữa theo chiều dọc
        line_height = 60
        total_h = len(wrapped_lines) * line_height
        card_h = 1150 - 320
        y_start = 320 + (card_h - total_h) // 2
        
        for line in wrapped_lines:
            bbox_l = draw.textbbox((0, 0), line, font=font_card_text)
            w_l = bbox_l[2] - bbox_l[0]
            # Draw shadow
            draw.text(((W - w_l) // 2 + 2, y_start + 2), line, font=font_card_text, fill=(0, 0, 0, 120))
            draw.text(((W - w_l) // 2, y_start), line, font=font_card_text, fill=(255, 255, 255, 255))
            y_start += line_height

    # Lưu file dưới dạng RGB để tương thích
    img.convert("RGB").save(output_path, "PNG")
    return output_path


def convert_slide_image_to_video(image_path: str, duration: float, output_path: str) -> str:
    """
    Dùng FFmpeg chuyển đổi ảnh tĩnh thành video MP4 có thời lượng chính xác.
    Cực kỳ nhẹ, nhanh và ổn định.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-r", "24",
        "-preset", "ultrafast",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg slide convert error: {e.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("FFmpeg image loop fail")

    return output_path
