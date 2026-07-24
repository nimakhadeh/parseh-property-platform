from django import forms
from .models import ContactRequest


class ContactRequestForm(forms.ModelForm):
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
