from django.contrib import admin
from .models import Property, Favorite, PropertyView, PropertyValuationRequest


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "transaction_type", "price", "area", "advisor", "is_published", "is_featured", "views_count")
    list_filter = ("transaction_type", "is_published", "is_featured", "has_elevator", "has_parking")
    search_fields = ("title", "description", "address")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published", "is_featured")
    autocomplete_fields = ["advisor"]
    readonly_fields = ("views_count", "created_at", "updated_at")

    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("title", "slug", "description", "transaction_type", "price")}),
        ("مشخصات فنی", {"fields": ("area", "rooms", "floor", "total_floors", "year_built")}),
        ("امکانات", {"fields": ("has_elevator", "has_parking", "has_warehouse", "has_balcony")}),
        ("موقعیت مکانی", {"fields": ("address", "latitude", "longitude")}),
        ("تصاویر", {"fields": ("image", "image_2", "image_3", "image_4")}),
        ("مشاور و وضعیت", {"fields": ("advisor", "is_published", "is_featured")}),
        ("آمار", {"fields": ("views_count", "created_at", "updated_at")}),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "property", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "property__title")
    autocomplete_fields = ["property"]


@admin.register(PropertyView)
class PropertyViewAdmin(admin.ModelAdmin):
    list_display = ("user", "property", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("user__username", "property__title")
    autocomplete_fields = ["property"]


@admin.register(PropertyValuationRequest)
class PropertyValuationRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "transaction_type", "status", "assigned_advisor", "created_at")
    list_filter = ("status", "transaction_type", "created_at")
    search_fields = ("name", "phone", "email", "address")
    list_editable = ("status", "assigned_advisor")
    autocomplete_fields = ["assigned_advisor"]
    readonly_fields = ("created_at",)

    fieldsets = (
        ("اطلاعات مالک", {"fields": ("name", "phone", "email")}),
        ("اطلاعات ملک", {"fields": ("transaction_type", "address", "area", "rooms", "description")}),
        ("تصاویر", {"fields": ("image", "image_2", "image_3")}),
        ("پیگیری", {"fields": ("status", "assigned_advisor", "admin_notes", "created_at")}),
    )
