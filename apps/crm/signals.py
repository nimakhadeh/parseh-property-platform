"""
هر جا شماره تلفن یک مشتری برای اولین‌بار در سایت ثبت می‌شود (درخواست تماس، درخواست
ارزیابی، یا لاگ فعالیت مشاور)، این سیگنال‌ها به‌صورت خودکار (یا پیدا) یک رکورد Customer
می‌سازند تا پرونده‌ی یکپارچه‌ی مشتری (apps.crm.models.Customer) همیشه به‌روز بماند.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.contact.models import ContactRequest
from apps.properties.models import PropertyValuationRequest

from .models import ActivityLog, Customer


def _get_or_create_customer(phone, name=""):
    if not phone:
        return
    customer, created = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
    if not created and name and not customer.name:
        customer.name = name
        customer.save(update_fields=["name"])


@receiver(post_save, sender=ContactRequest)
def sync_customer_from_contact_request(sender, instance, created, **kwargs):
    if created:
        _get_or_create_customer(instance.phone, instance.name)


@receiver(post_save, sender=PropertyValuationRequest)
def sync_customer_from_valuation_request(sender, instance, created, **kwargs):
    if created:
        _get_or_create_customer(instance.phone, instance.name)


@receiver(post_save, sender=ActivityLog)
def sync_customer_from_activity_log(sender, instance, created, **kwargs):
    if created and instance.customer_phone:
        _get_or_create_customer(instance.customer_phone, instance.customer_name)
