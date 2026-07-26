from datetime import timedelta

from celery import shared_task
from django.urls import reverse
from django.utils import timezone

from apps.notifications.services import notify

from .models import ActivityLog, Document


@shared_task
def send_due_activity_reminders():
    """هر فعالیتی که در ۳۰ دقیقه‌ی آینده برنامه‌ریزی شده و هنوز یادآوری نگرفته را
    به مشاور مسئولش اعلان می‌کند. توسط CELERY_BEAT_SCHEDULE هر ۵ دقیقه صدا زده می‌شود."""
    now = timezone.now()
    window_end = now + timedelta(minutes=30)
    due = ActivityLog.objects.filter(
        scheduled_at__gte=now, scheduled_at__lte=window_end,
        reminder_sent=False, is_done=False,
        advisor__user__isnull=False,
    ).select_related("advisor__user")

    sent_ids = []
    for activity in due:
        notify(
            activity.advisor.user,
            f"یادآوری: {activity.get_activity_type_display()} با {activity.customer_name or 'مشتری'} ساعت {timezone.localtime(activity.scheduled_at):%H:%M}",
            url=reverse("advisor_panel:activity_log_list"),
            related_object=activity,
        )
        sent_ids.append(activity.pk)

    if sent_ids:
        ActivityLog.objects.filter(pk__in=sent_ids).update(reminder_sent=True)
    return len(sent_ids)


@shared_task
def send_document_expiry_reminders():
    """اسنادی که تا ۷ روز دیگر (یا زودتر) منقضی می‌شوند و هنوز یادآوری نگرفته‌اند را
    به مشاور آپلودکننده اعلان می‌کند. توسط CELERY_BEAT_SCHEDULE هر روز صدا زده می‌شود."""
    upcoming = timezone.localdate() + timedelta(days=7)
    documents = Document.objects.filter(
        expiry_reminder_sent=False, expiry_date__isnull=False, expiry_date__lte=upcoming,
        uploaded_by__user__isnull=False,
    ).select_related("uploaded_by__user", "customer")

    sent_ids = []
    for document in documents:
        notify(
            document.uploaded_by.user,
            f"سند «{document.get_document_type_display()}» مشتری {document.customer} تا {document.expiry_date} منقضی می‌شود",
            url=document.customer.get_absolute_url(),
            related_object=document,
        )
        sent_ids.append(document.pk)

    if sent_ids:
        Document.objects.filter(pk__in=sent_ids).update(expiry_reminder_sent=True)
    return len(sent_ids)
