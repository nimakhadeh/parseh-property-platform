from django.conf import settings


def site_settings(request):
    """در اختیار قرار دادن اطلاعات سایت در تمام قالب‌ها (فوتر، واتساپ و ...)"""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_PHONE": settings.SITE_PHONE,
        "SITE_WHATSAPP": settings.SITE_WHATSAPP,
        "SITE_EMAIL": settings.SITE_EMAIL,
        "SITE_ADDRESS": settings.SITE_ADDRESS,
        "ADMIN_URL": settings.ADMIN_URL,
    }
