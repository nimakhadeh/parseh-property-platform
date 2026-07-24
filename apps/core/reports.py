"""داشبورد گزارش‌گیری برای مدیر سایت (فقط کاربران staff دسترسی دارند)"""
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from django.views.generic import TemplateView

from apps.properties.models import Property, Favorite
from apps.contact.models import ContactRequest
from apps.blog.models import Post
from apps.team.models import TeamMember


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """محدودسازی دسترسی به کاربران staff (مدیر سایت)"""

    login_url = "accounts:login"

    def test_func(self):
        return self.request.user.is_staff


class ReportsDashboardView(StaffRequiredMixin, TemplateView):
    """گزارش کلی سایت: بازدید، عملکرد مشاوران، درخواست‌های تماس، رشد اعضا"""

    template_name = "core/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- آمار کلی املاک ---
        properties = Property.objects.all()
        context["total_properties"] = properties.count()
        context["published_properties"] = properties.filter(is_published=True).count()
        context["sale_count"] = properties.filter(transaction_type="sale").count()
        context["rent_count"] = properties.filter(transaction_type="rent").count()
        context["total_views"] = properties.aggregate(total=Sum("views_count"))["total"] or 0
        context["total_favorites"] = Favorite.objects.count()

        # --- پربازدیدترین ملک‌ها (برای نمودار میله‌ای ساده) ---
        top_properties = list(properties.order_by("-views_count")[:10])
        max_views = max([p.views_count for p in top_properties], default=1) or 1
        for p in top_properties:
            p.bar_percent = round((p.views_count / max_views) * 100) if max_views else 0
        context["top_properties"] = top_properties

        # --- عملکرد مشاوران ---
        # توجه: به‌عمد stats هر مشاور با کوئری‌های جداگانه محاسبه می‌شود، نه annotate ترکیبی،
        # چون ترکیب Count/Sum روی چند رابطه‌ی reverse-FK متفاوت در یک کوئری باعث تورم غلط اعداد می‌شود.
        advisor_stats = []
        for advisor in TeamMember.objects.filter(is_active=True):
            advisor_properties = Property.objects.filter(advisor=advisor)
            advisor_stats.append({
                "advisor": advisor,
                "property_count": advisor_properties.count(),
                "views_sum": advisor_properties.aggregate(total=Sum("views_count"))["total"] or 0,
                "unread_requests": ContactRequest.objects.filter(property__advisor=advisor, is_read=False).count(),
            })
        advisor_stats.sort(key=lambda a: a["views_sum"], reverse=True)
        context["advisor_stats"] = advisor_stats

        # --- درخواست‌های تماس ---
        contact_requests = ContactRequest.objects.all()
        context["total_contact_requests"] = contact_requests.count()
        context["unread_contact_requests"] = contact_requests.filter(is_read=False).count()

        # --- روند هفتگی درخواست‌های تماس (۸ هفته اخیر) ---
        eight_weeks_ago = timezone.now() - timedelta(weeks=8)
        weekly_requests = (
            contact_requests.filter(created_at__gte=eight_weeks_ago)
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        weekly_requests = list(weekly_requests)
        max_weekly = max([w["count"] for w in weekly_requests], default=1) or 1
        for w in weekly_requests:
            w["bar_percent"] = round((w["count"] / max_weekly) * 100)
        context["weekly_requests"] = weekly_requests

        # --- روند هفتگی ثبت‌نام کاربران (۸ هفته اخیر) ---
        weekly_signups = (
            User.objects.filter(date_joined__gte=eight_weeks_ago)
            .annotate(week=TruncWeek("date_joined"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        weekly_signups = list(weekly_signups)
        max_signups = max([w["count"] for w in weekly_signups], default=1) or 1
        for w in weekly_signups:
            w["bar_percent"] = round((w["count"] / max_signups) * 100)
        context["weekly_signups"] = weekly_signups
        context["total_users"] = User.objects.count()

        # --- وبلاگ ---
        context["total_posts"] = Post.objects.filter(is_published=True).count()
        context["total_post_views"] = Post.objects.aggregate(total=Sum("views_count"))["total"] or 0

        return context
