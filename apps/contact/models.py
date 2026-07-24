from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator, MaxLengthValidator
from apps.properties.models import Property

phone_validator = RegexValidator(
    regex=r"^0?9\d{9}$|^0\d{10}$",
    message="شماره تماس معتبر وارد کنید (مثال: 09121234567).",
)


class ContactRequest(models.Model):
    """درخواست تماس / مشاوره از سمت کاربران"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="کاربر (در صورت ورود به حساب)", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contact_requests",
    )
    name = models.CharField("نام و نام خانوادگی", max_length=150)
    phone = models.CharField("شماره تماس", max_length=20, validators=[phone_validator])
    email = models.EmailField("ایمیل", blank=True)
    message = models.TextField("پیام", validators=[MaxLengthValidator(2000)])
    property = models.ForeignKey(
        Property, verbose_name="ملک مرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contact_requests",
    )
    is_read = models.BooleanField("خوانده شده", default=False)
    created_at = models.DateTimeField("تاریخ ارسال", auto_now_add=True)

    class Meta:
        verbose_name = "درخواست تماس"
        verbose_name_plural = "درخواست‌های تماس"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at:%Y-%m-%d}"
