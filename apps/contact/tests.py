"""
تست‌های خودکار اپ تماس.
اجرا: python manage.py test apps.contact
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import ContactRequest


class ContactRequestModelTests(TestCase):
    """تست اعتبارسنجی مدل ContactRequest"""

    def test_valid_phone_number_accepted(self):
        contact = ContactRequest(name="تست", phone="09121234567", message="سلام")
        contact.full_clean()  # نباید خطا بدهد

    def test_invalid_phone_number_rejected(self):
        contact = ContactRequest(name="تست", phone="12345", message="سلام")
        with self.assertRaises(ValidationError):
            contact.full_clean()

    def test_message_over_max_length_rejected(self):
        contact = ContactRequest(name="تست", phone="09121234567", message="ا" * 2001)
        with self.assertRaises(ValidationError):
            contact.full_clean()


@override_settings(RATELIMIT_ENABLE=False)
class ContactFormSubmissionTests(TestCase):
    """
    تست ارسال فرم تماس، شامل هانی‌پات ضداسپم.
    از enforce_csrf_checks=True استفاده می‌کنیم تا رفتار واقعی مرورگر شبیه‌سازی شود.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _get_csrf_token(self):
        self.client.get(reverse("contact:contact_page"))
        return self.client.cookies["csrftoken"].value

    def test_valid_submission_creates_request(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("contact:contact_submit"),
            {"name": "علی رضایی", "phone": "09121234567", "email": "", "message": "سلام، سوال داشتم"},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactRequest.objects.count(), 1)

    def test_honeypot_field_blocks_bot_submission(self):
        """اگر فیلد نامرئی 'website' پر شده باشد (یعنی احتمالاً یک ربات است)، نباید درخواستی ثبت شود"""
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("contact:contact_submit"),
            {
                "name": "ربات اسپم", "phone": "09120000000", "email": "",
                "message": "پیام تبلیغاتی مشکوک", "website": "http://spam.com",
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactRequest.objects.count(), 0)  # چیزی نباید ذخیره شده باشد

    def test_authenticated_user_request_linked_to_account(self):
        user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.client.force_login(user)
        token = self._get_csrf_token()
        self.client.post(
            reverse("contact:contact_submit"),
            {"name": "تست", "phone": "09121234567", "email": "", "message": "پیام تستی"},
            HTTP_X_CSRFTOKEN=token,
        )
        request_obj = ContactRequest.objects.first()
        self.assertEqual(request_obj.user, user)

    def test_invalid_phone_shows_error_not_crash(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("contact:contact_submit"),
            {"name": "تست", "phone": "123", "email": "", "message": "پیام"},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactRequest.objects.count(), 0)
