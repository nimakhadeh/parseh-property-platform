from celery import shared_task
from .valuation_notify import notify_new_valuation_request as _notify
from .models import PropertyValuationRequest


@shared_task
def notify_new_valuation_request_task(valuation_request_id):
    try:
        valuation_request = PropertyValuationRequest.objects.get(pk=valuation_request_id)
        _notify(valuation_request)
    except PropertyValuationRequest.DoesNotExist:
        pass
