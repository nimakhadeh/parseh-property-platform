"""نقطه‌ی ورود مشترک برای ساخت اعلان از هر اپی. سایر اپ‌ها به‌جای ساخت مستقیم
Notification، این تابع را صدا می‌زنند تا منطق ساخت یک‌جا بماند."""
from django.contrib.contenttypes.models import ContentType

from .models import Notification


def notify(recipient, message, *, url="", actor=None, related_object=None):
    kwargs = {"recipient": recipient, "message": message, "url": url, "actor": actor}
    if related_object is not None:
        kwargs["content_type"] = ContentType.objects.get_for_model(related_object)
        kwargs["object_id"] = related_object.pk
    return Notification.objects.create(**kwargs)


def notify_many(recipients, message, *, url="", actor=None, related_object=None):
    return [
        notify(recipient, message, url=url, actor=actor, related_object=related_object)
        for recipient in recipients
    ]
