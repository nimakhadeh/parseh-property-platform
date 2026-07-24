"""
تنظیمات تست محلی سریع با SQLite (بدون نیاز به PostgreSQL/PostGIS)
فقط برای تست اولیه روی لپ‌تاپ - در تولید استفاده نشود.
"""
from .development import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
