"""فیلترهای سفارشی قالب برای علاقه‌مندی و مقایسه ملک"""
from django import template

register = template.Library()


@register.filter
def in_list(value, the_list):
    """بررسی می‌کند آیا value داخل the_list (لیست شناسه‌های session) هست یا نه"""
    if not the_list:
        return False
    try:
        return int(value) in [int(x) for x in the_list]
    except (ValueError, TypeError):
        return value in the_list


@register.filter
def is_list_full(the_list, max_count=3):
    """بررسی می‌کند آیا لیست به سقف تعداد مجاز (پیش‌فرض ۳) رسیده است"""
    return bool(the_list) and len(the_list) >= int(max_count)


@register.filter
def as_list(value):
    """تبدیل یک آبجکت تکی به لیست یک‌عضوی (برای استفاده مجدد پارشیال نقشه با یک ملک)"""
    return [value] if value else []


@register.filter
def map_points(properties):
    """دادهٔ نقشه برای json_script؛ متن‌ها هرگز به‌عنوان کد جاوااسکریپت رندر نمی‌شوند."""
    return [
        {
            "lat": float(property_obj.latitude),
            "lng": float(property_obj.longitude),
            "title": property_obj.title,
            "price": property_obj.price_display,
            "url": property_obj.get_absolute_url(),
        }
        for property_obj in properties
        if property_obj.latitude is not None and property_obj.longitude is not None
    ]
