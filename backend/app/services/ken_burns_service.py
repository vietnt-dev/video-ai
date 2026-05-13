"""
Ken Burns Effect Service.

Biến ảnh tĩnh thành video có chuyển động (zoom in/out + pan).
Kỹ thuật này được dùng rộng rãi trong documentary và short-form content
để tạo cảm giác sống động từ ảnh tĩnh.

Các hiệu ứng:
- zoom_in    : zoom vào trung tâm (phổ biến nhất)
- zoom_out   : zoom ra từ trung tâm
- pan_right  : di chuyển từ trái sang phải
- pan_left   : di chuyển từ phải sang trái
- pan_up     : di chuyển từ dưới lên
- diagonal   : zoom + pan chéo (cinematic nhất)
"""
import os
import random
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image
from moviepy.editor import VideoClip, ImageClip

from app.config import settings

W = settings.video_width   # 1080
H = settings.video_height  # 1920

EffectType = Literal["zoom_in", "zoom_out", "pan_right", "pan_left", "pan_up", "diagonal"]

VIRAL_CUT_INTERVAL = 2.0

# Mapping style → effect phù hợp
STYLE_EFFECTS: dict[str, list[EffectType]] = {
    "co_nhan":     ["zoom_in", "pan_up", "diagonal"],
    "tu_vi":       ["zoom_in", "diagonal"],
    "su_that":     ["zoom_in", "zoom_out"],
    "tam_ly":      ["zoom_in", "pan_right"],
    "lam_giau":    ["zoom_in", "diagonal"],
    "suc_khoe":    ["pan_right", "pan_up", "zoom_in"],
    "tinh_cam":    ["zoom_in", "pan_right"],
    "engaging":    ["zoom_in", "zoom_out", "diagonal"],
    "educational": ["zoom_in", "pan_right"],
    "funny":       ["zoom_out", "pan_right"],
}


def _load_and_resize_image(image_path: str) -> np.ndarray:
    """Load ảnh và resize về đúng kích thước 9:16, crop nếu cần."""
    img = Image.open(image_path).convert("RGB")

    # Resize để cover toàn bộ frame (thêm 20% để có room cho animation)
    scale = 1.2
    target_w = int(W * scale)
    target_h = int(H * scale)

    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    return np.array(img)


def create_ken_burns_clip(
    image_path: str,
    duration: float,
    effect: EffectType = "zoom_in",
    style: str = "engaging",
) -> VideoClip:
    """
    Tạo video clip từ ảnh tĩnh với Ken Burns effect.

    Args:
        image_path: đường dẫn file ảnh (JPG/PNG)
        duration  : thời lượng clip (giây)
        effect    : loại hiệu ứng
        style     : phong cách video (để chọn effect phù hợp nếu effect="auto")

    Returns: MoviePy VideoClip
    """
    if effect == "auto":
        effects = STYLE_EFFECTS.get(style, ["zoom_in", "diagonal"])
        effect = random.choice(effects)

    frame_array = _load_and_resize_image(image_path)
    img_h, img_w = frame_array.shape[:2]
    cut_count = max(1, int(duration / VIRAL_CUT_INTERVAL) + 1)
    rng = random.Random(f"{image_path}:{duration}:{effect}:{style}")
    cut_offsets = [
        (
            rng.uniform(0.36, 0.64),
            rng.uniform(0.34, 0.62),
            rng.uniform(0.0, 0.04),
        )
        for _ in range(cut_count)
    ]

    def make_frame(t: float) -> np.ndarray:
        """Tạo frame tại thời điểm t."""
        progress = t / duration  # 0.0 → 1.0
        cut_index = min(int(t / VIRAL_CUT_INTERVAL), cut_count - 1)
        local_progress = (t % VIRAL_CUT_INTERVAL) / VIRAL_CUT_INTERVAL
        anchor_x, anchor_y, scale_boost = cut_offsets[cut_index]

        if effect == "zoom_in":
            # Zoom từ 100% → 120%, center
            scale = 1.04 + scale_boost + 0.08 * local_progress
            crop_w = int(W / scale)
            crop_h = int(H / scale)
            x = int((img_w - crop_w) * anchor_x)
            y = int((img_h - crop_h) * anchor_y)

        elif effect == "zoom_out":
            # Zoom từ 120% → 100%, center
            scale = 1.16 + scale_boost - 0.08 * local_progress
            crop_w = int(W / scale)
            crop_h = int(H / scale)
            x = int((img_w - crop_w) * anchor_x)
            y = int((img_h - crop_h) * anchor_y)

        elif effect == "pan_right":
            # Pan từ trái sang phải
            crop_w = W
            crop_h = H
            max_x = img_w - crop_w
            x = int(max_x * min(0.85, anchor_x + local_progress * 0.18))
            y = int((img_h - crop_h) * anchor_y)

        elif effect == "pan_left":
            # Pan từ phải sang trái
            crop_w = W
            crop_h = H
            max_x = img_w - crop_w
            x = int(max_x * max(0.05, anchor_x - local_progress * 0.18))
            y = int((img_h - crop_h) * anchor_y)

        elif effect == "pan_up":
            # Pan từ dưới lên
            crop_w = W
            crop_h = H
            max_y = img_h - crop_h
            x = int((img_w - crop_w) * anchor_x)
            y = int(max_y * max(0.05, anchor_y - local_progress * 0.18))

        elif effect == "diagonal":
            # Zoom in + pan chéo (cinematic nhất)
            scale = 1.05 + scale_boost + 0.07 * local_progress
            crop_w = int(W / scale)
            crop_h = int(H / scale)
            max_x = img_w - crop_w
            max_y = img_h - crop_h
            x = int(max_x * min(0.85, anchor_x + local_progress * 0.12))
            y = int(max_y * min(0.85, anchor_y + local_progress * 0.10))

        else:
            # Fallback: static center crop
            crop_w, crop_h = W, H
            x = (img_w - crop_w) // 2
            y = (img_h - crop_h) // 2

        # Clamp để không ra ngoài ảnh
        x = max(0, min(x, img_w - crop_w))
        y = max(0, min(y, img_h - crop_h))

        # Crop
        cropped = frame_array[y:y + crop_h, x:x + crop_w]

        # Resize về đúng W x H nếu cần
        if cropped.shape[1] != W or cropped.shape[0] != H:
            pil_img = Image.fromarray(cropped).resize((W, H), Image.BILINEAR)
            cropped = np.array(pil_img)

        return cropped

    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_fps(24)
    return clip


def image_to_video(
    image_path: str,
    output_path: str,
    duration: float,
    effect: EffectType = "auto",
    style: str = "engaging",
) -> str:
    """
    Convert ảnh thành video MP4 với Ken Burns effect.

    Returns: đường dẫn file video đã tạo
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    clip = create_ken_burns_clip(image_path, duration, effect, style)

    clip.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        bitrate="2000k",
        preset="ultrafast",
        threads=os.cpu_count() or 4,
        audio=False,
        logger=None,
    )
    clip.close()

    print(f"  🎬 Ken Burns video: {Path(output_path).name} ({duration:.1f}s, effect={effect})")
    return output_path
