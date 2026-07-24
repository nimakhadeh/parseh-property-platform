from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordChangeForm,
    PasswordResetForm, SetPasswordForm,
)
from django.contrib.auth.models import User
from .models import Profile

INPUT_CLASS = "input-field"


class StyledPasswordResetForm(PasswordResetForm):
    """فرم درخواست بازنشانی رمز عبور (مرحله اول: وارد کردن ایمیل)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "ایمیلی که با آن ثبت‌نام کرده‌اید"})


class StyledSetPasswordForm(SetPasswordForm):
    """فرم تعیین رمز عبور جدید (مرحله دوم: بعد از کلیک روی لینک ایمیل)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": INPUT_CLASS})
            field.help_text = None


class StyledPasswordChangeForm(PasswordChangeForm):
    """فرم تغییر رمز با استایل هماهنگ با بقیه فرم‌های سایت"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": INPUT_CLASS})
            field.help_text = None


class StyledAuthenticationForm(AuthenticationForm):
    """فرم ورود با استایل هماهنگ با بقیه فرم‌های سایت"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "نام کاربری"})
        self.fields["password"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "رمز عبور"})


class RegisterForm(UserCreationForm):
    """فرم ثبت‌نام با فیلد اضافه شماره تماس"""

    email = forms.EmailField(label="ایمیل", required=True, widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "ایمیل"}))
    phone = forms.CharField(label="شماره تماس", required=False, widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس (اختیاری)"}))

    class Meta:
        model = User
        fields = ["username", "email", "phone", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام کاربری"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "رمز عبور"})
        self.fields["password2"].widget.attrs.update({"class": INPUT_CLASS, "placeholder": "تکرار رمز عبور"})
        for field in self.fields.values():
            field.help_text = None

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.email = self.cleaned_data["email"]
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get("phone", "")
            profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """فرم ویرایش پروفایل (شماره تماس)"""

    class Meta:
        model = Profile
        fields = ["phone"]
        widgets = {
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "شماره تماس"}),
        }


class UserUpdateForm(forms.ModelForm):
    """فرم ویرایش اطلاعات پایه کاربر (نام، ایمیل)"""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام"}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام خانوادگی"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "ایمیل"}),
        }
