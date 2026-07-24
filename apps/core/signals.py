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
    cache.delete_many(["home:sale_properties", "home:rent_properties", "home:team_members"])


post_save.connect(_clear_home_cache, sender=Property)
post_delete.connect(_clear_home_cache, sender=Property)
post_save.connect(_clear_home_cache, sender=TeamMember)
post_delete.connect(_clear_home_cache, sender=TeamMember)
