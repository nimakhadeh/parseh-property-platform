from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    verbose_name = "مدیریت ارتباط با مشتری (CRM)"

    def ready(self):
        from . import signals  # noqa
