from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from apps.properties.models import Property
from .services.deepseek import analyze_property, DeepSeekNotConfiguredError
from .tasks import analyze_property_task


@require_POST
@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def analyze_property_view(request, slug):
    """
    ویو تحلیل هوشمند ملک با HTMX.
    محدود به ۵ درخواست در ساعت برای هر IP، چون هر فراخوانی هزینه واقعی از API پولی DeepSeek کم می‌کند.
    ابتدا سعی می‌کند به صورت مستقیم (همزمان) پاسخ بگیرد؛
    در صورت کندی یا خطا، امکان اجرای غیرهمزمان با Celery نیز فراهم است.
    """
    if getattr(request, "limited", False):
        return render(request, "properties/partials/ai_analysis_result.html", {
            "error": "تعداد درخواست‌های شما برای تحلیل هوشمند در این ساعت به سقف مجاز رسیده. لطفاً کمی بعد دوباره تلاش کنید.",
        })

    property_obj = get_object_or_404(Property, slug=slug, is_published=True)

    if not settings.DEEPSEEK_API_KEY:
        return render(request, "properties/partials/ai_analysis_result.html", {
            "error": "سرویس تحلیل هوشمند در حال حاضر فعال نیست. لطفاً کلید DeepSeek API را تنظیم کنید.",
        })

    property_data = {
        "id": property_obj.id,
        "title": property_obj.title,
        "description": property_obj.description,
        "price": property_obj.price,
        "transaction_type": property_obj.get_transaction_type_display(),
        "area": property_obj.area,
        "rooms": property_obj.rooms,
        "floor": property_obj.floor,
        "total_floors": property_obj.total_floors,
        "year_built": property_obj.year_built,
        "has_elevator": property_obj.has_elevator,
        "has_parking": property_obj.has_parking,
        "has_warehouse": property_obj.has_warehouse,
        "has_balcony": property_obj.has_balcony,
        "address": property_obj.address,
    }

    try:
        # تلاش برای فراخوانی مستقیم تا کاربر منتظر صف Celery نماند
        result = analyze_property(property_data)
        return render(request, "properties/partials/ai_analysis_result.html", {"result": result})
    except DeepSeekNotConfiguredError as exc:
        return render(request, "properties/partials/ai_analysis_result.html", {"error": str(exc)})
    except Exception:
        # در صورت بروز خطا (مثلاً timeout)، به صورت غیرهمزمان با Celery تلاش می‌کنیم
        analyze_property_task.delay(property_data)
        return render(request, "properties/partials/ai_analysis_result.html", {
            "error": "در حال حاضر امکان تحلیل فوری وجود ندارد. درخواست شما در حال پردازش است، لطفاً کمی بعد دوباره تلاش کنید.",
        })
