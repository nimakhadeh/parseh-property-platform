from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("<int:pk>/", views.survey_submit, name="survey_submit"),
]
