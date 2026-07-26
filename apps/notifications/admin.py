from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "message", "actor", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("message", "recipient__username")
    autocomplete_fields = ("recipient", "actor")
