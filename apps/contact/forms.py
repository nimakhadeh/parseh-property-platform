from django import forms
from .models import ContactRequest


class ContactRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # درخواست بازدید می‌تواند بدون توضیح باشد، ولی پیام تماس عمومی الزامی است.
        # انتخاب ملک نیز باید از میان آگهی‌های منتشرشده اعتبارسنجی شود.
        self.fields["property"].queryset = self.fields["property"].queryset.filter(is_published=True)
        if self.is_bound and self.data.get(self.add_prefix("property")):
            self.fields["message"].required = False

    class Meta:
        model = ContactRequest
        fields = ["name", "phone", "email", "message", "property"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field", "placeholder": "نام و نام خانوادگی"}),
            "phone": forms.TextInput(attrs={"class": "input-field", "placeholder": "شماره تماس"}),
            "email": forms.EmailInput(attrs={"class": "input-field", "placeholder": "ایمیل (اختیاری)"}),
            "message": forms.Textarea(attrs={"class": "input-field", "rows": 4, "placeholder": "پیام شما"}),
            "property": forms.HiddenInput(),
        }
