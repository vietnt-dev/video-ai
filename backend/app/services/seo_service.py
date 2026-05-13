"""
YouTube SEO Optimization Service.
Hỗ trợ Gemini (miễn phí) và OpenAI.
"""
import json
from app.config import settings

SEO_SYSTEM_PROMPT = """Bạn là chuyên gia SEO YouTube Shorts cho thị trường Việt Nam.
Nhiệm vụ: tạo metadata giúp video dễ được bấm, dễ hiểu, đúng nội dung và giữ uy tín kênh.

NGUYÊN TẮC SEO YOUTUBE SHORTS:
TITLE (45-70 ký tự): keyword chính trong 40 ký tự đầu, rõ lợi ích hoặc curiosity gap, tối đa 1 emoji.
DESCRIPTION (180-450 ký tự): dòng đầu nêu giá trị video, sau đó CTA tự nhiên, 3-5 hashtag liên quan, luôn có #Shorts.
TAGS (10-15 tags): mix broad (1-2 từ), niche (2-3 từ), long-tail (3-5 từ), ưu tiên tiếng Việt, thêm tiếng Anh khi hợp lý.

GIỌNG VĂN:
- Tự nhiên với người Việt, không dịch máy, không phóng đại quá mức.
- Không dùng title sai nội dung, không hứa kết quả chắc chắn.
- Với sức khỏe/tài chính/tử vi/tâm lý: tránh cam kết, tránh chẩn đoán, tránh lời khuyên nguy hiểm.

Trả về JSON:
{
  "title": "Title tiếng Việt tự nhiên ≤70 ký tự, có keyword chính",
  "description": "Description 180-450 ký tự với CTA và hashtags",
  "tags": ["tag1", "tag2", "..."],
  "hashtags": ["#hashtag1", "#hashtag2"],
  "seo_score_explanation": "Giải thích ngắn tại sao metadata này tối ưu"
}"""

AB_TITLE_PROMPT = """Tạo {count} biến thể title khác nhau cho YouTube Shorts.
Mỗi title dùng một công thức:
1. Con số + lợi ích cụ thể: "3 cách X giúp bạn Y"
2. Câu hỏi tò mò: "Vì sao nhiều người Việt hay mắc lỗi này?"
3. Nghịch lý/sự thật bất ngờ: "Điều về X nhiều người đang hiểu sai"
Title phải tự nhiên, không clickbait rỗng, tối đa 70 ký tự.
Trả về JSON: {{"titles": ["title1", "title2", "title3"]}}"""


async def _call_ai(system: str, user: str, temperature: float = 0.7) -> dict:
    """Gọi AI provider đang active (Gemini hoặc OpenAI)."""
    from app.services.gemini_service import get_active_provider

    provider = get_active_provider()

    if provider == "gemini":
        from app.services.gemini_service import gemini_generate
        raw = await gemini_generate(system, user, temperature=temperature, json_mode=True)
        return json.loads(raw)
    elif provider == "openai":
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return json.loads(resp.choices[0].message.content)
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

    raw = await _call_ai(SEO_SYSTEM_PROMPT, user_prompt, temperature=0.7)

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

    raw = await _call_ai("", AB_TITLE_PROMPT.format(count=count) + "\n\n" + user_prompt, temperature=0.9)
    return raw.get("titles", [])
