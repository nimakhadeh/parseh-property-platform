"""
تست‌های خودکار اپ حساب کاربری.
اجرا: python manage.py test apps.accounts
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from .forms import RegisterForm
from .models import Profile
from apps.properties.models import Property, Favorite
from apps.properties.tests import make_test_image


class ProfileAutoCreationTests(TestCase):
    """تست ساخت خودکار پروفایل با ساخته‌شدن هر کاربر جدید (از طریق سیگنال)"""

    def test_profile_created_automatically_on_user_creation(self):
        user = User.objects.create_user(username="newuser", password="testpass123")
        self.assertTrue(Profile.objects.filter(user=user).exists())


class RegistrationTests(TestCase):
    """تست ثبت‌نام کاربر جدید"""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _get_csrf_token(self):
        self.client.get(reverse("accounts:register"))
        return self.client.cookies["csrftoken"].value

    def test_successful_registration_creates_user_and_logs_in(self):
        token = self._get_csrf_token()
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "amirtest", "email": "amir@example.com", "phone": "09121234567",
                "password1": "ComplexPass123!", "password2": "ComplexPass123!",
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertTrue(User.objects.filter(username="amirtest").exists())
        self.assertEqual(Profile.objects.get(user__username="amirtest").phone, "09121234567")
        # کاربر باید بلافاصله بعد از ثبت‌نام لاگین شده باشد
        self.assertIn("_auth_user_id", self.client.session)

    def test_registration_with_mismatched_passwords_fails(self):
        token = self._get_csrf_token()
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "baduser", "email": "bad@example.com", "phone": "",
                "password1": "ComplexPass123!", "password2": "DifferentPass456!",
            },
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_invalid_phone_does_not_create_user_or_profile(self):
        token = self._get_csrf_token()
        for phone in ("abc", "1" * 21):
            with self.subTest(phone=phone):
                response = self.client.post(
                    reverse("accounts:register"),
                    {
                        "username": "invalidphone", "email": "phone@example.com", "phone": phone,
                        "password1": "ComplexPass123!", "password2": "ComplexPass123!",
                    },
                    HTTP_X_CSRFTOKEN=token,
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("phone", response.context["form"].errors)
                self.assertFalse(User.objects.filter(username="invalidphone").exists())
                self.assertFalse(Profile.objects.filter(user__username="invalidphone").exists())

    def test_registration_rolls_back_user_if_profile_save_fails(self):
        form = RegisterForm(data={
            "username": "atomicuser", "email": "atomic@example.com", "phone": "09121234567",
            "password1": "ComplexPass123!", "password2": "ComplexPass123!",
        })
        self.assertTrue(form.is_valid(), form.errors)
        original_save = Profile.save

        def save_profile(instance, *args, **kwargs):
            if instance.phone:
                raise RuntimeError("Profile storage failed")
            return original_save(instance, *args, **kwargs)

        with patch.object(Profile, "save", autospec=True, side_effect=save_profile):
            with self.assertRaisesMessage(RuntimeError, "Profile storage failed"):
                form.save()
        self.assertFalse(User.objects.filter(username="atomicuser").exists())
        self.assertFalse(Profile.objects.filter(user__username="atomicuser").exists())


class SessionFavoriteMergeTests(TestCase):
    """
    تست ادغام خودکار علاقه‌مندی‌های session با حساب کاربری هنگام ورود.
    سناریو: کاربر مهمان چند ملک را لایک می‌کند، سپس وارد حساب می‌شود؛
    آن علاقه‌مندی‌ها باید به حسابش منتقل شوند.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(username="mergeuser", password="testpass123")
        self.prop = Property.objects.create(
            title="ملک تست ادغام", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(), is_published=True,
        )

    def test_guest_favorites_merged_after_login(self):
        # مرحله ۱: کاربر مهمان ملک را لایک می‌کند (session)
        self.client.get(reverse("core:home"))
        token = self.client.cookies["csrftoken"].value
        self.client.post(reverse("properties:toggle_favorite", args=[self.prop.pk]), HTTP_X_CSRFTOKEN=token)
        self.assertIn(self.prop.pk, self.client.session.get("favorite_properties", []))

        # مرحله ۲: همان کاربر وارد حساب می‌شود
        self.client.get(reverse("accounts:login"))
        token = self.client.cookies["csrftoken"].value
        self.client.post(
            reverse("accounts:login"),
            {"username": "mergeuser", "password": "testpass123"},
            HTTP_X_CSRFTOKEN=token,
        )

        # مرحله ۳: علاقه‌مندی باید حالا در دیتابیس، متصل به حساب کاربری باشد
        self.assertTrue(Favorite.objects.filter(user=self.user, property=self.prop).exists())

    def test_login_ignores_deleted_and_withdrawn_session_favorites(self):
        withdrawn = Property.objects.create(
            title="ملک منتشرنشده", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image="", is_published=False,
        )
        deleted = Property.objects.create(
            title="ملک حذف‌شده", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image="",
        )
        deleted_id = deleted.pk
        deleted.delete()
        session = self.client.session
        session["favorite_properties"] = [self.prop.pk, withdrawn.pk, deleted_id]
        session.save()

        self.client.get(reverse("accounts:login"))
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "mergeuser", "password": "testpass123"},
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Favorite.objects.filter(user=self.user).values_list("property_id", flat=True)),
            [self.prop.pk],
        )
        self.assertEqual(self.client.session["favorite_properties"], [])
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
