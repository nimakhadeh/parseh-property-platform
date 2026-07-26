from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("زنگوله/", views.bell_partial, name="bell_partial"),
    path("همه-خوانده-شد/", views.mark_all_read, name="mark_all_read"),
    path("<int:pk>/برو/", views.go_to_notification, name="go"),
]
