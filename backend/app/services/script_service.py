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
- Hook phải vào thẳng vấn đề ngay từ giây đầu tiên bằng một câu giật gân, mất mát rõ ràng hoặc mâu thuẫn lớn, tuyệt đối không dẫn nhập, không giới thiệu.
- Ngay sau hook phải có OPEN LOOP: hé lộ một cú lật sẽ được giải thích ở gần cuối video, không giải thích hết ngay.
- Video phải có một "đường dây căng": pattern interrupt → vấn đề cụ thể → ví dụ đời thật → cú lật bất ngờ → payoff/hành động thực tế.
- Mỗi segment phải làm người xem tò mò muốn nghe câu tiếp theo, tuyệt đối không liệt kê kiến thức khô khan đều đều kiểu sách giáo khoa.
- Mỗi segment phải có ít nhất một trong các yếu tố: mâu thuẫn trái chiều, ví dụ cụ thể sát sườn, con số thực tế đời thường, hoặc câu lật ngược kỳ vọng.
- Ưu tiên ví dụ rất cụ thể của người Việt: lương 5 triệu, tiền nhà, hóa đơn điện nước, đi trễ bị phạt, sếp dí deadline, lướt điện thoại 2h sáng, nhịn ăn sáng.
- Ưu tiên một "big idea" hẹp và sắc, không giải thích toàn bộ chủ đề.
- Phải có ít nhất một câu kiểu "à ra vậy" làm payoff ở nửa sau video.
- Nghiêm cấm viết kiểu sách giáo khoa/dịch thuật: "đó chính là", "lý do là", "tóm lại", "đầu tiên", "tiếp theo", "ngoài ra", "chúng ta cần phải", "sau đây".
- Nghiêm cấm dùng các câu sáo rỗng: "Trong video này", "Hãy cùng khám phá", "Bạn có biết rằng", "bí mật tuyệt vời", "hành trình".
- Nghiêm cấm hook generic kiểu: "Bạn tưởng X đơn giản?", "Sự thật về X", "Đừng bỏ qua điều này" nếu không có chi tiết cụ thể.
- Không dùng giọng dịch máy, không dùng từ Hán-Việt nặng nề nếu có từ thuần Việt phổ thông hơn.
- Không nhồi emoji trong narration. Emoji chỉ dùng trong title nếu cần.
- Mỗi segment phải tạo được slide content như motion graphic punchline, KHÔNG như slide thuyết trình; mỗi dòng slide tối đa 3-4 từ.
- Nếu chủ đề thuộc sức khỏe, tài chính, tử vi hoặc tâm lý: tránh cam kết chắc chắn, tránh chẩn đoán, tránh hứa kết quả.
- Visual phải là cảnh quay cụ thể bám sát đúng câu thoại, không dùng cảnh chung chung như landscape, people walking, abstract background.
- Visual_prompt phải bắt đầu bằng chủ thể chính có thể tìm thấy trên stock footage, không bắt đầu bằng động từ mơ hồ như visualizing, showing, representing.
- Visual_prompt nên có hình ảnh đối lập hoặc metaphor bất ngờ khi phù hợp, ví dụ: "student deleting notes after AI answer", "office worker comparing two phone screens".

Trả về JSON theo đúng format sau, KHÔNG thêm bất kỳ text nào khác:
{
  "hook": "Câu hook 1-3 giây đầu — cụ thể, có nghịch lý/mất mát/lợi ích rõ, không generic",
  "segments": [
    {
      "text": "Nội dung đọc — tiếng Việt tự nhiên, như lời nói, câu ngắn 5-10 từ, có lực kéo sang câu sau",
      "visual_prompt": "Specific English description for Pexels/Imagen stock footage search",
      "duration": 4.5,
      "slide": {
        "layout": "title | compare | list | card | big_number | one_word | wrong_right | myth_fact | timeline | receipt | comment_cta | motion_tech",
        "title": "TIÊU ĐỀ SLIDE (in hoa, max 3 từ)",
        "content": ["Punchline max 3-4 từ", "Punchline max 3-4 từ"]
      }
    }
  ],
  "call_to_action": "CTA cuối video — kích thích bình luận/chia sẻ, không xin follow lộ liễu",
  "total_duration": 32.0,
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "suggested_title": "Tiêu đề YouTube SEO ≤70 ký tự, có curiosity gap, có keyword chính",
  "suggested_description": "Mô tả 2-3 câu, có hashtag trending"
}"""

RETENTION_SCRIPT_PROMPT = """
CẤU TRÚC GIỮ CHÂN BẮT BUỘC:
1. Hook: Một câu khiến người xem dừng lướt trong 1.5 giây, có mất mát/lợi ích/nghịch lý cụ thể.
2. Segment 1: Pattern interrupt + open loop. Nói điều trái với niềm tin phổ biến, nhưng chưa giải thích hết.
3. Segment 2: Một tình huống đời thật cực cụ thể tại Việt Nam (lương, deadline, điện thoại, lớp học, hóa đơn, sếp, gia đình).
4. Segment 3: Chỉ ra lỗi gốc hoặc cơ chế ẩn sau. Đây phải là câu "à ra vậy", không phải lời khuyên chung chung.
5. Segment 4: Cú lật/payoff. Đóng open loop bằng một insight ngắn, sắc, dễ nhớ.
6. Segment 5: Hành động nhỏ làm được ngay hôm nay, càng cụ thể càng tốt.
7. CTA: Câu chốt kích thích comment/share/save. Không dùng "hãy follow", "đăng ký kênh".

NHỊP KỂ:
- Mỗi segment chỉ gồm 1 câu thoại đắt giá, hoặc tối đa 2 câu siêu ngắn.
- Tuyệt đối không dùng giọng giáo điều dạy đời. Hãy đóng vai một người bạn ranh ma đang chỉ ra góc khuất mà họ chưa từng nghĩ tới.
- Giữ sự tò mò xuyên suốt: câu trước phải làm bàn đạp để câu sau nổ ra, không được kết thúc ý quá sớm.
- Tổng thời lượng video khoảng 25-35 giây (70-110 từ). Chỉ tập trung vào một luận điểm duy nhất, không lan man giải thích nhiều.
- Mỗi 6-8 giây phải có một pattern interrupt: "nhưng", "cú lật", "nghe vô lý", "vấn đề thật là", "đây mới là phần nguy hiểm".
- Slide text phải hoạt động như punchline, không phải transcript.
"""


WEAK_HOOK_PHRASES = {
    "trong video này",
    "hãy cùng",
    "bạn có biết",
    "cùng khám phá",
    "bí mật tuyệt vời",
    "hành trình",
    "bạn tưởng",
    "đơn giản",
    "đừng bỏ qua",
    "sự thật về",
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
    "cú lật",
    "nghe vô lý",
    "nguy hiểm",
    "mất",
    "thay vì",
    "đổi lại",
}

CTA_MARKERS = {
    "comment",
    "bình luận",
    "gửi",
    "share",
    "lưu",
    "save",
    "phần 2",
    "đồng ý",
}


def score_hook(hook: str) -> tuple[int, list[str]]:
    """Chấm hook theo các tín hiệu giữ chân người xem Shorts."""
    normalized = re.sub(r"\s+", " ", hook or "").strip().lower()
    words = normalized.split()
    score = 0
    reasons: list[str] = []

    if 4 <= len(words) <= 12:
        score += 2
    else:
        reasons.append("Hook nên dài 4-12 từ, đọc xong trong 1-2 giây.")

    if any(char.isdigit() for char in normalized):
        score += 1

    if any(marker in normalized for marker in ("?", "vì sao", "tại sao", "sự thật", "lý do", "sai lầm", "đừng", "mất", "nguy hiểm", "sai", "không phải")):
        score += 2
    else:
        reasons.append("Hook thiếu mất mát, curiosity gap hoặc nghịch lý.")

    if any(phrase in normalized for phrase in WEAK_HOOK_PHRASES):
        score -= 3
        reasons.append("Hook có cụm mở bài sáo rỗng/generic.")

    if any(word in normalized for word in ("ai", "tiền", "lương", "sếp", "deadline", "điện thoại", "học", "prompt", "não", "google", "mật khẩu", "dữ liệu")):
        score += 1
    else:
        reasons.append("Hook thiếu chi tiết cụ thể khiến người xem thấy liên quan ngay.")

    if normalized.startswith(("bạn tưởng", "sự thật về", "đừng bỏ qua")):
        score -= 2
        reasons.append("Hook mở bằng template quá quen, dễ bị lướt qua.")

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

    if 70 <= word_count <= 110:
        score += 2
    else:
        reasons.append("Kịch bản nên khoảng 70-110 từ để giữ nhịp 25-35 giây.")

    marker_hits = sum(1 for marker in RETENTION_MARKERS if marker in body)
    if marker_hits >= 4:
        score += 3
    else:
        reasons.append("Thiếu open loop, pattern interrupt, cú lật hoặc tín hiệu kéo người xem nghe tiếp.")

    if any(char.isdigit() for char in body):
        score += 1
    else:
        reasons.append("Nên có ít nhất một con số đời thường hoặc mốc cụ thể.")

    if any(word in body for word in ("lương", "tiền", "hóa đơn", "điện thoại", "cơm", "ngủ", "sếp", "mẹ", "chợ", "cà phê")):
        score += 2
    else:
        reasons.append("Thiếu ví dụ đời sống Việt Nam đủ cụ thể.")

    if any(marker in body for marker in ("cú lật", "nghe vô lý", "đây mới là", "vấn đề thật", "phần nguy hiểm", "không phải")):
        score += 2
    else:
        reasons.append("Thiếu câu payoff/cú lật đủ sắc ở nửa sau video.")

    cta = (script.call_to_action or "").lower()
    if any(marker in cta for marker in CTA_MARKERS):
        score += 1
    else:
        reasons.append("CTA chưa kích comment/share/save rõ ràng.")

    slide_lines = []
    for seg in script.segments:
        if seg.slide:
            slide_lines.append(seg.slide.title)
            slide_lines.extend(seg.slide.content)
    long_slide_lines = [line for line in slide_lines if len(line.split()) > 6]
    if long_slide_lines:
        score -= 2
        reasons.append("Slide text có dòng quá 6 từ, nên biến thành punchline ngắn 3-5 từ.")

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
        hook=f"Cách bạn làm {topic} đang phí thời gian.",
        segments=[
            ScriptSegment(
                text="Nghe vô lý, nhưng lỗi không nằm ở cố gắng.",
                visual_prompt="Vietnamese person frustrated at phone and notebook, close up",
                duration=4.5,
                slide=SlideContent(layout="title", title="SAI TỪ ĐẦU", content=["Lỗi không nằm ở cố gắng"])
            ),
            ScriptSegment(
                text="Ví dụ, bạn làm 2 tiếng nhưng vẫn quay lại điểm cũ.",
                visual_prompt="Vietnamese office worker checking clock and messy desk",
                duration=5.0,
                slide=SlideContent(layout="card", title="2 TIẾNG", content=["Vẫn quay lại điểm cũ"])
            ),
            ScriptSegment(
                text="Vấn đề thật là bạn đang sửa phần ít quan trọng nhất.",
                visual_prompt="Vietnamese person highlighting wrong line on paper, close up",
                duration=5.0,
                slide=SlideContent(layout="compare", title="VẤN ĐỀ", content=["Sửa phần phụ", "Bỏ phần chính"])
            ),
            ScriptSegment(
                text="Cú lật là đổi câu hỏi trước, rồi mới đổi cách làm.",
                visual_prompt="Vietnamese person rewriting question on notebook, morning light",
                duration=5.0,
                slide=SlideContent(layout="card", title="CÚ LẬT", content=["Đổi câu hỏi trước"])
            ),
            ScriptSegment(
                text="Hôm nay, viết lại một câu hỏi trong 5 phút.",
                visual_prompt="Phone timer five minutes, Vietnamese person writing focused question",
                duration=4.5,
                slide=SlideContent(layout="comment_cta", title="MUỐN VÍ DỤ?", content=["COMMENT 'PROMPT'", "Tôi làm phần 2"])
            ),
        ],
        call_to_action="Bạn muốn phần 2 với ví dụ cụ thể không?",
        total_duration=31.0,
        keywords=[topic, style, "shorts", "viral", "Việt Nam"],
        suggested_title=f"{topic}: Lỗi nhỏ khiến bạn phí thời gian",
        suggested_description=f"Một cú lật ngắn giúp bạn nhìn lại cách làm {topic}. #shorts #viral",
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
QUY TẮC BẮT BUỘC CHO MOTION SHORT DẠNG TEXT/VISUAL BEAT (Mỗi segment phải chứa thêm trường "slide"):
- Hệ thống sẽ animate từng slide theo beat: label vào trước, keyword/punchline bật sau, item/card xuất hiện tuần tự.
- Vì vậy slide text phải là vật thể motion, KHÔNG phải nội dung trình chiếu để đọc.
- "slide" object gồm:
  1. "layout": chọn một trong:
     - "title": mở đầu/pattern interrupt.
     - "big_number": khi có số, tiền, %, thời gian, thống kê.
     - "one_word": khi cần nhấn 1 keyword cực mạnh như "SAI", "AI", "CÚ LẬT".
     - "wrong_right": khi có so sánh sai/đúng, cũ/mới.
     - "myth_fact": khi có hiểu lầm vs sự thật.
     - "timeline": khi có 3 mốc ngắn theo thời gian/quy trình.
     - "receipt": khi nội dung giống bill, chat, note, checklist đời thật.
     - "motion_tech": khi cần visual giống tech short cao cấp: headline lớn + badge + proof/terminal/stat + CTA.
     - "compare": khi cần so sánh 2 ý ngang nhau.
     - "list": khi có 2-3 hành động ngắn.
     - "card": khi có một insight/payoff.
     - "comment_cta": slide cuối kích bình luận.
  2. "title": Tiêu đề cực ngắn của slide (in hoa, viết gọn, max 3 từ, ví dụ: "SAI TỪ ĐẦU", "CÚ LẬT").
  3. "content": Mảng chứa punchline hiển thị trên slide, KHÔNG chép lại nguyên câu voice.
     Mỗi dòng tối đa 3-4 từ. Càng ít chữ càng tốt.
     Slide phải giống một frame viral TikTok/tech short: 1 keyword lớn, 1 cú lật, 1 bằng chứng, hoặc 1 câu chốt.
     Tránh mọi câu có cấu trúc bài trình bày như "lý do", "đầu tiên", "tiếp theo", "tóm lại".
     - Với layout "big_number": content[0] là số/keyword lớn, content[1] là giải thích cực ngắn nếu cần.
     - Với layout "one_word": content[0] là 1-3 từ cực mạnh, content[1] là dòng phụ nếu cần.
     - Với layout "wrong_right": content bắt buộc có đúng 2 phần tử dạng ["Sai/Cũ", "Đúng/Mới"].
     - Với layout "myth_fact": content bắt buộc có đúng 2 phần tử dạng ["Tưởng...", "Thật ra..."].
     - Với layout "timeline": content có đúng 3 phần tử, mỗi phần tử max 4 từ.
     - Với layout "receipt": content có 2-4 dòng cực ngắn giống hóa đơn/chat/note.
       Nếu chủ đề AI/công nghệ/code, dùng content giống terminal, browser result hoặc UI proof.
       Ví dụ: ["$ hỏi AI", "> đáp án nhanh", "> nhưng hiểu sai"].
     - Với layout "motion_tech": content có 4-6 phần tử theo thứ tự:
       [headline lớn, keyword cam, repo/stat/license badges, terminal command, insight/subtitle, CTA save]
       Ví dụ: ["AI TOOL", "Miễn phí", "Local-first · Nhanh · Riêng tư", "$ pnpm run web", "dữ liệu không gửi đi đâu", "Lưu video lại"]
     - Với layout "compare": mảng bắt buộc có đúng 2 phần tử dạng ["Ý Cũ/Sai", "Ý Mới/Đúng"]. Ví dụ: ["Tự gõ phím mất 2h", "AI viết trong 10s"].
     - Với layout "list": mảng chứa từ 2 đến 3 phần tử đại diện cho các gạch đầu dòng. Ví dụ: ["Đưa vai trò", "Nêu mục tiêu", "Giới hạn thời gian"].
     - Với layout "comment_cta": content[0] là CTA nhìn thấy trên màn hình, ví dụ: ["COMMENT 'PROMPT'"].
     - Với layout "title" hoặc "card": mảng chứa 1 phần tử đại diện cho thông tin nổi bật.
- Slide đầu tiên phải là cold open/pattern interrupt, ưu tiên "one_word", "big_number" hoặc "myth_fact"; không dùng title giới thiệu chung.
- Slide giữa video nên dùng "one_word", "big_number", "receipt" hoặc "myth_fact" cho cú lật/payoff.
- Slide cuối nên dùng "comment_cta" hoặc "list" để gợi bình luận/hành động ngay.
- Không tạo slide giống PowerPoint: không headline dài, không bullet dài, không quote dài, không giải thích đủ câu.
- Ưu tiên layout dễ animate:
  - Hook: "one_word", "big_number", "myth_fact".
  - Ví dụ đời thật/proof: "receipt" hoặc "timeline".
  - Cú lật: "one_word", "myth_fact", "wrong_right".
  - Hành động/CTA: "comment_cta".
- Với chủ đề AI, công nghệ, học tập, năng suất: ít nhất 1 segment nên dùng "receipt" để tạo cảm giác UI/proof, không chỉ text nói suông.
- Với style Motion Tech hoặc chủ đề AI/công nghệ/tool/workflow: slide hook và ít nhất 2 segment nên dùng "motion_tech".
"""

    base_user_prompt = f"""Chủ đề: {topic}
Phong cách: {style_config.get('label', style)}
{lang_note}
{slide_instruction}

Tạo kịch bản video ngắn 25-35 giây với:
- Trước khi viết, tự chọn 1 BIG IDEA duy nhất nhưng KHÔNG đưa vào JSON:
  1 niềm tin sai phổ biến + 1 hậu quả cụ thể + 1 cú lật khó đoán + 1 hành động nhỏ.
  Nếu big idea nghe chung chung, hãy tự viết lại cho sắc hơn.
- Hook 1-3 giây đầu: một câu cụ thể, mạnh, có mất mát/lợi ích/nghịch lý; không dùng template generic
- 5 đoạn nội dung chính theo đúng cấu trúc: open loop → ví dụ đời thật → lỗi gốc/cơ chế ẩn → cú lật/payoff → hành động nhỏ
- Mỗi đoạn 3.5-4.5 giây, 1 câu rất gọn; không đoạn nào dài quá 2 câu
- Tổng nội dung nên 70-110 từ nhưng phải dày thông tin, không câu đệm
- Mỗi đoạn phải có lực kéo riêng, không được chỉ liệt kê thông tin đúng
- Ít nhất 2 đoạn phải có ví dụ đời sống Việt Nam thật cụ thể
- Ít nhất 1 đoạn phải có con số hoặc mốc thời gian đời thường
- Ít nhất 1 đoạn phải có pattern interrupt rõ: "nghe vô lý", "cú lật", "vấn đề thật là", "đây mới là phần nguy hiểm"
- Phải có một câu payoff làm người xem nghĩ "à ra vậy"
- Visual prompts bằng tiếng Anh, mỗi prompt là một cảnh quay cụ thể 8-14 từ, ưu tiên vật/người/hành động có thể thấy rõ
- Mỗi visual_prompt phải chứa 2-4 keyword tìm stock video sát nghĩa, ví dụ: "Vietnamese office worker checking bills, worried face, close up"
- Tránh visual_prompt trừu tượng hoặc quá điện ảnh nếu câu thoại đang nói về kiến thức cụ thể; ưu tiên hình ảnh đối lập hoặc metaphor bất ngờ
- CTA cuối: một câu ngắn, tự nhiên, kích comment/share/save; không nài nỉ follow

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
            + "\nBản mới phải bớt giáo khoa, có open loop rõ hơn, ví dụ đời thật hơn, cú lật sắc hơn và CTA kích bình luận hơn."
        )

    if best_script:
        return best_script

    print("  ⚠️ Provider returned invalid JSON repeatedly; using fallback script")
    return build_fallback_script(topic, style)
