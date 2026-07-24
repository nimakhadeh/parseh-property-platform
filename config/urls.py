"""تنظیمات اصلی مسیرهای پروژه"""
from django.contrib import admin
from django.urls import path, include, register_converter
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from .converters import UnicodeSlugConverter
from .sitemaps import sitemaps

register_converter(UnicodeSlugConverter, "uslug")

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.core.urls")),
    path("حساب-کاربری/", include("apps.accounts.urls")),
    path("پنل-مشاور/", include("apps.advisor_panel.urls")),
    path("املاک/", include("apps.properties.urls")),
    path("مشاوران/", include("apps.team.urls")),
    path("وبلاگ/", include("apps.blog.urls")),
    path("تماس/", include("apps.contact.urls")),
    path("ai/", include("apps.ai.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "پنل مدیریت پلتفرم املاک پارسه"
admin.site.site_title = "مدیریت پارسه"
admin.site.index_title = "خوش آمدید"
