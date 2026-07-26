from django import forms
from apps.contact.models import phone_validator
from apps.crm.models import ActivityLog, Deal, Document, Task
from apps.properties.models import Property
from apps.team.models import TeamMember

INPUT_CLASS = "input-field"
CHECK_CLASS = "w-4 h-4 accent-primary"


class ManagerAdvisorForm(forms.ModelForm):
    """فرم افزودن/ویرایش مشاور توسط مدیر مجموعه"""

    class Meta:
        model = TeamMember
        fields = ["name", "role", "bio", "image", "phone", "email", "user", "order", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام و نام خانوادگی"}),
            "role": forms.Select(attrs={"class": INPUT_CLASS}),
            "bio": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": "بیوگرافی کوتاه"}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "ایمیل"}),
            "user": forms.Select(attrs={"class": INPUT_CLASS}),
            "order": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
        }
        help_texts = {
            "user": "با اتصال یک حساب کاربری، آن کاربر می‌تواند وارد پنل مشاور شود.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        # چون رابطه user<->TeamMember یک‌به‌یک است، کاربرانی که از قبل به مشاور دیگری
        # متصل شده‌اند از لیست انتخاب حذف می‌شوند (به‌جز خودِ مشاور در حال ویرایش)
        taken_user_ids = TeamMember.objects.exclude(pk=self.instance.pk).exclude(user__isnull=True).values_list("user_id", flat=True)
        self.fields["user"].queryset = User.objects.exclude(id__in=taken_user_ids)
        self.fields["user"].required = False


class AdvisorPropertyForm(forms.ModelForm):
    """فرم افزودن/ویرایش ملک برای مشاوران (فیلد advisor و آمار به‌صورت خودکار مدیریت می‌شوند)"""

    class Meta:
        model = Property
        fields = [
            "title", "description", "price", "transaction_type",
            "area", "rooms", "floor", "total_floors", "year_built",
            "has_elevator", "has_parking", "has_warehouse", "has_balcony",
            "address", "latitude", "longitude",
            "image", "image_2", "image_3", "image_4",
            "is_published", "is_featured",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "عنوان ملک"}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 5, "placeholder": "توضیحات کامل ملک"}),
            "price": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "قیمت به تومان"}),
            "transaction_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "area": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "rooms": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "floor": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "total_floors": forms.NumberInput(attrs={"class": INPUT_CLASS}),
            "year_built": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "مثلاً 1402"}),
            "address": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "آدرس کامل"}),
            "latitude": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "any", "placeholder": "مثلاً 35.712300"}),
            "longitude": forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "any", "placeholder": "مثلاً 51.404300"}),
            "has_elevator": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
            "has_parking": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
            "has_warehouse": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
            "has_balcony": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
            "is_published": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
            "is_featured": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
        }


class ActivityLogForm(forms.ModelForm):
    """فرم ثبت سریع لاگ فعالیت توسط مشاور (فیلد advisor در ویو تنظیم می‌شود)"""

    class Meta:
        model = ActivityLog
        fields = ["activity_type", "property", "customer_name", "customer_phone", "note", "scheduled_at", "is_done"]
        widgets = {
            "activity_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "property": forms.Select(attrs={"class": INPUT_CLASS}),
            "customer_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام مشتری"}),
            "customer_phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس مشتری"}),
            "note": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": "یادداشت"}),
            "scheduled_at": forms.DateTimeInput(attrs={"class": INPUT_CLASS, "type": "datetime-local"}),
            "is_done": forms.CheckboxInput(attrs={"class": CHECK_CLASS}),
        }

    def __init__(self, *args, advisor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].required = False
        self.fields["property"].queryset = Property.objects.filter(advisor=advisor) if advisor else Property.objects.none()


class TaskAssignForm(forms.ModelForm):
    """فرم محول‌کردن وظیفه‌ی جدید توسط مدیر مجموعه به یک مشاور"""

    class Meta:
        model = Task
        fields = ["title", "description", "assignee", "property", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "عنوان وظیفه"}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": "توضیحات"}),
            "assignee": forms.Select(attrs={"class": INPUT_CLASS}),
            "property": forms.Select(attrs={"class": INPUT_CLASS}),
            "due_date": forms.DateTimeInput(attrs={"class": INPUT_CLASS, "type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = TeamMember.objects.filter(is_active=True).order_by("name")
        self.fields["property"].required = False
        self.fields["property"].queryset = Property.objects.all().order_by("-created_at")


class DealForm(forms.Form):
    """فرم ثبت فرصت فروش جدید در قیف فروش (مشتری با شماره تلفن پیدا/ساخته می‌شود)"""

    title = forms.CharField(label="عنوان", max_length=200, widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثلاً خرید آپارتمان ۲ خواب در ولنجک"}))
    customer_name = forms.CharField(label="نام مشتری", max_length=150, widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام مشتری"}))
    customer_phone = forms.CharField(label="شماره تماس مشتری", max_length=20, validators=[phone_validator], widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس مشتری"}))
    property = forms.ModelChoiceField(label="ملک مرتبط", queryset=Property.objects.all(), required=False, widget=forms.Select(attrs={"class": INPUT_CLASS}))
    value = forms.IntegerField(label="ارزش تخمینی معامله (تومان)", required=False, min_value=0, widget=forms.NumberInput(attrs={"class": INPUT_CLASS}))
    note = forms.CharField(label="یادداشت", required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}))


class DocumentUploadForm(forms.ModelForm):
    """فرم آپلود سند برای پرونده‌ی یک مشتری (فیلد customer/uploaded_by در ویو تنظیم می‌شود)"""

    class Meta:
        model = Document
        fields = ["document_type", "title", "file", "deal", "expiry_date"]
        widgets = {
            "document_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "title": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "عنوان سند (اختیاری)"}),
            "file": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
            "deal": forms.Select(attrs={"class": INPUT_CLASS}),
            "expiry_date": forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}),
        }

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deal"].required = False
        self.fields["deal"].queryset = customer.deals.all() if customer else Deal.objects.none()
