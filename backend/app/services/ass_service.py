import re


VIDEO_WIDTH = 1080
CAPTION_Y = 1340
KEYWORD_Y = 1510
MAX_WORDS_PER_CAPTION = 4
MAX_CHARS_PER_LINE = 16
MAX_LINES = 2

NEGATIVE_WORDS = {"SAI", "MẤT", "PHÍ", "ĐỪNG", "KHÔNG", "LỖI", "NGUY", "CŨ"}
TECH_WORDS = {"AI", "PROMPT", "GOOGLE", "GEMINI", "CHATGPT", "DATA", "DỮ", "LIỆU"}
CTA_WORDS = {"COMMENT", "BÌNH", "LUẬN", "SHARE", "GỬI", "LƯU", "SAVE"}

# ASS colors are BGR. These are intentionally high-contrast for mobile.
ASS_YELLOW = r"&H0000D7FF"
ASS_RED = r"&H003C3CF5"
ASS_CYAN = r"&H00EED322"
ASS_GREEN = r"&H0099D134"
ASS_PURPLE = r"&H00FC84C0"

def format_ass_time(seconds: float) -> str:
    """Chuyển đổi giây sang định dạng thời gian của ASS (H:MM:SS.cs)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    # ASS yêu cầu centiseconds có 2 chữ số (ví dụ: 05)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    """Escape các ký tự có ý nghĩa đặc biệt trong ASS."""
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", " ")
    )


def semantic_ass_color(word: str) -> str | None:
    token = re.sub(r"[^\w%]+", "", word.upper())
    if re.search(r"\d", token) or token in {"TRIỆU", "TỶ", "USD", "VND", "%"}:
        return ASS_YELLOW
    if token in NEGATIVE_WORDS:
        return ASS_RED
    if token in TECH_WORDS:
        return ASS_CYAN
    if token in CTA_WORDS:
        return ASS_GREEN
    if token in {"CÚ", "LẬT"}:
        return ASS_PURPLE
    return None


def normalize_caption_text(text: str) -> str:
    """Chuẩn hóa text theo kiểu caption ngắn, đậm như TikTok/CapCut."""
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def split_caption_lines(words: list[str]) -> list[list[str]]:
    """Chia một cụm caption thành tối đa 2 dòng để không tràn màn hình."""
    lines: list[list[str]] = [[]]
    current_len = 0

    for word in words:
        next_len = current_len + len(word) + (1 if current_len else 0)
        if next_len > MAX_CHARS_PER_LINE and len(lines) < MAX_LINES:
            lines.append([word])
            current_len = len(word)
        else:
            lines[-1].append(word)
            current_len = next_len

    return lines


def build_caption_chunks(words: list[str]) -> list[tuple[int, int]]:
    """
    Gom từ thành các cụm ngắn. Mỗi cụm là một caption riêng,
    giúp video giống TikTok/CapCut hơn thay vì hiện cả đoạn dài.
    """
    chunks = []
    start = 0

    while start < len(words):
        end = start
        char_count = 0

        while end < len(words):
            next_len = char_count + len(words[end]) + (1 if char_count else 0)
            if end > start and (
                end - start >= MAX_WORDS_PER_CAPTION
                or next_len > MAX_CHARS_PER_LINE * MAX_LINES
            ):
                break

            char_count = next_len
            end += 1

        chunks.append((start, end))
        start = end

    return chunks


def chunk_has_semantic_keyword(words: list[str]) -> bool:
    return any(semantic_ass_color(word) for word in words)


def extract_keyword_caption(words: list[str]) -> list[str]:
    """Pick only the strongest on-screen words for slide-heavy videos."""
    semantic_words = []
    for word in words:
        clean = re.sub(r"[^\w%]+", "", word.upper())
        if not clean:
            continue
        if semantic_ass_color(clean):
            semantic_words.append(clean)

    if semantic_words:
        return semantic_words[:3]

    # Fallback: choose a short punchy phrase, not the full transcript.
    strong_words = [
        re.sub(r"[^\w%]+", "", word.upper())
        for word in words
        if len(re.sub(r"[^\w%]+", "", word)) >= 4
    ]
    return strong_words[:2]


def select_caption_chunks(words: list[str], mode: str = "full") -> list[tuple[int, int]]:
    chunks = build_caption_chunks(words)
    if mode != "compact":
        return chunks

    # Slide-heavy videos already contain punchline text. Keep only the first
    # phrase plus semantic-keyword phrases to avoid duplicate-reading fatigue.
    selected = []
    for idx, chunk in enumerate(chunks):
        chunk_words = words[chunk[0]:chunk[1]]
        if idx == 0 or chunk_has_semantic_keyword(chunk_words):
            selected.append(chunk)
        if len(selected) >= 2:
            break
    return selected or chunks[:1]


def render_karaoke_caption_text(
    words: list[str],
    centiseconds_per_word: int,
) -> str:
    """Render text ASS karaoke trong một event để tránh giật layout."""
    lines = split_caption_lines(words)
    rendered_lines = []

    for line_words in lines:
        parts = []
        for word in line_words:
            safe_word = escape_ass_text(word)
            color = semantic_ass_color(word)
            if color:
                parts.append(rf"{{\k{centiseconds_per_word}\1c{color}\b1}}{safe_word}{{\rTikTok}}")
            else:
                parts.append(rf"{{\k{centiseconds_per_word}}}{safe_word}")

        rendered_lines.append(" ".join(parts))

    return r"\N".join(rendered_lines)


def render_keyword_caption_text(words: list[str]) -> str:
    parts = []
    for word in words:
        safe_word = escape_ass_text(word)
        color = semantic_ass_color(word) or ASS_YELLOW
        parts.append(rf"{{\1c{color}\b1}}{safe_word}{{\rTikTok}}")
    return " ".join(parts)


def generate_ass_subtitles(
    script_texts: list,
    durations: list,
    output_path: str,
    mode: str = "full",
):
    """
    Tạo file phụ đề .ass:
    - full: TikTok/CapCut phrase captions.
    - compact: ít caption hơn cho video nhiều chữ.
    - keyword_only: chỉ hiện keyword/punch phrase cho slide-heavy video.
    """
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTok,Roboto,86,&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,9,4,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    current_time = 0.0

    for text, audio_duration in zip(script_texts, durations):
        if not text or not text.strip():
            current_time += audio_duration
            continue

        text = normalize_caption_text(text)
        words = text.split()
        if not words:
            current_time += audio_duration
            continue

        # Logic khớp thời gian với Edge-TTS (90% duration)
        reading_duration = audio_duration * 0.9
        time_per_word = reading_duration / len(words)

        if mode == "keyword_only":
            keyword_words = extract_keyword_caption(words)
            if keyword_words:
                start = current_time + max(0.18, audio_duration * 0.38)
                end = min(current_time + audio_duration - 0.12, start + 1.15)
                if end > start:
                    events.append(
                        "Dialogue: 0,"
                        f"{format_ass_time(start)},"
                        f"{format_ass_time(end)},"
                        "TikTok,,0,0,0,,"
                        rf"{{\an5\pos({VIDEO_WIDTH // 2},{KEYWORD_Y})\fad(40,90)\fscx112\fscy112}}"
                        f"{render_keyword_caption_text(keyword_words)}"
                    )
            current_time += audio_duration
            continue

        chunks = select_caption_chunks(words, mode=mode)

        for chunk_start, chunk_end in chunks:
            chunk_words = words[chunk_start:chunk_end]
            chunk_start_time = current_time + chunk_start * time_per_word
            chunk_end_time = min(
                current_time + chunk_end * time_per_word,
                current_time + audio_duration,
            )
            chunk_duration = max(chunk_end_time - chunk_start_time, 0.1)
            centiseconds_per_word = max(
                1,
                round((chunk_duration / len(chunk_words)) * 100),
            )
            line_text = render_karaoke_caption_text(
                chunk_words,
                centiseconds_per_word,
            )

            events.append(
                "Dialogue: 0,"
                f"{format_ass_time(chunk_start_time)},"
                f"{format_ass_time(chunk_end_time)},"
                "TikTok,,0,0,0,,"
                rf"{{\an5\pos({VIDEO_WIDTH // 2},{CAPTION_Y})\fad(80,80)}}"
                f"{line_text}"
            )

        current_time += audio_duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n".join(events))
        f.write("\n")

    return output_path
