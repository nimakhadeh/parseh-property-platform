from django.urls import path
from . import views
from .reports import ReportsDashboardView

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("درباره-ما/", views.AboutView.as_view(), name="about"),
    path("پرسش-های-متداول/", views.FAQView.as_view(), name="faq"),
    path("گزارش-مدیریت/", ReportsDashboardView.as_view(), name="reports"),
]
