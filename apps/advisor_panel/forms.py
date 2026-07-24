from django import forms
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
