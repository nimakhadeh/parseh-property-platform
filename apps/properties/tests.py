"""
تست‌های خودکار اپ املاک.
اجرا: python manage.py test apps.properties
"""
from io import BytesIO

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.team.models import TeamMember
from .models import Property, Favorite


def make_test_image():
    """ساخت یک فایل تصویر واقعی و کوچک برای تست (نه فقط یک فایل متنی جعلی)"""
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile("test.png", buffer.getvalue(), content_type="image/png")


class PropertyModelTests(TestCase):
    """تست مدل Property"""

    def test_slug_auto_generated_from_title(self):
        prop = Property.objects.create(
            title="آپارتمان لوکس در ولنجک",
            description="توضیحات تستی",
            price=5_000_000_000,
            transaction_type="sale",
            area=120,
            rooms=3,
            address="تهران",
            image=make_test_image(),
        )
        self.assertTrue(prop.slug)  # اسلاگ باید خودکار ساخته شده باشد
        self.assertNotEqual(prop.slug, "")

    def test_duplicate_titles_get_unique_slugs(self):
        """دو ملک با عنوان یکسان نباید اسلاگ یکسان بگیرند (وگرنه خطای URL تکراری پیش می‌آید)"""
        prop1 = Property.objects.create(
            title="ملک تستی مشابه", description="۱", price=1000, transaction_type="sale",
            area=50, rooms=1, address="تهران", image=make_test_image(),
        )
        prop2 = Property.objects.create(
            title="ملک تستی مشابه", description="۲", price=2000, transaction_type="sale",
            area=60, rooms=2, address="تهران", image=make_test_image(),
        )
        self.assertNotEqual(prop1.slug, prop2.slug)

    def test_price_display_formats_correctly(self):
        prop = Property.objects.create(
            title="تست قیمت", description="-", price=5_200_000_000, transaction_type="sale",
            area=100, rooms=2, address="-", image=make_test_image(),
        )
        self.assertIn("میلیارد", prop.price_display)

    def test_property_str_returns_title(self):
        prop = Property.objects.create(
            title="عنوان خاص", description="-", price=100, transaction_type="rent",
            area=10, rooms=1, address="-", image=make_test_image(),
        )
        self.assertEqual(str(prop), "عنوان خاص")


class PropertyListViewTests(TestCase):
    """تست فیلترهای صفحه لیست ملک"""

    def setUp(self):
        self.client = Client()
        Property.objects.create(
            title="ملک فروش ارزان", description="-", price=1_000_000_000, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(), is_published=True,
        )
        Property.objects.create(
            title="ملک اجاره", description="-", price=50_000_000, transaction_type="rent",
            area=60, rooms=1, address="-", image=make_test_image(), is_published=True,
        )
        Property.objects.create(
            title="ملک منتشرنشده", description="-", price=1, transaction_type="sale",
            area=1, rooms=1, address="-", image=make_test_image(), is_published=False,
        )

    def test_only_published_properties_shown(self):
        response = self.client.get(reverse("properties:property_list"))
        self.assertEqual(response.status_code, 200)
        titles = [p.title for p in response.context["properties"]]
        self.assertNotIn("ملک منتشرنشده", titles)

    def test_filter_by_transaction_type(self):
        response = self.client.get(reverse("properties:property_list"), {"type": "rent"})
        titles = [p.title for p in response.context["properties"]]
        self.assertIn("ملک اجاره", titles)
        self.assertNotIn("ملک فروش ارزان", titles)

    def test_filter_by_price_range(self):
        response = self.client.get(reverse("properties:property_list"), {"max_price": "100000000"})
        titles = [p.title for p in response.context["properties"]]
        self.assertIn("ملک اجاره", titles)
        self.assertNotIn("ملک فروش ارزان", titles)


class PropertyDetailViewTests(TestCase):
    """تست صفحه جزئیات ملک"""

    def setUp(self):
        self.client = Client()
        self.prop = Property.objects.create(
            title="ملک تست جزئیات", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(), is_published=True,
        )

    def test_detail_page_loads(self):
        response = self.client.get(self.prop.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_view_count_increments(self):
        initial = self.prop.views_count
        self.client.get(self.prop.get_absolute_url())
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.views_count, initial + 1)

    def test_unpublished_property_returns_404(self):
        self.prop.is_published = False
        self.prop.save()
        response = self.client.get(self.prop.get_absolute_url())
        self.assertEqual(response.status_code, 404)


class FavoriteToggleTests(TestCase):
    """
    تست دکمه علاقه‌مندی - هم برای کاربر مهمان (session) و هم کاربر واردشده (دیتابیس).
    این دقیقاً همان قابلیتی است که قبلاً به‌خاطر نبود توکن CSRF در HTMX از کار افتاده بود.

    نکته مهم: Client پیش‌فرض جنگو بررسی CSRF را نادیده می‌گیرد (enforce_csrf_checks=False)،
    یعنی اگر این تست را با Client عادی می‌نوشتیم، حتی با بازگشت همان باگ قدیمی هم PASS می‌شد!
    برای همین عمداً enforce_csrf_checks=True استفاده می‌کنیم تا رفتار واقعی مرورگر+HTMX را
    شبیه‌سازی کنیم و این تست واقعاً از رگرسیون آن باگ محافظت کند.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.prop = Property.objects.create(
            title="ملک تست لایک", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(), is_published=True,
        )

    def _get_csrf_token(self):
        """دریافت توکن CSRF از کوکی، دقیقاً همان کاری که کد جاوااسکریپت سایت انجام می‌دهد"""
        self.client.get(reverse("core:home"))
        return self.client.cookies["csrftoken"].value

    def test_guest_can_toggle_favorite_via_session(self):
        token = self._get_csrf_token()
        url = reverse("properties:toggle_favorite", args=[self.prop.pk])
        response = self.client.post(url, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertIn(self.prop.pk, session.get("favorite_properties", []))

    def test_request_without_csrf_token_is_rejected(self):
        """این تست تضمین می‌کند درخواست بدون توکن CSRF واقعاً رد می‌شود (رفتار امنیتی صحیح)"""
        self.client.get(reverse("core:home"))  # کوکی ست می‌شود اما هدر ارسال نمی‌کنیم
        url = reverse("properties:toggle_favorite", args=[self.prop.pk])
        response = self.client.post(url)  # بدون HTTP_X_CSRFTOKEN
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_favorite_saved_to_database(self):
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_login(user)
        token = self._get_csrf_token()
        url = reverse("properties:toggle_favorite", args=[self.prop.pk])
        self.client.post(url, HTTP_X_CSRFTOKEN=token)
        self.assertTrue(Favorite.objects.filter(user=user, property=self.prop).exists())

    def test_toggle_twice_removes_favorite(self):
        user = User.objects.create_user(username="testuser2", password="testpass123")
        self.client.force_login(user)
        token = self._get_csrf_token()
        url = reverse("properties:toggle_favorite", args=[self.prop.pk])
        self.client.post(url, HTTP_X_CSRFTOKEN=token)
        self.client.post(url, HTTP_X_CSRFTOKEN=token)  # بار دوم باید حذفش کند
        self.assertFalse(Favorite.objects.filter(user=user, property=self.prop).exists())


class CompareToggleTests(TestCase):
    """تست محدودیت حداکثر ۳ ملک برای مقایسه"""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.properties = [
            Property.objects.create(
                title=f"ملک مقایسه {i}", description="-", price=100, transaction_type="sale",
                area=80, rooms=2, address="-", image=make_test_image(), is_published=True,
            )
            for i in range(4)
        ]

    def _get_csrf_token(self):
        self.client.get(reverse("core:home"))
        return self.client.cookies["csrftoken"].value

    def test_cannot_add_more_than_three_to_compare(self):
        token = self._get_csrf_token()
        for prop in self.properties[:3]:
            self.client.post(reverse("properties:toggle_compare", args=[prop.pk]), HTTP_X_CSRFTOKEN=token)
        # تلاش برای افزودن ملک چهارم
        self.client.post(reverse("properties:toggle_compare", args=[self.properties[3].pk]), HTTP_X_CSRFTOKEN=token)
        session = self.client.session
        self.assertEqual(len(session.get("compare_properties", [])), 3)
