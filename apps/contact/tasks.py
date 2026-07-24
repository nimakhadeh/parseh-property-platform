from celery import shared_task
from .telegram_notify import notify_new_contact_request as _notify
from .models import ContactRequest


@shared_task
def notify_new_contact_request_task(contact_request_id):
    try:
        contact_request = ContactRequest.objects.select_related("property").get(pk=contact_request_id)
        _notify(contact_request)
    except ContactRequest.DoesNotExist:
        pass
