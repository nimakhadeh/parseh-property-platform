from django.contrib import admin

from .models import ActivityLog, Customer, Deal, Document, SatisfactionSurvey, Task


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("advisor", "activity_type", "customer_name", "property", "scheduled_at", "is_done", "created_at")
    list_filter = ("activity_type", "is_done", "advisor")
    search_fields = ("customer_name", "customer_phone", "note")
    autocomplete_fields = ("advisor", "property")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assignee", "assigner", "status", "due_date", "created_at")
    list_filter = ("status", "assignee")
    search_fields = ("title", "description")
    autocomplete_fields = ("assignee", "assigner", "property")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "created_at")
    search_fields = ("name", "phone")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "advisor", "stage", "value", "updated_at")
    list_filter = ("stage", "advisor")
    search_fields = ("title", "customer__name", "customer__phone")
    autocomplete_fields = ("customer", "property", "advisor")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("customer", "document_type", "title", "expiry_date", "expiry_reminder_sent", "uploaded_by", "created_at")
    list_filter = ("document_type", "expiry_reminder_sent")
    search_fields = ("title", "customer__name", "customer__phone")
    autocomplete_fields = ("customer", "deal", "uploaded_by")


@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ("deal", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("deal__title", "comment")
    autocomplete_fields = ("deal",)
