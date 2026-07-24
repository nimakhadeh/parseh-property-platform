"""سرویس ارسال اعلان تلگرام هنگام ثبت درخواست تماس جدید (بر پایه سرویس مشترک apps.core.telegram)"""
from apps.core.telegram import send_telegram_message


def notify_new_contact_request(contact_request):
    """ارسال پیام تلگرام هنگام ثبت یک درخواست تماس جدید"""
    property_line = ""
    if contact_request.property_id:
        property_line = f"\n🏠 ملک مرتبط: {contact_request.property.title}"

    message = (
        "📩 درخواست تماس جدید در پلتفرم پارسه\n\n"
        f"👤 نام: {contact_request.name}\n"
        f"📞 تلفن: {contact_request.phone}\n"
        f"✉️ ایمیل: {contact_request.email or '-'}"
        f"{property_line}\n\n"
        f"💬 پیام: {contact_request.message}"
    )
    send_telegram_message(message)
