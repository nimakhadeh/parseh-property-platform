from django.db import models
from django.conf import settings
from apps.core.validators import validate_image_file
from apps.core.image_utils import compress_image_field


class TeamMember(models.Model):
    """مدل مشاور / عضو تیم"""

    ROLE_CHOICES = [
        ("manager", "مدیر مجموعه"),
        ("investment", "مشاور سرمایه‌گذاری"),
        ("rent", "مشاور اجاره"),
        ("sale", "مشاور فروش"),
        ("legal", "مشاور حقوقی"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="حساب کاربری مرتبط",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="team_member",
        help_text="در صورت اتصال، این مشاور می‌تواند وارد پنل مدیریت مشاوران شود.",
    )
    name = models.CharField("نام و نام خانوادگی", max_length=150)
    role = models.CharField("سمت", max_length=20, choices=ROLE_CHOICES, default="sale")
    bio = models.TextField("بیوگرافی", blank=True)
    image = models.ImageField("تصویر", upload_to="team/", blank=True, null=True, validators=[validate_image_file])
    phone = models.CharField("شماره تماس", max_length=20, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    order = models.PositiveIntegerField("ترتیب نمایش", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "مشاور"
        verbose_name_plural = "مشاوران"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        self.image = compress_image_field(self.image)
        super().save(*args, **kwargs)
