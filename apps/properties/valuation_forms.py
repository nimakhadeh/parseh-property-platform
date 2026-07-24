from django import forms
from .models import PropertyValuationRequest

INPUT_CLASS = "input-field"


class PropertyValuationRequestForm(forms.ModelForm):
    """فرم عمومی ثبت درخواست ارزیابی آنلاین ملک (برای مالکین)"""

    class Meta:
        model = PropertyValuationRequest
        fields = [
            "name", "phone", "email", "transaction_type",
            "address", "area", "rooms", "description",
            "image", "image_2", "image_3",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام و نام خانوادگی"}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "ایمیل (اختیاری)"}),
            "transaction_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "address": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "آدرس کامل ملک"}),
            "area": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "متراژ (متر مربع)"}),
            "rooms": forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "تعداد اتاق"}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 4, "placeholder": "توضیحات تکمیلی درباره ملک (سال ساخت، امکانات، وضعیت و ...)"}),
        }
