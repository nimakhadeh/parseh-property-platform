"""تنظیمات Celery برای پردازش غیرهمزمان (مانند تحلیل هوشمند ملک)"""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("parseh_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"درخواست: {self.request!r}")
