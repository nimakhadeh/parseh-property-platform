from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
from apps.team.models import TeamMember
from apps.core.validators import validate_image_file
from apps.core.image_utils import compress_image_field


class Property(models.Model):
    """مدل ملک"""

    TRANSACTION_CHOICES = [
        ("sale", "فروش"),
        ("rent", "اجاره"),
    ]

    title = models.CharField("عنوان ملک", max_length=200)
    slug = models.SlugField("اسلاگ", max_length=220, unique=True, blank=True, allow_unicode=True)
    description = models.TextField("توضیحات")
    price = models.BigIntegerField("قیمت (تومان)")
    transaction_type = models.CharField("نوع معامله", max_length=10, choices=TRANSACTION_CHOICES)

    area = models.PositiveIntegerField("متراژ (متر مربع)")
    rooms = models.PositiveSmallIntegerField("تعداد اتاق")
    floor = models.PositiveSmallIntegerField("طبقه", default=0)
    total_floors = models.PositiveSmallIntegerField("تعداد کل طبقات", default=1)
    year_built = models.PositiveIntegerField("سال ساخت", blank=True, null=True)

    has_elevator = models.BooleanField("آسانسور", default=False)
    has_parking = models.BooleanField("پارکینگ", default=False)
    has_warehouse = models.BooleanField("انباری", default=False)
    has_balcony = models.BooleanField("بالکن", default=False)

    address = models.CharField("آدرس", max_length=300)
    latitude = models.DecimalField("عرض جغرافیایی", max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField("طول جغرافیایی", max_digits=10, decimal_places=6, blank=True, null=True)

    advisor = models.ForeignKey(
        TeamMember, verbose_name="مشاور", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="properties",
    )

    image = models.ImageField("تصویر اصلی", upload_to="properties/", validators=[validate_image_file])
    image_2 = models.ImageField("تصویر دوم", upload_to="properties/", blank=True, null=True, validators=[validate_image_file])
    image_3 = models.ImageField("تصویر سوم", upload_to="properties/", blank=True, null=True, validators=[validate_image_file])
    image_4 = models.ImageField("تصویر چهارم", upload_to="properties/", blank=True, null=True, validators=[validate_image_file])

    is_published = models.BooleanField("منتشر شده", default=True)
    is_featured = models.BooleanField("ویژه", default=False)
    views_count = models.PositiveIntegerField("تعداد بازدید", default=0)

    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("تاریخ بروزرسانی", auto_now=True)

    class Meta:
        verbose_name = "ملک"
        verbose_name_plural = "املاک"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_published", "transaction_type"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["price"]),
            models.Index(fields=["-views_count"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # فشرده‌سازی خودکار تصاویر تازه‌آپلودشده (بهبود سرعت لود سایت)
        self.image = compress_image_field(self.image)
        self.image_2 = compress_image_field(self.image_2)
        self.image_3 = compress_image_field(self.image_3)
        self.image_4 = compress_image_field(self.image_4)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("properties:property_detail", kwargs={"slug": self.slug})

    @property
    def images(self):
        return [img for img in [self.image, self.image_2, self.image_3, self.image_4] if img]

    @property
    def price_display(self):
        """نمایش قیمت به صورت خوانا (میلیون / میلیارد تومان)"""
        if self.price >= 1_000_000_000:
            return f"{self.price / 1_000_000_000:.1f} میلیارد تومان"
        if self.price >= 1_000_000:
            return f"{self.price / 1_000_000:.0f} میلیون تومان"
        return f"{self.price:,} تومان"


class Favorite(models.Model):
    """علاقه‌مندی ملک به حساب کاربری (برای کاربران وارد‌شده - ماندگار و قابل دسترس از هر دستگاه)"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.CASCADE, related_name="favorites")
    property = models.ForeignKey(Property, verbose_name="ملک", on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField("تاریخ افزودن", auto_now_add=True)

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        unique_together = ["user", "property"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} ← {self.property}"


class PropertyView(models.Model):
    """تاریخچه بازدید ملک توسط کاربران وارد‌شده"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.CASCADE, related_name="viewed_properties")
    property = models.ForeignKey(Property, verbose_name="ملک", on_delete=models.CASCADE, related_name="view_history")
    viewed_at = models.DateTimeField("آخرین بازدید", auto_now=True)

    class Meta:
        verbose_name = "بازدید ملک"
        verbose_name_plural = "تاریخچه بازدید ملک‌ها"
        unique_together = ["user", "property"]
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.user} بازدید از {self.property}"


class PropertyValuationRequest(models.Model):
    """
    درخواست ارزیابی آنلاین ملک - برای مالکینی که می‌خواهند ملک خود را برای
    فروش یا اجاره به پارسه بسپارند و نیاز به کارشناسی قیمت دارند.
    """

    STATUS_CHOICES = [
        ("pending", "در انتظار بررسی"),
        ("reviewed", "بررسی شد"),
        ("contacted", "تماس گرفته شد"),
        ("rejected", "رد شد"),
    ]

    name = models.CharField("نام و نام خانوادگی مالک", max_length=150)
    phone = models.CharField("شماره تماس", max_length=20)
    email = models.EmailField("ایمیل", blank=True)

    transaction_type = models.CharField("نوع درخواست", max_length=10, choices=Property.TRANSACTION_CHOICES)
    address = models.CharField("آدرس ملک", max_length=300)
    area = models.PositiveIntegerField("متراژ (متر مربع)", blank=True, null=True)
    rooms = models.PositiveSmallIntegerField("تعداد اتاق", blank=True, null=True)
    description = models.TextField("توضیحات مالک درباره ملک", blank=True)

    image = models.ImageField("تصویر اول", upload_to="valuation_requests/", blank=True, null=True, validators=[validate_image_file])
    image_2 = models.ImageField("تصویر دوم", upload_to="valuation_requests/", blank=True, null=True, validators=[validate_image_file])
    image_3 = models.ImageField("تصویر سوم", upload_to="valuation_requests/", blank=True, null=True, validators=[validate_image_file])

    status = models.CharField("وضعیت", max_length=15, choices=STATUS_CHOICES, default="pending")
    assigned_advisor = models.ForeignKey(
        TeamMember, verbose_name="مشاور مسئول پیگیری", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="valuation_requests",
    )
    admin_notes = models.TextField("یادداشت داخلی (برای مشاوران)", blank=True)
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "درخواست ارزیابی ملک"
        verbose_name_plural = "درخواست‌های ارزیابی ملک"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ارزیابی ملک {self.name} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        self.image = compress_image_field(self.image)
        self.image_2 = compress_image_field(self.image_2)
        self.image_3 = compress_image_field(self.image_3)
        super().save(*args, **kwargs)

    @property
    def images(self):
        return [img for img in [self.image, self.image_2, self.image_3] if img]
