"""
فشرده‌سازی خودکار تصاویر آپلودی برای بهبود سرعت لود سایت.
عکس‌های موبایل امروزه اغلب ۳ تا ۸ مگابایت هستند؛ این ابزار آن‌ها را قبل از
ذخیره در دیسک/فضای ابری، به حداکثر ۱۶۰۰ پیکسل عرض و کیفیت ۸۲٪ کاهش می‌دهد.
"""
import sys
import logging
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile

logger = logging.getLogger(__name__)

MAX_DIMENSION = 1600
JPEG_QUALITY = 82


def compress_image_field(image_field, max_dimension=MAX_DIMENSION, quality=JPEG_QUALITY):
    """
    اگر مقدار این فیلد یک فایل تازه‌آپلودشده باشد (نه فایل از قبل ذخیره‌شده در storage)،
    آن را فشرده کرده و یک InMemoryUploadedFile جدید برمی‌گرداند تا به‌جای فایل اصلی ذخیره شود.
    اگر فیلد خالی باشد یا فشرده‌سازی با خطا مواجه شود، مقدار اصلی بدون تغییر برگردانده می‌شود.
    """
    if not image_field or not hasattr(image_field, "file"):
        return image_field

    # اگر فایل قبلاً در storage ذخیره شده (ویرایش رکورد بدون تغییر عکس)، برای جلوگیری از
    # باز کردن غیرضروری فایل از دیسک، همان مقدار را بدون پردازش برمی‌گردانیم
    if getattr(image_field, "_committed", True):
        return image_field

    # فقط فایل‌های تازه‌آپلودشده پردازش می‌شوند؛ فایل‌های از قبل ذخیره‌شده دوباره فشرده نمی‌شوند
    # (وگرنه با هر بار save() مدل، کیفیت عکس به‌تدریج افت می‌کرد)
    if not isinstance(image_field.file, UploadedFile):
        return image_field

    try:
        img = Image.open(image_field)
        img_format = (img.format or "JPEG").upper()
        original_name = image_field.name

        if img.mode in ("RGBA", "P") and img_format == "JPEG":
            img = img.convert("RGB")

        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        buffer = BytesIO()
        save_kwargs = {"optimize": True}
        if img_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
        img.save(buffer, format=img_format, **save_kwargs)
        buffer.seek(0)

        return InMemoryUploadedFile(
            buffer, "ImageField", original_name, f"image/{img_format.lower()}",
            sys.getsizeof(buffer), None,
        )
    except Exception as exc:
        logger.warning("فشرده‌سازی تصویر ناموفق بود، فایل اصلی ذخیره می‌شود: %s", exc)
        return image_field
