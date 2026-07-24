"""تسک‌های Celery برای پردازش غیرهمزمان تحلیل هوشمند"""
from celery import shared_task
from .services.deepseek import analyze_property


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def analyze_property_task(self, property_data: dict):
    """
    اجرای غیرهمزمان تحلیل هوشمند ملک.
    در صورت بروز خطا، حداکثر ۲ بار تلاش مجدد انجام می‌شود.
    """
    try:
        return analyze_property(property_data)
    except Exception as exc:
        raise self.retry(exc=exc)
