"""
تنظیمات پایه‌ی پروژه‌ی پلتفرم املاک پارسه
این فایل بین محیط توسعه و تولید مشترک است.
"""

import os
from pathlib import Path
from datetime import timedelta

# مسیر ریشه‌ی پروژه
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------------
# امنیت
# -----------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-in-env-file")
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# مسیر پنل ادمین - برای کاهش حملات ربات‌های اسکنر، پیشنهاد می‌شود در .env تغییر داده شود
# مثال: ADMIN_URL=parseh-manage-x7k9/
ADMIN_URL = os.environ.get("ADMIN_URL", "admin/")

# -----------------------------------------------------------------------
# اپلیکیشن‌ها
# -----------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.advisor_panel",
    "apps.core",
    "apps.properties",
    "apps.team",
    "apps.contact",
    "apps.blog",
    "apps.ai",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------------------------------------------------
# دیتابیس (PostgreSQL)
# -----------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "parseh_db"),
        "USER": os.environ.get("DB_USER", "parseh_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# -----------------------------------------------------------------------
# اعتبارسنجی رمز عبور
# -----------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------
# بین‌المللی‌سازی - فارسی و راست‌چین
# -----------------------------------------------------------------------
LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------
# فایل‌های استاتیک و مدیا
# -----------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# نکته: Django 5.1 دیگر STATICFILES_STORAGE (تنظیم قدیمی) را نمی‌خواند و بی‌صدا نادیده می‌گیرد؛
# باید حتماً از STORAGES استفاده شود وگرنه whitenoise هرگز واقعاً فعال نمی‌شود.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------
# Redis / Celery
# -----------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # اگر Redis به هر دلیلی در دسترس نباشد (قطعی، تنظیم‌نشدن، محیط تست)،
            # سایت با خطا متوقف نمی‌شود؛ فقط کش نادیده گرفته می‌شود و کوئری مستقیم اجرا می‌شود
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# -----------------------------------------------------------------------
# تنظیمات هوش مصنوعی DeepSeek
# -----------------------------------------------------------------------
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
AI_ANALYSIS_CACHE_SECONDS = 60 * 60 * 24 * 7  # هفت روز

# -----------------------------------------------------------------------
# اطلاعات سایت (برای فوتر و تماس)
# -----------------------------------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "پلتفرم املاک پارسه")
SITE_PHONE = os.environ.get("SITE_PHONE", "021-00000000")
SITE_WHATSAPP = os.environ.get("SITE_WHATSAPP", "989120000000")
SITE_EMAIL = os.environ.get("SITE_EMAIL", "info@parseh-estate.ir")
SITE_ADDRESS = os.environ.get("SITE_ADDRESS", "تهران، خیابان ولیعصر")

# اعلان تلگرام برای درخواست‌های تماس جدید (اختیاری)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "accounts:login"
LOGOUT_REDIRECT_URL = "/"

# -----------------------------------------------------------------------
# سخت‌سازی کوکی‌های سشن و CSRF (در تمام محیط‌ها فعال است)
# -----------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # یک هفته

# -----------------------------------------------------------------------
# محدودیت حجم آپلود (جلوگیری از حملات DoS با فایل‌های حجیم)
# -----------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # ۱۰ مگابایت برای فرم‌ها
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # ۱۰ مگابایت برای فایل‌ها

# -----------------------------------------------------------------------
# محدودیت نرخ درخواست (Rate Limiting) - جلوگیری از اسپم و سوءاستفاده از API هوش مصنوعی
# -----------------------------------------------------------------------
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"  # از همان کش Redis استفاده می‌شود
