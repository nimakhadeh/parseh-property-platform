from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^0?9\d{9}$|^0\d{10}$",
    message="شماره تماس معتبر وارد کنید (مثال: 09121234567).",
)


class Profile(models.Model):
    """اطلاعات تکمیلی کاربر (کنار مدل پیش‌فرض User جنگو)"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("شماره تماس", max_length=20, blank=True, validators=[phone_validator])
    created_at = models.DateTimeField("تاریخ عضویت", auto_now_add=True)

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

    def __str__(self):
        return f"پروفایل {self.user.username}"
