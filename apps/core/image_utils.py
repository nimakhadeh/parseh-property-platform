"""
فشرده‌سازی خودکار تصاویر آپلودی برای بهبود سرعت لود سایت.
عکس‌های موبایل امروزه اغلب ۳ تا ۸ مگابایت هستند؛ این ابزار آن‌ها را قبل از
ذخیره در دیسک/فضای ابری، به حداکثر ۱۶۰۰ پیکسل عرض و فرمت WebP (کیفیت ۸۲٪) تبدیل می‌کند.
WebP در همان کیفیت بصری معمولاً ۲۵-۳۵٪ کوچک‌تر از JPEG است و شفافیت (RGBA) را هم پشتیبانی می‌کند.
"""
import sys
import logging
from io import BytesIO
from pathlib import PurePosixPath
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile

logger = logging.getLogger(__name__)

MAX_DIMENSION = 1600
WEBP_QUALITY = 82


def compress_image_field(image_field, max_dimension=MAX_DIMENSION, quality=WEBP_QUALITY):
    """
    اگر مقدار این فیلد یک فایل تازه‌آپلودشده باشد (نه فایل از قبل ذخیره‌شده در storage)،
    آن را به WebP تبدیل و فشرده کرده و یک InMemoryUploadedFile جدید برمی‌گرداند تا
    به‌جای فایل اصلی ذخیره شود. اگر فیلد خالی باشد یا فشرده‌سازی با خطا مواجه شود،
    مقدار اصلی بدون تغییر برگردانده می‌شود.
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
        original_name = image_field.name

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "transparency" in img.info or img.mode == "P" else "RGB")

        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality, method=6)
        buffer.seek(0)

        webp_name = f"{PurePosixPath(original_name).stem}.webp"
        return InMemoryUploadedFile(
            buffer, "ImageField", webp_name, "image/webp",
            sys.getsizeof(buffer), None,
        )
    except Exception as exc:
        logger.warning("فشرده‌سازی تصویر ناموفق بود، فایل اصلی ذخیره می‌شود: %s", exc)
        return image_field
