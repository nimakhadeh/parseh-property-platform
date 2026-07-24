"""اعتبارسنج‌های مشترک برای استفاده در چند اپ (محدودیت آپلود تصویر)"""
from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def validate_image_file(file):
    """
    بررسی می‌کند که فایل آپلودشده:
    ۱) از نوع مجاز باشد (jpg, jpeg, png, webp)
    ۲) حجمش بیشتر از ۵ مگابایت نباشد
    این جلوی آپلود فایل‌های غیرتصویری (مثل اسکریپت مخرب با پسوند جعلی) و
    فایل‌های حجیم که می‌توانند فضای دیسک سرور را پر کنند را می‌گیرد.
    """
    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"فرمت فایل مجاز نیست. فرمت‌های مجاز: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(f"حجم فایل نباید بیشتر از {MAX_IMAGE_SIZE_MB} مگابایت باشد.")
