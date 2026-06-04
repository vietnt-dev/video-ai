"""
YouTube SEO Optimization Service.
Hỗ trợ Gemini (miễn phí) và OpenAI.
"""
import json
from app.config import settings

SEO_SYSTEM_PROMPT = """Bạn là chuyên gia SEO YouTube Shorts cho thị trường Việt Nam.
Nhiệm vụ: tạo metadata giúp video dễ được bấm, dễ hiểu, đúng nội dung và giữ uy tín kênh.

NGUYÊN TẮC SEO YOUTUBE SHORTS:
TITLE (38-70 ký tự): keyword chính trong 40 ký tự đầu, rõ lợi ích/mất mát/curiosity gap, tối đa 1 emoji.
Title phải có một trong 4 lực kéo:
1. Lỗi phổ biến: "Bạn đang dùng AI sai từ bước này"
2. Mất mát cụ thể: "Một prompt sai làm phí cả buổi"
3. Nghịch lý: "AI không thay bạn, người biết AI mới thay"
4. Câu hỏi có căng thẳng: "Vì sao học nhiều vẫn không giỏi AI?"
DESCRIPTION (180-450 ký tự): dòng đầu nêu giá trị video, sau đó CTA tự nhiên, 3-5 hashtag liên quan, luôn có #Shorts.
TAGS (10-15 tags): mix broad (1-2 từ), niche (2-3 từ), long-tail (3-5 từ), ưu tiên tiếng Việt, thêm tiếng Anh khi hợp lý.

GIỌNG VĂN:
- Tự nhiên với người Việt, không dịch máy, không phóng đại quá mức.
- Không dùng title sai nội dung, không hứa kết quả chắc chắn.
- Không dùng title nhạt kiểu "Tìm hiểu về X", "Sự thật về X" nếu không có góc cụ thể.
- Với sức khỏe/tài chính/tử vi/tâm lý: tránh cam kết, tránh chẩn đoán, tránh lời khuyên nguy hiểm.

Trả về JSON:
{
  "title": "Title tiếng Việt tự nhiên ≤70 ký tự, có keyword chính và lực kéo rõ",
  "description": "Description 180-450 ký tự với CTA và hashtags",
  "tags": ["tag1", "tag2", "..."],
  "hashtags": ["#hashtag1", "#hashtag2"],
  "seo_score_explanation": "Giải thích ngắn tại sao metadata này tối ưu"
}"""

AB_TITLE_PROMPT = """Tạo {count} biến thể title khác nhau cho YouTube Shorts.
Mỗi title dùng một công thức:
1. Lỗi phổ biến + hậu quả: "Bạn đang dùng AI sai từ bước này"
2. Mất mát cụ thể: "Một prompt sai làm phí cả buổi"
3. Nghịch lý/cú lật: "AI không thay bạn, người biết AI mới thay"
4. Câu hỏi căng thẳng: "Vì sao học nhiều vẫn không giỏi AI?"
Title phải tự nhiên, không clickbait rỗng, không dùng "Tìm hiểu về", tối đa 70 ký tự.
Trả về JSON: {{"titles": ["title1", "title2", "title3"]}}"""


async def _call_ai(system: str, user: str, temperature: float = 0.7) -> dict:
    """Gọi AI provider đang active (Gemini hoặc OpenAI)."""
    from app.services.gemini_service import get_active_provider
    from app.services.script_service import parse_script_json

    provider = get_active_provider()

    if provider == "gemini":
        from app.services.gemini_service import gemini_generate
        raw = await gemini_generate(system, user, temperature=temperature, json_mode=True)
        return parse_script_json(raw)
    elif provider == "openai":
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return parse_script_json(resp.choices[0].message.content)
    else:
        raise RuntimeError("Chưa cấu hình AI provider")


async def generate_youtube_seo(
    topic: str,
    script_hook: str,
    script_summary: str,
    keywords: list[str],
    language: str = "vi",
) -> dict:
    """Tạo metadata SEO tối ưu cho YouTube Shorts."""
    lang_note = (
        "Video bằng tiếng Việt, target: người Việt 18-35 tuổi"
        if language == "vi"
        else "Video in English, global audience"
    )

    user_prompt = f"""CHỦ ĐỀ: {topic}
{lang_note}
HOOK: "{script_hook}"
NỘI DUNG: {script_summary}
KEYWORDS: {', '.join(keywords)}

Tạo metadata SEO tối ưu. Title phải khác hook, đúng nội dung, không phóng đại."""

    try:
        raw = await _call_ai(SEO_SYSTEM_PROMPT, user_prompt, temperature=0.7)
    except Exception as e:
        print(f"⚠️ SEO metadata AI failed, using fallback: {e}")
        raw = {
            "title": topic[:70],
            "description": f"{script_hook}\n\n{script_summary[:260]}\n\n#Shorts #YouTubeShorts",
            "tags": keywords[:10],
            "hashtags": ["#Shorts", "#YouTubeShorts"],
            "seo_score_explanation": "Fallback metadata vì AI trả JSON không hợp lệ.",
        }

    title = raw.get("title", topic)[:100]
    description = raw.get("description", "")
    tags = raw.get("tags", keywords)[:15]
    hashtags = raw.get("hashtags", ["#Shorts"])

    if "#Shorts" not in description:
        description += "\n\n#Shorts #YouTubeShorts"
    if "#Shorts" not in hashtags:
        hashtags.append("#Shorts")

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "hashtags": hashtags,
        "seo_explanation": raw.get("seo_score_explanation", ""),
    }


async def generate_ab_test_titles(
    topic: str,
    script_hook: str,
    keywords: list[str],
    count: int = 3,
) -> list[str]:
    """Tạo nhiều biến thể title để A/B test."""
    user_prompt = f"""Chủ đề: "{topic}"
Hook: "{script_hook}"
Keywords: {', '.join(keywords)}
Tạo {count} biến thể title theo 3 công thức đã mô tả."""

    try:
        raw = await _call_ai("", AB_TITLE_PROMPT.format(count=count) + "\n\n" + user_prompt, temperature=0.9)
        return raw.get("titles", [])
    except Exception as e:
        print(f"⚠️ AB title AI failed, using fallback: {e}")
        return [
            topic[:70],
            f"{script_hook[:64]}",
            f"Điều ít ai để ý về {topic}"[:70],
        ][:count]
