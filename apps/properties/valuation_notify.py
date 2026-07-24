"""سرویس ارسال اعلان تلگرام هنگام ثبت درخواست ارزیابی ملک جدید"""
from apps.core.telegram import send_telegram_message


def notify_new_valuation_request(valuation_request):
    """ارسال پیام تلگرام هنگام ثبت یک درخواست ارزیابی ملک جدید"""
    message = (
        "🏷 درخواست ارزیابی ملک جدید در پلتفرم پارسه\n\n"
        f"👤 نام مالک: {valuation_request.name}\n"
        f"📞 تلفن: {valuation_request.phone}\n"
        f"📍 آدرس: {valuation_request.address}\n"
        f"🎯 نوع درخواست: {valuation_request.get_transaction_type_display()}\n"
        f"📐 متراژ: {valuation_request.area or '-'}"
    )
    send_telegram_message(message)
