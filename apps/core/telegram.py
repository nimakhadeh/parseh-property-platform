"""
سرویس پایه‌ی ارسال پیام به تلگرام - مشترک بین اپ‌های مختلف پروژه (contact، properties و ...).
اختیاری است: فقط وقتی TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID در .env تنظیم شده باشند فعال می‌شود.

راهنمای ساخت ربات:
۱. در تلگرام به @BotFather پیام دهید و با /newbot یک ربات بسازید تا توکن بگیرید.
۲. ربات را استارت کنید و chat_id خودتان را از @userinfobot بگیرید.
۳. مقادیر را در .env قرار دهید: TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text):
    """
    ارسال یک پیام متنی به تلگرام مدیر سایت.
    این تابع هرگز نباید باعث خطا در فرآیند اصلی درخواست شود؛ خطاها فقط لاگ می‌شوند.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        return  # سرویس تلگرام تنظیم نشده؛ به‌سادگی رد می‌شویم

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
        if response.status_code != 200:
            logger.warning("ارسال اعلان تلگرام ناموفق بود: %s", response.text)
    except requests.RequestException as exc:
        logger.warning("خطا در اتصال به API تلگرام: %s", exc)
