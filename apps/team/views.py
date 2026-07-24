"""ویوی عمومی صفحه معرفی مشاور (قابل کلیک از کارت مشاور در صفحه اصلی/درباره ما)"""
from django.views.generic import DetailView
from apps.properties.models import Property
from apps.properties.wishlist_views import _favorite_ids
from .models import TeamMember


class AdvisorDetailView(DetailView):
    """صفحه معرفی مشاور + لیست ملک‌های فعال او"""

    model = TeamMember
    template_name = "team/advisor_detail.html"
    context_object_name = "advisor"

    def get_queryset(self):
        return TeamMember.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.filter(advisor=self.object, is_published=True)
        context["favorite_ids"] = _favorite_ids(self.request)
        context["compare_ids"] = self.request.session.get("compare_properties", [])
        return context
