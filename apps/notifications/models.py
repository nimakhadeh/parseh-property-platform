from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    """اعلان داخلی برای یک کاربر. زیرساخت مشترک برای همه‌ی فازهای بعدی
    (لاگ فعالیت، کارتابل وظایف، قیف فروش و ...) — به‌جای مدل اعلان جدا برای هر اپ،
    همه از طریق apps.notifications.services.notify() این مدل را پر می‌کنند."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="گیرنده",
        on_delete=models.CASCADE, related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="ایجادکننده",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="کاربری که باعث ایجاد این اعلان شده (مثلاً مدیری که وظیفه محول کرده)؛ برای اعلان‌های خودکار سیستم خالی می‌ماند.",
    )
    message = models.CharField("پیام", max_length=255)
    url = models.CharField("لینک مقصد", max_length=300, blank=True)
    is_read = models.BooleanField("خوانده‌شده", default=False)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.recipient}: {self.message[:40]}"
