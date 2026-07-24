from django.contrib import admin
from .models import TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "phone", "user", "is_active", "order")
    list_filter = ("role", "is_active")
    search_fields = ("name", "email", "phone", "user__username")
    list_editable = ("order", "is_active")
    autocomplete_fields = ["user"]
