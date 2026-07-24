"""
تست‌های خودکار اپ تیم (صفحه عمومی معرفی مشاور).
اجرا: python manage.py test apps.team
"""
from django.test import TestCase, Client
from django.urls import reverse

from .models import TeamMember
from apps.properties.models import Property
from apps.properties.tests import make_test_image


class AdvisorDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.advisor = TeamMember.objects.create(name="مشاور تستی", role="sale", is_active=True)
        self.published_property = Property.objects.create(
            title="ملک منتشرشده مشاور", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor, is_published=True,
        )
        self.unpublished_property = Property.objects.create(
            title="ملک منتشرنشده مشاور", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor, is_published=False,
        )

    def test_advisor_page_loads(self):
        response = self.client.get(reverse("team:advisor_detail", args=[self.advisor.pk]))
        self.assertEqual(response.status_code, 200)

    def test_only_published_properties_shown_on_advisor_page(self):
        response = self.client.get(reverse("team:advisor_detail", args=[self.advisor.pk]))
        titles = [p.title for p in response.context["properties"]]
        self.assertIn("ملک منتشرشده مشاور", titles)
        self.assertNotIn("ملک منتشرنشده مشاور", titles)

    def test_inactive_advisor_returns_404(self):
        self.advisor.is_active = False
        self.advisor.save()
        response = self.client.get(reverse("team:advisor_detail", args=[self.advisor.pk]))
        self.assertEqual(response.status_code, 404)
