from django.conf import settings
from django.db import models

from apps.contact.models import phone_validator
from apps.core.validators import validate_document_file
from apps.properties.models import Property
from apps.team.models import TeamMember


class ActivityLog(models.Model):
    """لاگ فعالیت مشاور: هر تعامل (کارشناسی/بازدید/سرویس/تماس/جلسه) که مشاور با یک
    مشتری یا روی یک ملک انجام می‌دهد یا برنامه‌ریزی می‌کند. رکوردهای دارای scheduled_at
    هم برای یادآوری خودکار (apps.crm.tasks) و هم برای فاز تقویم/نقشه‌ی امروز استفاده می‌شوند."""

    ACTIVITY_TYPES = [
        ("consultation", "کارشناسی"),
        ("visit", "بازدید"),
        ("service", "سرویس"),
        ("call", "تماس"),
        ("meeting", "جلسه"),
    ]

    advisor = models.ForeignKey(
        TeamMember, verbose_name="مشاور", on_delete=models.CASCADE, related_name="activity_logs",
    )
    activity_type = models.CharField("نوع فعالیت", max_length=20, choices=ACTIVITY_TYPES)
    property = models.ForeignKey(
        Property, verbose_name="ملک مرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="activity_logs",
    )
    customer_name = models.CharField("نام مشتری", max_length=150, blank=True)
    customer_phone = models.CharField("شماره تماس مشتری", max_length=20, blank=True, validators=[phone_validator])
    note = models.TextField("یادداشت", blank=True)
    scheduled_at = models.DateTimeField("زمان برنامه‌ریزی‌شده", null=True, blank=True)
    is_done = models.BooleanField("انجام‌شده", default=False)
    reminder_sent = models.BooleanField("یادآوری ارسال‌شده", default=False)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "لاگ فعالیت"
        verbose_name_plural = "لاگ فعالیت‌ها"
        ordering = ["-scheduled_at", "-created_at"]
        indexes = [
            models.Index(fields=["advisor", "-created_at"]),
            models.Index(fields=["reminder_sent", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.advisor.name}"


class Task(models.Model):
    """کارتابل وظایف: مدیر مجموعه به یک مشاور کار محول می‌کند و پیشرفتش را پیگیری می‌کند."""

    STATUS_CHOICES = [
        ("pending", "در انتظار"),
        ("in_progress", "در حال انجام"),
        ("done", "انجام‌شده"),
        ("cancelled", "لغوشده"),
    ]

    title = models.CharField("عنوان", max_length=200)
    description = models.TextField("توضیحات", blank=True)
    assignee = models.ForeignKey(
        TeamMember, verbose_name="محول‌شده به", on_delete=models.CASCADE, related_name="tasks_assigned",
    )
    assigner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="محول‌کننده",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    property = models.ForeignKey(
        Property, verbose_name="ملک مرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks",
    )
    status = models.CharField("وضعیت", max_length=20, choices=STATUS_CHOICES, default="pending")
    due_date = models.DateTimeField("مهلت انجام", null=True, blank=True)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    completed_at = models.DateTimeField("زمان انجام", null=True, blank=True)

    class Meta:
        verbose_name = "وظیفه"
        verbose_name_plural = "وظایف"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assignee", "status"]),
        ]

    def __str__(self):
        return f"{self.title} → {self.assignee.name}"


class Customer(models.Model):
    """پرونده‌ی یکپارچه‌ی مشتری، بر اساس شماره تلفن (کلید طبیعی و یکتا).
    به‌صورت خودکار هنگام ثبت ContactRequest/PropertyValuationRequest/ActivityLog
    (با شماره تلفن) ساخته می‌شود — به apps.crm.signals مراجعه کنید."""

    phone = models.CharField("شماره تماس", max_length=20, unique=True, validators=[phone_validator])
    name = models.CharField("نام", max_length=150, blank=True)
    created_at = models.DateTimeField("اولین تماس", auto_now_add=True)

    class Meta:
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.phone

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("advisor_panel:customer_profile", args=[self.phone])

    def contact_requests(self):
        from apps.contact.models import ContactRequest
        return ContactRequest.objects.filter(phone=self.phone).select_related("property").order_by("-created_at")

    def valuation_requests(self):
        from apps.properties.models import PropertyValuationRequest
        return PropertyValuationRequest.objects.filter(phone=self.phone).order_by("-created_at")

    def activity_logs(self):
        return ActivityLog.objects.filter(customer_phone=self.phone).select_related("advisor", "property").order_by("-created_at")


class Deal(models.Model):
    """یک فرصت فروش/اجاره در قیف فروش (Kanban)."""

    STAGE_CHOICES = [
        ("new", "لید جدید"),
        ("contacted", "تماس گرفته شد"),
        ("viewing", "بازدید"),
        ("negotiation", "مذاکره"),
        ("contract", "قرارداد"),
        ("won", "موفق"),
        ("lost", "ناموفق"),
    ]

    title = models.CharField("عنوان", max_length=200)
    customer = models.ForeignKey(Customer, verbose_name="مشتری", on_delete=models.CASCADE, related_name="deals")
    property = models.ForeignKey(
        Property, verbose_name="ملک مرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="deals",
    )
    advisor = models.ForeignKey(TeamMember, verbose_name="مشاور مسئول", on_delete=models.CASCADE, related_name="deals")
    stage = models.CharField("مرحله", max_length=20, choices=STAGE_CHOICES, default="new")
    value = models.PositiveBigIntegerField("ارزش تخمینی معامله (تومان)", null=True, blank=True)
    note = models.TextField("یادداشت", blank=True)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "فرصت فروش"
        verbose_name_plural = "قیف فروش"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["advisor", "stage"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_stage_display()})"


class Document(models.Model):
    """سند مربوط به پرونده‌ی یک مشتری (قرارداد، وکالت‌نامه، سند مالکیت، مدرک شناسایی، ...).
    اگر expiry_date داشته باشد، apps.crm.tasks.send_document_expiry_reminders هفت روز
    قبل از انقضا به مشاور آپلودکننده یادآوری می‌فرستد."""

    DOCUMENT_TYPES = [
        ("contract", "قرارداد"),
        ("power_of_attorney", "وکالت‌نامه"),
        ("ownership_deed", "سند مالکیت"),
        ("id_card", "مدرک شناسایی"),
        ("other", "سایر"),
    ]

    customer = models.ForeignKey(Customer, verbose_name="مشتری", on_delete=models.CASCADE, related_name="documents")
    deal = models.ForeignKey(
        Deal, verbose_name="فرصت فروش مرتبط", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="documents",
    )
    document_type = models.CharField("نوع سند", max_length=20, choices=DOCUMENT_TYPES, default="other")
    title = models.CharField("عنوان", max_length=150, blank=True)
    file = models.FileField("فایل", upload_to="documents/%Y/%m/", validators=[validate_document_file])
    uploaded_by = models.ForeignKey(
        TeamMember, verbose_name="آپلودکننده", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="uploaded_documents",
    )
    expiry_date = models.DateField("تاریخ انقضا", null=True, blank=True)
    expiry_reminder_sent = models.BooleanField("یادآوری انقضا ارسال‌شده", default=False)
    created_at = models.DateTimeField("زمان آپلود", auto_now_add=True)

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "اسناد"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expiry_reminder_sent", "expiry_date"]),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.customer}"


class SatisfactionSurvey(models.Model):
    """نظرسنجی رضایت مشتری برای یک فرصت فروش مشخص - یک‌بار قابل ثبت (لینک عمومی، بدون نیاز به ورود)."""

    RATING_CHOICES = [
        (1, "خیلی ضعیف"),
        (2, "ضعیف"),
        (3, "متوسط"),
        (4, "خوب"),
        (5, "عالی"),
    ]

    deal = models.OneToOneField(Deal, verbose_name="فرصت فروش", on_delete=models.CASCADE, related_name="survey")
    rating = models.PositiveSmallIntegerField("امتیاز", choices=RATING_CHOICES)
    comment = models.TextField("نظر مشتری", blank=True)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "نظرسنجی رضایت"
        verbose_name_plural = "نظرسنجی‌های رضایت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"نظرسنجی {self.deal.title} - {self.rating}/۵"
