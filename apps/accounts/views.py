from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages

from apps.properties.models import Favorite, PropertyView
from apps.properties.wishlist_views import _favorite_ids
from apps.contact.models import ContactRequest
from .forms import RegisterForm, ProfileUpdateForm, UserUpdateForm, StyledAuthenticationForm


def _merge_session_favorites_into_account(request, user):
    """
    وقتی کاربری بدون ورود، ملک‌هایی را به علاقه‌مندی‌های session اضافه کرده و سپس
    ثبت‌نام/ورود می‌کند، این تابع آن‌ها را به حساب کاربری‌اش منتقل می‌کند.
    """
    session_favorites = request.session.get("favorite_properties", [])
    for property_id in session_favorites:
        Favorite.objects.get_or_create(user=user, property_id=property_id)
    if session_favorites:
        request.session["favorite_properties"] = []
        request.session.modified = True


class CustomLoginView(LoginView):
    """ورود کاربر + ادغام خودکار علاقه‌مندی‌های session با حساب کاربری"""

    template_name = "accounts/login.html"
    form_class = StyledAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        _merge_session_favorites_into_account(self.request, self.request.user)
        return response


class RegisterView(CreateView):
    """ثبت‌نام کاربر جدید + ورود خودکار پس از ثبت‌نام"""

    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("core:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        _merge_session_favorites_into_account(self.request, self.object)
        messages.success(self.request, "ثبت‌نام شما با موفقیت انجام شد. خوش آمدید!")
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """داشبورد کاربر: علاقه‌مندی‌ها، تاریخچه بازدید، درخواست‌های تماس، ویرایش پروفایل"""

    template_name = "accounts/profile.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["favorites"] = Favorite.objects.filter(user=user).select_related("property")[:12]
        context["recent_views"] = PropertyView.objects.filter(user=user).select_related("property")[:12]
        context["contact_requests"] = ContactRequest.objects.filter(user=user).select_related("property")[:10]
        context["favorite_ids"] = _favorite_ids(self.request)
        context["compare_ids"] = self.request.session.get("compare_properties", [])
        context["user_form"] = UserUpdateForm(instance=user)
        context["profile_form"] = ProfileUpdateForm(instance=getattr(user, "profile", None))
        return context

    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=getattr(request.user, "profile", None))
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت به‌روزرسانی شد.")
            return redirect("accounts:profile")
        context = self.get_context_data()
        context["user_form"] = user_form
        context["profile_form"] = profile_form
        return self.render_to_response(context)
