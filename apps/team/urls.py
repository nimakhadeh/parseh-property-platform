from django.urls import path
from . import views

app_name = "team"

urlpatterns = [
    path("<int:pk>/", views.AdvisorDetailView.as_view(), name="advisor_detail"),
]
