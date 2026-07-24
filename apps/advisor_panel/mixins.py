"""میکسین‌های کنترل دسترسی برای پنل مدیریت مشاوران"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """فقط مدیر مجموعه (is_staff) اجازه دسترسی به مدیریت لیست مشاوران را دارد"""

    login_url = "accounts:login"

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("این بخش فقط برای مدیر مجموعه قابل دسترسی است.")
        return super().handle_no_permission()


class AdvisorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    فقط کاربرانی که یک پروفایل TeamMember به حساب‌شان متصل است (مشاوران) اجازه دسترسی دارند.
    مدیران (is_staff) هم برای مقاصد پشتیبانی به همه‌ی پنل دسترسی دارند.
    """

    login_url = "accounts:login"

    def test_func(self):
        user = self.request.user
        return user.is_staff or hasattr(user, "team_member")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("شما به‌عنوان مشاور در سیستم ثبت نشده‌اید. لطفاً با مدیر سایت تماس بگیرید.")
        return super().handle_no_permission()

    def get_advisor(self):
        """برگرداندن TeamMember مرتبط با کاربر جاری (یا None اگر staff بدون پروفایل مشاور باشد)"""
        return getattr(self.request.user, "team_member", None)
