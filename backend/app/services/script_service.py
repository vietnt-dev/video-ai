"""
Script generation service.
Hỗ trợ cả Gemini (miễn phí) và OpenAI GPT-4o.
Provider được chọn tự động dựa trên config AI_PROVIDER.
"""
import json
import re
from app.config import settings
from app.models import VideoScript, ScriptSegment
from app.services.style_prompts import get_style_system_prompt, get_style_config

# Base format — áp dụng cho mọi style và provider
BASE_FORMAT_PROMPT = """
QUY TẮC BẮT BUỘC CHO VOICE-OVER SHORTS:
- Viết như người Việt nói chuyện hàng ngày ngoài đời thực, KHÔNG viết như bài văn, bài báo hay quảng cáo.
- Dùng từ ngữ đời thường, gần gũi, bắt trend và cực kỳ tự nhiên. Cho phép dùng từ lóng văn phòng, công nghệ nếu phù hợp ngữ cảnh (ví dụ: gánh team, ăn hành, auto xịn, out trình, bay màu, quay xe, bị sếp dí, bắt bài, tạ...).
- Mỗi câu 5-10 từ. Một ý, một câu. Nhịp rất nhanh, dễ đọc thành tiếng, không dùng câu ghép phức tạp.
- Mật độ thông tin cao: mỗi câu phải thêm một dữ kiện mới, một cú lật hoặc một hành động thực tế.
- Hook phải vào thẳng vấn đề ngay từ giây đầu tiên bằng một câu giật gân hoặc mâu thuẫn lớn, tuyệt đối không dẫn nhập, không giới thiệu.
- Video phải có một "đường dây căng": vấn đề kịch tính → cú lật bất ngờ → ví dụ đời thật → giải thích bản chất → hành động thực tế.
- Mỗi segment phải làm người xem tò mò muốn nghe câu tiếp theo, tuyệt đối không liệt kê kiến thức khô khan đều đều kiểu sách giáo khoa.
- Mỗi segment phải có ít nhất một trong các yếu tố: mâu thuẫn trái chiều, ví dụ cụ thể sát sườn, con số thực tế đời thường, hoặc câu lật ngược kỳ vọng.
- Ưu tiên ví dụ rất cụ thể của người Việt: lương 5 triệu, tiền nhà, hóa đơn điện nước, đi trễ bị phạt, sếp dí deadline, lướt điện thoại 2h sáng, nhịn ăn sáng.
- Nghiêm cấm viết kiểu sách giáo khoa/dịch thuật: "đó chính là", "lý do là", "tóm lại", "đầu tiên", "tiếp theo", "ngoài ra", "chúng ta cần phải", "sau đây".
- Nghiêm cấm dùng các câu sáo rỗng: "Trong video này", "Hãy cùng khám phá", "Bạn có biết rằng", "bí mật tuyệt vời", "hành trình".
- Không dùng giọng dịch máy, không dùng từ Hán-Việt nặng nề nếu có từ thuần Việt phổ thông hơn.
- Không nhồi emoji trong narration. Emoji chỉ dùng trong title nếu cần.
- Mỗi segment phải tạo được slide content cực kỳ ngắn gọn, sắc bén để hiển thị trên màn hình điện thoại.
- Nếu chủ đề thuộc sức khỏe, tài chính, tử vi hoặc tâm lý: tránh cam kết chắc chắn, tránh chẩn đoán, tránh hứa kết quả.
- Visual phải là cảnh quay cụ thể bám sát đúng câu thoại, không dùng cảnh chung chung như landscape, people walking, abstract background.
- Visual_prompt phải bắt đầu bằng chủ thể chính có thể tìm thấy trên stock footage, không bắt đầu bằng động từ mơ hồ như visualizing, showing, representing.

Trả về JSON theo đúng format sau, KHÔNG thêm bất kỳ text nào khác:
{
  "hook": "Câu hook 3 giây đầu — ngắn, giật gân, tạo tò mò ngay lập tức (ví dụ: Dừng lại! Đừng..., Sự thật phũ phàng về...)",
  "segments": [
    {
      "text": "Nội dung đọc — tiếng Việt tự nhiên, như lời nói, câu ngắn 5-10 từ",
      "visual_prompt": "Specific English description for Pexels/Imagen stock footage search",
      "duration": 4.5,
      "slide": {
        "layout": "title | compare | list | card",
        "title": "TIÊU ĐỀ SLIDE (ngắn gọn, in hoa, max 4 từ)",
        "content": ["Nội dung dòng 1", "Nội dung dòng 2"]
      }
    }
  ],
  "call_to_action": "CTA cuối video — ngắn, tự nhiên, kêu giúp bình luận hoặc click link",
  "total_duration": 32.0,
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "suggested_title": "Tiêu đề YouTube SEO ≤70 ký tự, có emoji, có keyword chính",
  "suggested_description": "Mô tả 2-3 câu, có hashtag trending"
}"""

RETENTION_SCRIPT_PROMPT = """
CẤU TRÚC GIỮ CHÂN BẮT BUỘC:
1. Hook: Cực kỳ giật gân, tát thẳng vào nỗi đau hoặc chỉ ra một nghịch lý cực lớn (ví dụ: Dừng lại! Sếp bạn đang..., Cú lừa lớn nhất khi...).
2. Segment 1: Đập tan một niềm tin sai lầm cũ của người xem.
3. Segment 2: Đưa ra ví dụ thực tế cực kỳ cụ thể tại Việt Nam (Ví dụ: cày cuốc 12 tiếng vẫn nghèo, bị sếp mắng oan...).
4. Segment 3: Lý giải ngắn gọn bản chất/nguyên nhân ẩn sau (nhấn mạnh yếu tố bất ngờ).
5. Segment 4: Cú lật (Twist) hoặc bài học sắc bén giúp họ "quay xe" nhận thức.
6. Segment 5: Hành động nhỏ, cụ thể làm được ngay lập tức để thay đổi.
7. CTA: Câu chốt kích thích bình luận tranh cãi hoặc chia sẻ một cách tự nhiên nhất.

NHỊP KỂ:
- Mỗi segment chỉ gồm 1 câu thoại đắt giá, hoặc tối đa 2 câu siêu ngắn.
- Tuyệt đối không dùng giọng giáo điều dạy đời. Hãy đóng vai một người bạn ranh ma đang chỉ ra góc khuất mà họ chưa từng nghĩ tới.
- Giữ sự tò mò xuyên suốt: câu trước phải làm bàn đạp để câu sau nổ ra, không được kết thúc ý quá sớm.
- Tổng thời lượng video khoảng 25-35 giây (80-125 từ). Chỉ tập trung vào một luận điểm duy nhất, không lan man giải thích nhiều.
"""


WEAK_HOOK_PHRASES = {
    "trong video này",
    "hãy cùng",
    "bạn có biết",
    "cùng khám phá",
    "bí mật tuyệt vời",
    "hành trình",
}

BORING_BODY_PHRASES = {
    "đó chính là",
    "lý do là",
    "đầu tiên",
    "tiếp theo",
    "ngoài ra",
    "tóm lại",
    "rất quan trọng",
    "cần lưu ý",
    "một cách hiệu quả",
}

RETENTION_MARKERS = {
    "nhưng",
    "thật ra",
    "vấn đề là",
    "không phải",
    "sai lầm",
    "đừng",
    "vì sao",
    "tại sao",
    "đây là",
    "chỉ cần",
    "ví dụ",
    "mỗi ngày",
    "hôm nay",
}


def score_hook(hook: str) -> tuple[int, list[str]]:
    """Chấm hook theo các tín hiệu giữ chân người xem Shorts."""
    normalized = re.sub(r"\s+", " ", hook or "").strip().lower()
    words = normalized.split()
    score = 0
    reasons: list[str] = []

    if 5 <= len(words) <= 14:
        score += 2
    else:
        reasons.append("Hook nên dài 5-14 từ.")

    if any(char.isdigit() for char in normalized):
        score += 1

    if any(marker in normalized for marker in ("?", "vì sao", "tại sao", "sự thật", "lý do", "sai lầm", "đừng")):
        score += 2
    else:
        reasons.append("Hook thiếu curiosity gap hoặc nghịch lý.")

    if any(phrase in normalized for phrase in WEAK_HOOK_PHRASES):
        score -= 3
        reasons.append("Hook có cụm mở bài sáo rỗng.")

    if len(set(words)) <= max(3, len(words) * 0.6):
        score -= 1
        reasons.append("Hook lặp từ, nghe thiếu sắc.")

    return score, reasons


def build_video_script(raw: dict, topic: str) -> VideoScript:
    from app.models import SlideContent
    
    segments = []
    for seg in raw.get("segments", []):
        slide_data = None
        if "slide" in seg and seg["slide"]:
            slide_raw = seg["slide"]
            slide_data = SlideContent(
                layout=slide_raw.get("layout", "card"),
                title=slide_raw.get("title", ""),
                content=slide_raw.get("content", [])
            )
        segments.append(
            ScriptSegment(
                text=seg["text"],
                visual_prompt=seg["visual_prompt"],
                duration=float(seg.get("duration", 8.0)),
                slide=slide_data
            )
        )

    return VideoScript(
        hook=raw["hook"],
        segments=segments,
        call_to_action=raw["call_to_action"],
        total_duration=float(raw.get("total_duration", 55.0)),
        keywords=raw.get("keywords", [topic]),
        suggested_title=raw.get("suggested_title"),
        suggested_description=raw.get("suggested_description"),
    )


def extract_json_object(raw_text: str) -> str:
    """Lấy object JSON đầu tiên từ response, kể cả khi có markdown bao quanh."""
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    in_string = False
    escape = False
    depth = 0

    for index in range(start, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return text[start:]


def _fix_json_strings(text: str) -> str:
    """
    Sửa các lỗi phổ biến trong JSON string từ AI:
    - Newline/tab thật bên trong string value → escape thành \\n, \\t
    - Smart quotes → straight quotes
    - Trailing comma
    """
    # Thay smart quotes
    text = (
        text
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    # Escape newline/tab thật bên trong string values
    # Duyệt từng ký tự, chỉ escape khi đang trong string
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
                continue
            if ch == "\r":
                result.append("\\r")
                continue
            if ch == "\t":
                result.append("\\t")
                continue
        result.append(ch)

    cleaned = "".join(result)
    # Xoá trailing comma trước } hoặc ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def parse_script_json(raw_text: str) -> dict:
    """Parse JSON từ AI và sửa vài lỗi format phổ biến."""
    json_text = extract_json_object(raw_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        cleaned = _fix_json_strings(json_text)
        return json.loads(cleaned)


def score_script(script: VideoScript) -> tuple[int, list[str]]:
    """Chấm toàn kịch bản để tránh video đúng nhưng nhạt."""
    score, reasons = score_hook(script.hook)
    body = " ".join([seg.text for seg in script.segments]).lower()
    segment_texts = [seg.text.strip() for seg in script.segments if seg.text.strip()]
    word_count = len((script.hook + " " + body + " " + script.call_to_action).split())

    if 4 <= len(segment_texts) <= 6:
        score += 2
    else:
        reasons.append("Nên có 4-6 segment, ít nhưng sắc.")

    if 80 <= word_count <= 125:
        score += 2
    else:
        reasons.append("Kịch bản nên khoảng 80-125 từ để giữ nhịp 25-35 giây.")

    marker_hits = sum(1 for marker in RETENTION_MARKERS if marker in body)
    if marker_hits >= 3:
        score += 3
    else:
        reasons.append("Thiếu mâu thuẫn, cú lật, hoặc tín hiệu kéo người xem nghe tiếp.")

    if any(char.isdigit() for char in body):
        score += 1
    else:
        reasons.append("Nên có ít nhất một con số đời thường hoặc mốc cụ thể.")

    if any(word in body for word in ("lương", "tiền", "hóa đơn", "điện thoại", "cơm", "ngủ", "sếp", "mẹ", "chợ", "cà phê")):
        score += 2
    else:
        reasons.append("Thiếu ví dụ đời sống Việt Nam đủ cụ thể.")

    boring_hits = sum(1 for phrase in BORING_BODY_PHRASES if phrase in body)
    if boring_hits:
        score -= boring_hits * 2
        reasons.append("Body còn giọng giáo khoa/liệt kê.")

    repeated_starts = [
        text.split()[0].lower()
        for text in segment_texts
        if text.split()
    ]
    if len(repeated_starts) != len(set(repeated_starts)):
        score -= 1
        reasons.append("Nhiều segment mở đầu giống nhau, nhịp nghe dễ đều.")

    return score, reasons


def build_fallback_script(topic: str, style: str = "engaging") -> VideoScript:
    """Fallback tối thiểu để job không fail khi provider trả JSON hỏng liên tục."""
    from app.models import SlideContent
    return VideoScript(
        hook=f"Bạn tưởng {topic} đơn giản? Sai lầm nằm ở đây.",
        segments=[
            ScriptSegment(
                text="Không phải bạn thiếu cố gắng, mà đang nhìn sai vấn đề.",
                visual_prompt="Vietnamese person looking confused at phone, close up, realistic",
                duration=4.5,
                slide=SlideContent(layout="title", title="SAI LẦM LỚN", content=["Bạn nhìn sai vấn đề"])
            ),
            ScriptSegment(
                text="Ví dụ, chỉ một thói quen nhỏ mỗi ngày cũng kéo kết quả đi xa.",
                visual_prompt="Vietnamese office worker repeating daily habit, desk, close up",
                duration=5.0,
                slide=SlideContent(layout="card", title="VÍ DỤ", content=["Thói quen nhỏ kéo kết quả đi xa"])
            ),
            ScriptSegment(
                text="Vấn đề là não thích đường dễ, dù đường đó làm bạn chậm lại.",
                visual_prompt="Tired Vietnamese person choosing easy option, phone distraction",
                duration=5.0,
                slide=SlideContent(layout="compare", title="VẤN ĐỀ", content=["Não thích đường dễ", "Kết quả bị chậm lại"])
            ),
            ScriptSegment(
                text="Cú lật là bạn không cần đổi hết, chỉ cần đổi điểm bắt đầu.",
                visual_prompt="Vietnamese person writing one small plan, notebook, morning light",
                duration=5.0,
                slide=SlideContent(layout="card", title="CÚ LẬT", content=["Đổi điểm bắt đầu"])
            ),
            ScriptSegment(
                text="Hôm nay, chọn một việc nhỏ và làm nó trong 5 phút.",
                visual_prompt="Phone timer five minutes, Vietnamese person starting focused work",
                duration=4.5,
                slide=SlideContent(layout="list", title="HÀNH ĐỘNG", content=["Chọn một việc nhỏ", "Làm trong 5 phút"])
            ),
        ],
        call_to_action="Bạn từng mắc lỗi này chưa? Bình luận thật nhé.",
        total_duration=31.0,
        keywords=[topic, style, "shorts", "viral", "Việt Nam"],
        suggested_title=f"{topic}: Sai lầm nhỏ nhiều người bỏ qua",
        suggested_description=f"Một góc nhìn ngắn, dễ hiểu về {topic}. #shorts #viral",
    )


async def _generate_with_gemini(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Gọi Gemini để tạo script."""
    from app.services.gemini_service import gemini_generate

    raw_text = await gemini_generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.85,
        json_mode=True,
    )
    return raw_text


async def _generate_with_openai(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Gọi OpenAI để tạo script."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    return response.choices[0].message.content


async def generate_script(
    topic: str,
    style: str = "engaging",
    language: str = "vi",
    media_source: str = "hybrid",
) -> VideoScript:
    """
    Tạo kịch bản video từ chủ đề.
    Tự động chọn Gemini (free) hoặc OpenAI tùy config.
    """
    from app.services.gemini_service import get_active_provider

    style_config = get_style_config(style)
    style_system_prompt = get_style_system_prompt(style)
    full_system_prompt = style_system_prompt + "\n\n" + BASE_FORMAT_PROMPT + "\n\n" + RETENTION_SCRIPT_PROMPT

    lang_note = (
        "Viết bằng tiếng Việt Việt Nam — tự nhiên, đời thường, đọc lên nghe trôi chảy"
        if language == "vi"
        else "Write in English — natural, conversational tone"
    )

    slide_instruction = ""
    if media_source == "slide":
        slide_instruction = """
QUY TẮC BẮT BUỘC CHO TRÌNH CHIẾU SLIDE (Mỗi segment phải chứa thêm trường "slide"):
- "slide" object gồm:
  1. "layout": "title" (slide tiêu đề mở đầu), "compare" (slide so sánh 2 cột), "list" (slide danh sách 2-3 gạch đầu dòng), hoặc "card" (slide thẻ thông tin lớn ở giữa).
  2. "title": Tiêu đề cực ngắn của slide (in hoa, viết gọn, max 4 từ, ví dụ: "LÀM VIỆC", "SAI LẦM").
  3. "content": Mảng chứa các chuỗi nội dung chính hiển thị trên slide (phải viết hoa câu ngắn gọn, súc tích).
     - Với layout "compare": mảng bắt buộc có đúng 2 phần tử dạng ["Ý Cũ/Sai", "Ý Mới/Đúng"]. Ví dụ: ["Tự gõ phím mất 2h", "AI viết trong 10s"].
     - Với layout "list": mảng chứa từ 2 đến 3 phần tử đại diện cho các gạch đầu dòng. Ví dụ: ["Tiết kiệm 80% thời gian", "Tự động hóa hoàn toàn"].
     - Với layout "title" hoặc "card": mảng chứa 1 phần tử đại diện cho thông tin nổi bật.
"""

    base_user_prompt = f"""Chủ đề: {topic}
Phong cách: {style_config.get('label', style)}
{lang_note}
{slide_instruction}

Tạo kịch bản video ngắn 25-35 giây với:
- Hook 3 giây đầu: một câu ngắn, mạnh, đúng công thức của phong cách này, không giải thích hết
- 5 đoạn nội dung chính theo đúng cấu trúc: sai lầm/niềm tin cũ → ví dụ đời thật → giải thích ngắn → cú lật → hành động nhỏ
- Mỗi đoạn 4-5 giây, 1 câu rất gọn; không đoạn nào dài quá 2 câu
- Tổng nội dung nên 80-125 từ nhưng phải dày thông tin, không câu đệm
- Mỗi đoạn phải có lực kéo riêng, không được chỉ liệt kê thông tin đúng
- Ít nhất 2 đoạn phải có ví dụ đời sống Việt Nam thật cụ thể
- Ít nhất 1 đoạn phải có con số hoặc mốc thời gian đời thường
- Visual prompts bằng tiếng Anh, mỗi prompt là một cảnh quay cụ thể 8-14 từ, ưu tiên vật/người/hành động có thể thấy rõ
- Mỗi visual_prompt phải chứa 2-4 keyword tìm stock video sát nghĩa, ví dụ: "Vietnamese office worker checking bills, worried face, close up"
- Tránh visual_prompt trừu tượng hoặc quá điện ảnh nếu câu thoại đang nói về kiến thức cụ thể
- CTA cuối: một câu ngắn, tự nhiên, không nài nỉ

Lưu ý: visual_prompt PHẢI bằng tiếng Anh để tìm stock footage."""

    provider = get_active_provider()
    print(f"  🤖 Script provider: {provider}")

    if provider == "none":
        raise RuntimeError(
            "Chưa cấu hình AI provider. "
            "Thêm GEMINI_API_KEY (miễn phí tại aistudio.google.com) "
            "hoặc OPENAI_API_KEY vào file .env"
        )

    feedback = ""
    best_script: VideoScript | None = None
    best_score = -999

    for attempt in range(4):
        user_prompt = base_user_prompt + feedback
        if provider == "gemini":
            raw_text = await _generate_with_gemini(full_system_prompt, user_prompt)
        else:
            raw_text = await _generate_with_openai(full_system_prompt, user_prompt)

        try:
            raw = parse_script_json(raw_text)
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Script JSON parse failed attempt {attempt + 1}: {e}")
            feedback = (
                "\n\nBản trước KHÔNG parse được JSON hợp lệ. "
                "Hãy trả lại CHỈ MỘT JSON object hợp lệ, không markdown, không text ngoài JSON.\n"
                "Quy tắc bắt buộc:\n"
                "- Tất cả key và string phải dùng dấu nháy kép.\n"
                "- Không dùng dấu nháy kép bên trong value; nếu cần nhấn mạnh, dùng dấu nháy đơn.\n"
                "- Không có trailing comma.\n"
                "- Không xuống dòng bên trong string value.\n"
                f"Lỗi parse: {str(e)}"
            )
            continue

        script = build_video_script(raw, topic)
        script_score, reasons = score_script(script)
        print(f"  🎯 Script score attempt {attempt + 1}: {script_score} — {script.hook}")

        if script_score > best_score:
            best_score = script_score
            best_script = script

        if script_score >= 10:
            return script

        feedback = (
            "\n\nBản trước còn nhạt hoặc chưa đủ giữ chân. Viết lại toàn bộ JSON.\n"
            "Lý do cần sửa:\n- "
            + "\n- ".join(reasons or ["Kịch bản chưa có đủ mâu thuẫn, ví dụ cụ thể và payoff."])
            + "\nBản mới phải bớt giáo khoa, nhiều tình huống đời thật hơn, mỗi câu có lực kéo hơn."
        )

    if best_script:
        return best_script

    print("  ⚠️ Provider returned invalid JSON repeatedly; using fallback script")
    return build_fallback_script(topic, style)
