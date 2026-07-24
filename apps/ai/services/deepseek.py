"""
سرویس اتصال به DeepSeek API برای تحلیل هوشمند ملک.
از کتابخانه‌ی openai (سازگار با API استاندارد DeepSeek) استفاده می‌کند.
"""

import json
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DeepSeekNotConfiguredError(Exception):
    """زمانی که DEEPSEEK_API_KEY تنظیم نشده باشد"""
    pass


def _get_client():
    from openai import OpenAI

    if not settings.DEEPSEEK_API_KEY:
        raise DeepSeekNotConfiguredError(
            "کلید DEEPSEEK_API_KEY تنظیم نشده است. لطفاً آن را در فایل .env قرار دهید."
        )
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        timeout=20.0,   # ثانیه - جلوگیری از قفل شدن request/worker در صورت کندی سرویس
        max_retries=1,
    )


SYSTEM_PROMPT = """
تو یک تحلیلگر حرفه‌ای بازار املاک و مستغلات ایران هستی.
بر اساس اطلاعات ملکی که دریافت می‌کنی، یک تحلیل کامل و دقیق ارائه بده.
خروجی باید *فقط* یک JSON معتبر با ساختار زیر باشد و هیچ متن اضافه‌ای قبل یا بعد از آن ننویس:

{
  "advantages": ["مزیت ۱", "مزیت ۲", "..."],
  "disadvantages": ["نکته منفی ۱", "نکته منفی ۲", "..."],
  "investment_notes": "یک پاراگراف تحلیل سرمایه‌گذاری",
  "suggested_price_range": "بازه قیمت پیشنهادی به تومان (مثلا: ۵ تا ۵.۵ میلیارد تومان)",
  "overall_score": "عددی بین ۱ تا ۱۰ به عنوان امتیاز کلی ملک"
}
"""


def _cache_key(property_id: int) -> str:
    return f"ai_analysis:property:{property_id}"


def analyze_property(property_data: dict) -> dict:
    """
    تحلیل هوشمند یک ملک با استفاده از DeepSeek.
    نتیجه به مدت هفت روز در Redis کش می‌شود.
    """
    property_id = property_data.get("id")
    if property_id:
        cached = cache.get(_cache_key(property_id))
        if cached:
            return cached

    client = _get_client()

    user_prompt = (
        "اطلاعات ملک زیر را تحلیل کن:\n" + json.dumps(property_data, ensure_ascii=False, indent=2)
    )

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )
        raw_text = response.choices[0].message.content.strip()
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("پاسخ DeepSeek قابل تبدیل به JSON نبود: %s", raw_text)
        raise
    except Exception as exc:
        logger.exception("خطا در اتصال به DeepSeek: %s", exc)
        raise

    if property_id:
        cache.set(_cache_key(property_id), result, settings.AI_ANALYSIS_CACHE_SECONDS)

    return result
