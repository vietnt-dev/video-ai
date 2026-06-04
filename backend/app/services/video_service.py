import os
import subprocess
import math
from pathlib import Path
from typing import Optional

# Vẫn giữ AudioFileClip để đọc thời lượng chuẩn xác của file TTS (chỉ đọc header, rất nhanh)
from moviepy.editor import AudioFileClip

from app.config import settings
from app.services.ass_service import generate_ass_subtitles

# Video dimensions
W = settings.video_width   # 1080
H = settings.video_height  # 1920

def compose_video(
    video_clips_paths: list,
    audio_paths: list,
    durations: list,
    script_texts: list,
    output_path: str,
    music_path: Optional[str] = None,
    use_dynamic_captions: bool = True,
    caption_mode: str = "full",
) -> str:
    """
    Sử dụng FFmpeg thuần (C/C++) để ghép nối video, lồng âm thanh và render phụ đề .ass.
    Tốc độ cực nhanh (giảm từ 4 phút xuống ~10-20 giây).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    job_id = Path(output_path).stem

    # 1. Sinh file phụ đề chuẩn ASS
    ass_path = f"{settings.assets_dir}/audio/{job_id}/subtitles.ass"
    
    # Cần tính lại durations chuẩn xác từ file audio TTS (vì durations cũ là ước tính)
    actual_durations = []
    for aud_path, est_dur in zip(audio_paths, durations):
        if aud_path and os.path.exists(aud_path):
            try:
                clip = AudioFileClip(aud_path)
                actual_durations.append(clip.duration)
                clip.close()
            except:
                actual_durations.append(est_dur)
        else:
            actual_durations.append(est_dur)

    generate_ass_subtitles(script_texts, actual_durations, ass_path, mode=caption_mode)

    # 2. Xây dựng bản đồ lệnh FFmpeg (Filtergraph)
    inputs = []
    filter_complex = []
    
    concat_v = []
    concat_a = []
    
    input_idx = 0
    
    for i, (vid_path, aud_path, dur) in enumerate(zip(video_clips_paths, audio_paths, actual_durations)):
        # ─── XỬ LÝ HÌNH ẢNH (VIDEO) ───
        if vid_path and os.path.exists(vid_path):
            # Dùng -stream_loop -1 để video lặp lại vô hạn (nếu ngắn hơn dur)
            inputs.extend(["-stream_loop", "-1", "-i", vid_path])
            # Ép về 1080x1920, cắt đúng thời lượng (trim), đồng bộ frame
            filter_complex.append(
                f"[{input_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,setsar=1,fps=24,format=yuv420p,"
                f"trim=duration={dur},setpts=PTS-STARTPTS[v{i}]"
            )
            input_idx += 1
        else:
            # Nếu không có video, tạo phông nền đen gốc
            inputs.extend(["-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={dur}"])
            filter_complex.append(f"[{input_idx}:v]fps=24,format=yuv420p[v{i}]")
            input_idx += 1
            
        concat_v.append(f"[v{i}]")
        
        # ─── XỬ LÝ ÂM THANH (AUDIO) ───
        if aud_path and os.path.exists(aud_path):
            inputs.extend(["-i", aud_path])
            filter_complex.append(
                f"[{input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                f"apad=whole_dur={dur}[a{i}]"
            )
            input_idx += 1
        else:
            inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur}"])
            filter_complex.append(f"[{input_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}]")
            input_idx += 1
            
        concat_a.append(f"[a{i}]")

    # 3. Gom (Concat) tất cả đoạn video và audio lại
    num_segments = len(actual_durations)
    v_concat_str = "".join(concat_v)
    a_concat_str = "".join(concat_a)
    
    filter_complex.append(f"{v_concat_str}concat=n={num_segments}:v=1:a=0[vbase]")
    filter_complex.append(f"{a_concat_str}concat=n={num_segments}:v=0:a=1[abase]")

    # 4. In phụ đề ASS lên video tổng
    # FFmpeg bắt buộc phải escape ký tự đặc biệt trong đường dẫn file
    escaped_ass = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\\\:')
    fonts_dir = os.path.abspath(os.path.join(settings.assets_dir, "fonts")).replace('\\', '/').replace(':', '\\\\:')
    filter_complex.append(f"[vbase]ass='{escaped_ass}':fontsdir='{fonts_dir}'[vout]")

    # 5. Lồng nhạc nền (Background Music)
    if music_path and os.path.exists(music_path):
        inputs.extend(["-stream_loop", "-1", "-i", music_path])
        music_idx = input_idx
        # Giảm âm lượng nhạc nền xuống 12%, lặp vô hạn
        filter_complex.append(f"[{music_idx}:a]volume=0.12[bgm]")
        # Mix nhạc nền và giọng đọc
        filter_complex.append(f"[abase][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]")
    else:
        filter_complex.append(f"[abase]anull[aout]")

    # Gộp toàn bộ filtergraph
    filter_script = ";".join(filter_complex)

    # 6. Chạy FFmpeg
    configured_threads = settings.ffmpeg_threads or 2
    cpu_count = str(max(1, min(configured_threads, os.cpu_count() or configured_threads)))
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_script,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", "24",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-threads", cpu_count,
        output_path
    ]

    print(f"🚀 Executing Enterprise FFmpeg pipeline for {job_id}...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error Output:\n{e.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("FFmpeg processing failed")

    return output_path
