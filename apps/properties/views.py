from django.views.generic import ListView, DetailView
from django.db.models import F, Q
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Property, PropertyView as PropertyViewHistory
from .filter_forms import PropertyFilterForm
from .wishlist_views import _favorite_ids, _compare_ids

# کش استخر ملک‌های مرتبط برای صفحه جزئیات؛ فقط ۲ کلید (sale/rent) پس با
# ابطال کش صفحه اصلی هماهنگ است (apps/core/signals.py::_clear_home_cache)
RELATED_PROPERTIES_CACHE_TIMEOUT = 60 * 15  # ۱۵ دقیقه


class PropertyListView(ListView):
    """لیست املاک با فیلتر پیشرفته (نوع معامله، قیمت، اتاق، متراژ، امکانات) + Infinite Scroll با HTMX"""

    model = Property
    template_name = "properties/property_list.html"
    context_object_name = "properties"
    paginate_by = 9

    def get_queryset(self):
        qs = Property.objects.filter(is_published=True)
        g = self.request.GET

        transaction_type = g.get("type")
        if transaction_type in ("sale", "rent"):
            qs = qs.filter(transaction_type=transaction_type)

        query = g.get("q", "").strip()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(address__icontains=query))

        filters = PropertyFilterForm(g)
        filters.is_valid()
        # Invalid individual fields/ranges are ignored; valid filters still apply.
        for field in ("price", "area"):
            for bound, lookup in (("min", "gte"), ("max", "lte")):
                value = filters.cleaned_data.get(f"{bound}_{field}")
                if value is not None:
                    qs = qs.filter(**{f"{field}__{lookup}": value})

        rooms = filters.cleaned_data.get("rooms")
        if rooms is not None:
            qs = qs.filter(rooms__gte=4) if rooms >= 4 else qs.filter(rooms=rooms)

        if g.get("has_elevator"):
            qs = qs.filter(has_elevator=True)
        if g.get("has_parking"):
            qs = qs.filter(has_parking=True)
        if g.get("has_warehouse"):
            qs = qs.filter(has_warehouse=True)
        if g.get("has_balcony"):
            qs = qs.filter(has_balcony=True)

        sort = g.get("sort")
        if sort == "price_asc":
            qs = qs.order_by("price")
        elif sort == "price_desc":
            qs = qs.order_by("-price")
        elif sort == "newest":
            qs = qs.order_by("-created_at")
        elif sort == "area_desc":
            qs = qs.order_by("-area")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # برای نمایش پین‌ها روی نقشه تعاملی (فقط ملک‌هایی که مختصات دارند)
        context["map_properties"] = [
            p for p in context["properties"] if p.latitude and p.longitude
        ]
        context["favorite_ids"] = _favorite_ids(self.request)
        context["compare_ids"] = _compare_ids(self.request)

        qs_dict = self.request.GET.copy()
        qs_dict.pop("page", None)
        context["querystring"] = qs_dict.urlencode()
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["properties/partials/property_list_items.html"]
        return [self.template_name]


class PropertyDetailView(DetailView):
    """جزئیات ملک"""

    model = Property
    template_name = "properties/property_detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Property.objects.select_related("advisor").filter(is_published=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        Property.objects.filter(pk=obj.pk).update(views_count=F("views_count") + 1)
        if self.request.user.is_authenticated:
            PropertyViewHistory.objects.update_or_create(user=self.request.user, property=obj)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        related_pool = cache.get_or_set(
            f"property_detail:related:{self.object.transaction_type}",
            lambda: list(
                Property.objects.filter(
                    is_published=True, transaction_type=self.object.transaction_type
                ).order_by("-created_at")[:10]
            ),
            RELATED_PROPERTIES_CACHE_TIMEOUT,
        )
        context["related_properties"] = [p for p in related_pool if p.pk != self.object.pk][:3]

        # این بخش‌ها هیچ‌وقت کش نمی‌شوند چون به کاربر/session جاری وابسته‌اند
        context["favorite_ids"] = _favorite_ids(self.request)
        context["compare_ids"] = _compare_ids(self.request)
        return context
