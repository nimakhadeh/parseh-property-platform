"""
ویوهای علاقه‌مندی (Wishlist) و مقایسه ملک.

- علاقه‌مندی‌ها: برای کاربران واردشده در دیتابیس (مدل Favorite) ذخیره می‌شود تا از هر
  دستگاهی قابل دسترس باشد؛ برای مهمان‌ها (بدون ورود) در session مرورگر نگه داشته می‌شود.
- مقایسه: همیشه مبتنی بر session است (ابزاری کوتاه‌مدت، نیازی به ماندگاری ندارد).
"""
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.http import HttpResponse
from .models import Property, Favorite

MAX_COMPARE = 3


def _toggle_session_list(request, session_key, property_id, max_items=None):
    items = request.session.get(session_key, [])
    if property_id in items:
        items.remove(property_id)
        added = False
    else:
        if max_items and len(items) >= max_items:
            return items, False, True  # لیست پر است
        items.append(property_id)
        added = True
    request.session[session_key] = items
    request.session.modified = True
    return items, added, False


def _is_favorite(request, property_obj):
    if request.user.is_authenticated:
        return Favorite.objects.filter(user=request.user, property=property_obj).exists()
    return property_obj.pk in request.session.get("favorite_properties", [])


def _favorite_ids(request):
    if request.user.is_authenticated:
        return list(Favorite.objects.filter(user=request.user).values_list("property_id", flat=True))
    return request.session.get("favorite_properties", [])


@require_POST
def toggle_favorite(request, pk):
    """افزودن/حذف ملک از علاقه‌مندی‌ها (دیتابیس برای کاربر واردشده، session برای مهمان)"""
    property_obj = get_object_or_404(Property, pk=pk, is_published=True)

    if request.user.is_authenticated:
        favorite, created = Favorite.objects.get_or_create(user=request.user, property=property_obj)
        if not created:
            favorite.delete()
            added = False
        else:
            added = True
    else:
        _, added, _ = _toggle_session_list(request, "favorite_properties", property_obj.pk)

    html = render_to_string(
        "properties/partials/favorite_button.html",
        {"property": property_obj, "is_favorite": added},
        request=request,
    )
    response = HttpResponse(html)
    response["HX-Trigger"] = "favoritesUpdated"
    return response


@require_POST
def toggle_compare(request, pk):
    """افزودن/حذف ملک از لیست مقایسه (حداکثر ۳ ملک، همیشه مبتنی بر session)"""
    property_obj = get_object_or_404(Property, pk=pk, is_published=True)
    items, added, is_full = _toggle_session_list(
        request, "compare_properties", property_obj.pk, max_items=MAX_COMPARE
    )

    html = render_to_string(
        "properties/partials/compare_button.html",
        {
            "property": property_obj,
            "is_comparing": property_obj.pk in items,
            "is_full": is_full and property_obj.pk not in items,
        },
        request=request,
    )
    response = HttpResponse(html)
    response["HX-Trigger"] = "compareUpdated"
    return response


def compare_bar(request):
    """نوار شناور پایین صفحه که ملک‌های انتخاب‌شده برای مقایسه را نشان می‌دهد"""
    ids = request.session.get("compare_properties", [])
    properties = list(Property.objects.filter(pk__in=ids, is_published=True))
    properties.sort(key=lambda p: ids.index(p.pk) if p.pk in ids else 0)
    return render(request, "properties/partials/compare_bar.html", {"properties": properties})


def header_counts(request):
    """شمارنده‌های کوچک علاقه‌مندی و مقایسه در هدر سایت"""
    favorites_count = len(_favorite_ids(request))
    compare_count = len(request.session.get("compare_properties", []))
    return render(request, "properties/partials/header_counts.html", {
        "favorites_count": favorites_count,
        "compare_count": compare_count,
    })


def favorites_list(request):
    """صفحه نمایش علاقه‌مندی‌ها"""
    if request.user.is_authenticated:
        properties = Property.objects.filter(
            pk__in=Favorite.objects.filter(user=request.user).values_list("property_id", flat=True),
            is_published=True,
        )
    else:
        ids = request.session.get("favorite_properties", [])
        properties = Property.objects.filter(pk__in=ids, is_published=True)

    return render(request, "properties/favorites_list.html", {
        "properties": properties,
        "favorite_ids": _favorite_ids(request),
        "compare_ids": request.session.get("compare_properties", []),
    })


def compare_view(request):
    """صفحه مقایسه ملک‌ها"""
    ids = request.session.get("compare_properties", [])
    properties = list(Property.objects.filter(pk__in=ids, is_published=True).select_related("advisor"))
    # حفظ ترتیب انتخاب کاربر
    properties.sort(key=lambda p: ids.index(p.pk) if p.pk in ids else 0)
    return render(request, "properties/compare.html", {
        "properties": properties,
        "favorite_ids": _favorite_ids(request),
        "compare_ids": ids,
    })


@require_POST
def clear_compare(request):
    """خالی کردن کامل لیست مقایسه"""
    request.session["compare_properties"] = []
    request.session.modified = True
    response = render(request, "properties/partials/compare_table.html", {"properties": []})
    response["HX-Trigger"] = "compareUpdated"
    return response
