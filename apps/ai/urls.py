from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("تحلیل/<uslug:slug>/", views.analyze_property_view, name="analyze_property"),
]
