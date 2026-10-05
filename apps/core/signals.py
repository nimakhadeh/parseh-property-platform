"""
ابطال خودکار کش صفحه اصلی هنگام ثبت/ویرایش/حذف ملک یا مشاور.
این تضمین می‌کند که کاربر همیشه آخرین اطلاعات را می‌بیند، حتی وقتی کش فعال است.
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.properties.models import Property
from apps.team.models import TeamMember


def _clear_home_cache(**kwargs):
    property_instance = kwargs.get("instance")
    keys = [
        "home:sale_properties", "home:rent_properties", "home:team_members",
        "home:stats_properties_count", "home:stats_advisors_count",
        "property_detail:related:sale", "property_detail:related:rent",
    ]
    if property_instance is not None and getattr(property_instance, "pk", None):
        keys.append(f"ai_analysis:property:{property_instance.pk}")
    cache.delete_many(keys)


post_save.connect(_clear_home_cache, sender=Property)
post_delete.connect(_clear_home_cache, sender=Property)
post_save.connect(_clear_home_cache, sender=TeamMember)
post_delete.connect(_clear_home_cache, sender=TeamMember)
