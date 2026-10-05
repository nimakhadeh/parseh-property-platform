"""تنظیمات محیط تولید (Production) - برای اجرا روی سرور با Nginx + Gunicorn"""
import os
from .base import *  # noqa

DEBUG = False

# ALLOWED_HOSTS باید حتماً در .env تنظیم شود
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise Exception("لطفاً متغیر ALLOWED_HOSTS را در فایل .env تنظیم کنید.")

# -----------------------------------------------------------------------
# امنیت تولید
# -----------------------------------------------------------------------
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
CSRF_COOKIE_SECURE = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# HSTS فقط زمانی فعال می‌شود که SSL روشن باشد (وگرنه سایت بدون SSL غیرقابل‌دسترس می‌شود)
if SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # ۳۰ روز، بعد از اطمینان از پایداری SSL می‌توان افزایش داد
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# -----------------------------------------------------------------------
# ایمیل تولید (اختیاری - SMTP)
# -----------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# -----------------------------------------------------------------------
# لاگ‌ها (فایل چرخشی؛ حداکثر ۵ مگابایت در هر فایل، ۵ نسخه پشتیبان)
# -----------------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file_django": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django-error.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "level": "ERROR",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file_django"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["file_error", "console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
