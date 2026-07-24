"""
تست‌های خودکار پنل مشاور - با تمرکز ویژه روی امنیت (جداسازی دسترسی بین مشاوران).
اجرا: python manage.py test apps.advisor_panel
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from apps.team.models import TeamMember
from apps.properties.models import Property
from apps.properties.tests import make_test_image


class AdvisorPanelAccessControlTests(TestCase):
    """
    مهم‌ترین دسته تست پروژه از نظر امنیتی:
    مشاور A نباید بتواند ملک متعلق به مشاور B را ببیند، ویرایش یا حذف کند.
    """

    def setUp(self):
        self.client = Client()

        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.user_b = User.objects.create_user(username="advisor_b", password="testpass123")

        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=self.user_b)

        self.property_a = Property.objects.create(
            title="ملک مشاور الف", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor_a, is_published=True,
        )
        self.property_b = Property.objects.create(
            title="ملک مشاور ب", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor_b, is_published=True,
        )

    def test_advisor_sees_only_own_properties_in_list(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:property_list"))
        titles = [p.title for p in response.context["properties"]]
        self.assertIn("ملک مشاور الف", titles)
        self.assertNotIn("ملک مشاور ب", titles)

    def test_advisor_cannot_open_edit_page_of_other_advisors_property(self):
        """این حیاتی‌ترین تست پروژه است: دسترسی مستقیم با URL نباید کار کند"""
        self.client.force_login(self.user_a)
        url = reverse("advisor_panel:property_edit", args=[self.property_b.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)  # نباید حتی صفحه را ببیند

    def test_advisor_cannot_delete_other_advisors_property(self):
        self.client.force_login(self.user_a)
        url = reverse("advisor_panel:property_delete", args=[self.property_b.pk])
        self.client.post(url)
        self.property_b.refresh_from_db()
        self.assertTrue(self.property_b.is_published)  # نباید تغییری کرده باشد

    def test_new_property_automatically_assigned_to_creating_advisor(self):
        self.client.force_login(self.user_a)
        response = self.client.post(reverse("advisor_panel:property_create"), {
            "title": "ملک جدید تستی", "description": "-", "price": "1000000000",
            "transaction_type": "sale", "area": "100", "rooms": "2", "floor": "1",
            "total_floors": "5", "address": "تهران", "image": make_test_image(),
            "is_published": "on",
        })
        new_property = Property.objects.get(title="ملک جدید تستی")
        self.assertEqual(new_property.advisor, self.advisor_a)

    def test_user_without_advisor_profile_cannot_access_panel(self):
        random_user = User.objects.create_user(username="randomuser", password="testpass123")
        self.client.force_login(random_user)
        response = self.client.get(reverse("advisor_panel:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("advisor_panel:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_staff_user_can_access_any_advisors_property(self):
        staff_user = User.objects.create_user(username="staffuser", password="testpass123", is_staff=True)
        self.client.force_login(staff_user)
        url = reverse("advisor_panel:property_edit", args=[self.property_a.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ManagerAdvisorPanelTests(TestCase):
    """تست پنل مدیریت مشاوران (فقط برای is_staff)"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username="manager", password="testpass123", is_staff=True)
        self.normal_advisor_user = User.objects.create_user(username="advisor_x", password="testpass123")
        TeamMember.objects.create(name="مشاور ایکس", role="sale", user=self.normal_advisor_user)

    def test_staff_can_access_manager_panel(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:manager_advisor_list"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_advisor_cannot_access_manager_panel(self):
        self.client.force_login(self.normal_advisor_user)
        response = self.client.get(reverse("advisor_panel:manager_advisor_list"))
        self.assertEqual(response.status_code, 403)

    def test_toggle_active_status(self):
        self.client.force_login(self.staff_user)
        advisor = TeamMember.objects.get(name="مشاور ایکس")
        self.assertTrue(advisor.is_active)
        self.client.post(reverse("advisor_panel:manager_advisor_toggle", args=[advisor.pk]))
        advisor.refresh_from_db()
        self.assertFalse(advisor.is_active)
