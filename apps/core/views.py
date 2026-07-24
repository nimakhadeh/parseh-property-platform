from django.core.cache import cache
from django.views.generic import TemplateView
from apps.properties.models import Property
from apps.properties.wishlist_views import _favorite_ids
from apps.team.models import TeamMember
from .models import FAQ

# مدت زمان کش صفحه اصلی؛ به‌محض ثبت/ویرایش ملک یا مشاور، این کش به‌صورت خودکار پاک می‌شود
# (به apps/core/signals.py مراجعه کنید) بنابراین این عدد صرفاً یک "شبکه ایمنی" است
HOME_CACHE_TIMEOUT = 60 * 15  # ۱۵ دقیقه


class HomeView(TemplateView):
    """صفحه اصلی سایت"""

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sale_properties"] = cache.get_or_set(
            "home:sale_properties",
            lambda: list(Property.objects.filter(is_published=True, transaction_type="sale")[:6]),
            HOME_CACHE_TIMEOUT,
        )
        context["rent_properties"] = cache.get_or_set(
            "home:rent_properties",
            lambda: list(Property.objects.filter(is_published=True, transaction_type="rent")[:6]),
            HOME_CACHE_TIMEOUT,
        )
        context["team_members"] = cache.get_or_set(
            "home:team_members",
            lambda: list(TeamMember.objects.filter(is_active=True)[:4]),
            HOME_CACHE_TIMEOUT,
        )

        # این بخش‌ها هیچ‌وقت کش نمی‌شوند چون به کاربر/session جاری وابسته‌اند
        context["favorite_ids"] = _favorite_ids(self.request)
        context["compare_ids"] = self.request.session.get("compare_properties", [])
        return context


class FAQView(TemplateView):
    """صفحه پرسش‌های متداول"""

    template_name = "core/faq.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faqs = FAQ.objects.filter(is_published=True)
        grouped = {}
        for faq in faqs:
            grouped.setdefault(faq.get_category_display(), []).append(faq)
        context["grouped_faqs"] = grouped
        return context


class AboutView(TemplateView):
    """صفحه درباره ما / معرفی تیم"""

    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team_members"] = TeamMember.objects.filter(is_active=True)
        return context
