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


class CalendarAndTodayMapTests(TestCase):
    """تست تقویم (دسترسی هر مشاور به فعالیت‌های خودش) و نقشه‌ی امروز مدیر (فقط staff، فیلتر بر اساس مختصات)"""

    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.crm.models import ActivityLog

        self.timezone = timezone
        self.timedelta = timedelta
        self.ActivityLog = ActivityLog

        self.staff_user = User.objects.create_user(username="manager", password="testpass123", is_staff=True)
        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.user_b = User.objects.create_user(username="advisor_b", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=self.user_b)

        self.property_with_coords = Property.objects.create(
            title="ملک با مختصات", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor_a, is_published=True, latitude=35.7, longitude=51.4,
        )
        self.property_without_coords = Property.objects.create(
            title="ملک بدون مختصات", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor_b, is_published=True,
        )

    def test_advisor_calendar_shows_only_own_scheduled_activities(self):
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="visit", customer_name="مشتری الف",
            scheduled_at=self.timezone.now() + self.timedelta(hours=1),
        )
        self.ActivityLog.objects.create(
            advisor=self.advisor_b, activity_type="visit", customer_name="مشتری ب",
            scheduled_at=self.timezone.now() + self.timedelta(hours=1),
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:calendar"))
        all_names = [a.customer_name for _, items in response.context["grouped_activities"] for a in items]
        self.assertIn("مشتری الف", all_names)
        self.assertNotIn("مشتری ب", all_names)

    def test_non_staff_cannot_access_today_map(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:today_map"))
        self.assertEqual(response.status_code, 403)

    def test_today_map_only_includes_property_linked_activities_with_coords(self):
        today_now = self.timezone.now()
        # این یکی باید روی نقشه باشد: امروز، ملک دارد، ملک مختصات دارد
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="visit", property=self.property_with_coords,
            customer_name="بازدید قابل نمایش", scheduled_at=today_now,
        )
        # این یکی نباید باشد: ملک مختصات ندارد
        self.ActivityLog.objects.create(
            advisor=self.advisor_b, activity_type="visit", property=self.property_without_coords,
            customer_name="بازدید بدون مختصات", scheduled_at=today_now,
        )
        # این یکی نباید باشد: اصلاً به ملکی متصل نیست
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="call", customer_name="تماس بدون ملک", scheduled_at=today_now,
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:today_map"))
        titles = [p["title"] for p in response.context["points"]]
        self.assertEqual(titles, ["ملک با مختصات"])

    def test_calendar_groups_by_local_date_not_utc_date(self):
        """
        باگ واقعی: scheduled_at در UTC ذخیره می‌شود؛ ساعت ۰۰:۵۶ به وقت محلی (آسیا/تهران، +۳:۳۰)
        معادل ۲۱:۲۶ روز قبل به وقت UTC است. گروه‌بندی باید بر اساس تاریخ محلی باشد، نه UTC.
        """
        from datetime import datetime, timezone as dt_timezone

        # ساعت ۲۱:۲۶ به وقت UTC == ساعت ۰۰:۵۶ روز بعد به وقت محلی تهران (+۰۳:۳۰)
        utc_time = datetime(2026, 7, 25, 21, 26, 0, tzinfo=dt_timezone.utc)
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="visit", customer_name="بازدید نیمه‌شب",
            scheduled_at=utc_time,
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:calendar"))
        grouped_days = [day for day, _ in response.context["grouped_activities"]]
        self.assertIn(self.timezone.localtime(utc_time).date(), grouped_days)
        self.assertNotIn(utc_time.date(), grouped_days)

    def test_today_map_js_values_are_quoted_strings(self):
        """همان باگ گیومه‌ی map.html در today_map.html هم وجود داشت؛ اینجا هم گارد می‌کنیم"""
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="visit", property=self.property_with_coords,
            customer_name="بازدید", scheduled_at=self.timezone.now(),
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:today_map"))
        content = response.content.decode()
        self.assertIn('title: "', content)
        self.assertIn('advisor_name: "', content)


class AdvisorPerformanceTests(TestCase):
    """جدول امتیاز مشاوران، SLA پاسخ‌دهی، و نقشه حرارتی فعالیت (فقط مدیر مجموعه)"""

    def setUp(self):
        from django.utils import timezone

        from apps.contact.models import ContactRequest
        from apps.crm.models import ActivityLog, Deal, Task

        self.timezone = timezone
        self.ActivityLog = ActivityLog
        self.Task = Task
        self.Deal = Deal
        self.ContactRequest = ContactRequest

        self.staff_user = User.objects.create_user(username="manager", password="testpass123", is_staff=True)
        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)

        self.property_a = Property.objects.create(
            title="ملک مشاور الف", description="-", price=100, transaction_type="sale",
            area=80, rooms=2, address="-", image=make_test_image(),
            advisor=self.advisor_a, is_published=True,
        )

    def test_non_staff_cannot_access_performance_dashboard(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:performance"))
        self.assertEqual(response.status_code, 403)

    def test_leaderboard_score_combines_activities_tasks_and_won_deals(self):
        self.ActivityLog.objects.create(advisor=self.advisor_a, activity_type="call", customer_name="ت۱")
        self.ActivityLog.objects.create(advisor=self.advisor_a, activity_type="call", customer_name="ت۲")

        done_task = self.Task.objects.create(title="کار", assignee=self.advisor_a, status="done")
        done_task.completed_at = self.timezone.now()
        done_task.save(update_fields=["completed_at"])

        from apps.crm.models import Customer
        customer = Customer.objects.create(phone="09121230000", name="مشتری")
        self.Deal.objects.create(title="معامله", customer=customer, advisor=self.advisor_a, stage="won")

        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:performance"))
        row = next(r for r in response.context["leaderboard"] if r["advisor"] == self.advisor_a)
        self.assertEqual(row["activities"], 2)
        self.assertEqual(row["tasks_done"], 1)
        self.assertEqual(row["deals_won"], 1)
        self.assertEqual(row["score"], 2 * 1 + 1 * 2 + 1 * 10)

    def test_sla_counts_pending_lead_with_no_activity_log(self):
        self.ContactRequest.objects.create(
            name="مشتری", phone="09121230001", message="سلام", property=self.property_a,
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:performance"))
        row = next(r for r in response.context["sla_rows"] if r["advisor"] == self.advisor_a)
        self.assertEqual(row["total_leads"], 1)
        self.assertEqual(row["pending"], 1)
        self.assertEqual(row["responded"], 0)
        self.assertIsNone(row["avg_hours"])

    def test_sla_computes_response_time_from_matching_activity_log(self):
        contact = self.ContactRequest.objects.create(
            name="مشتری", phone="09121230002", message="سلام", property=self.property_a,
        )
        self.ActivityLog.objects.create(
            advisor=self.advisor_a, activity_type="call", customer_phone="09121230002",
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:performance"))
        row = next(r for r in response.context["sla_rows"] if r["advisor"] == self.advisor_a)
        self.assertEqual(row["responded"], 1)
        self.assertEqual(row["pending"], 0)
        self.assertIsNotNone(row["avg_hours"])
        self.assertGreaterEqual(row["avg_hours"], 0)

    def test_heatmap_includes_today_with_correct_count(self):
        self.ActivityLog.objects.create(advisor=self.advisor_a, activity_type="visit", customer_name="ت۱")
        self.ActivityLog.objects.create(advisor=self.advisor_a, activity_type="visit", customer_name="ت۲")
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:performance"))
        today = self.timezone.localdate()
        today_cell = None
        for week in response.context["heatmap_weeks"]:
            for day in week:
                if day and day["date"] == today:
                    today_cell = day
        self.assertIsNotNone(today_cell)
        self.assertEqual(today_cell["count"], 2)
        self.assertEqual(today_cell["level"], 1)

    def test_heatmap_filters_by_selected_advisor(self):
        user_b = User.objects.create_user(username="advisor_b", password="testpass123")
        advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=user_b)
        self.ActivityLog.objects.create(advisor=advisor_b, activity_type="visit", customer_name="ت۱")
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("advisor_panel:performance"), {"advisor": self.advisor_a.pk})
        today = self.timezone.localdate()
        today_cell = None
        for week in response.context["heatmap_weeks"]:
            for day in week:
                if day and day["date"] == today:
                    today_cell = day
        self.assertEqual(today_cell["count"], 0)


class DocumentUploadTests(TestCase):
    """آپلود سند برای پرونده‌ی مشتری از صفحه‌ی پروفایل مشتری"""

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.crm.models import Customer, Document

        self.SimpleUploadedFile = SimpleUploadedFile
        self.Document = Document

        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.customer = Customer.objects.create(phone="09121110002", name="مشتری سند")

    def test_advisor_can_upload_document_for_customer(self):
        self.client.force_login(self.user_a)
        pdf = self.SimpleUploadedFile("contract.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        response = self.client.post(
            reverse("advisor_panel:document_upload", args=[self.customer.phone]),
            {"document_type": "contract", "title": "قرارداد اجاره", "file": pdf, "expiry_date": ""},
        )
        self.assertRedirects(response, reverse("advisor_panel:customer_profile", args=[self.customer.phone]))
        document = self.Document.objects.get(customer=self.customer)
        self.assertEqual(document.uploaded_by, self.advisor_a)
        self.assertEqual(document.document_type, "contract")

    def test_document_upload_rejects_disallowed_extension(self):
        self.client.force_login(self.user_a)
        malicious = self.SimpleUploadedFile("script.exe", b"MZ fake binary", content_type="application/octet-stream")
        self.client.post(
            reverse("advisor_panel:document_upload", args=[self.customer.phone]),
            {"document_type": "other", "title": "", "file": malicious, "expiry_date": ""},
        )
        self.assertEqual(self.Document.objects.filter(customer=self.customer).count(), 0)

    def test_customer_profile_lists_uploaded_documents(self):
        pdf = self.SimpleUploadedFile("deed.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
        self.Document.objects.create(
            customer=self.customer, uploaded_by=self.advisor_a, document_type="ownership_deed", file=pdf,
        )
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:customer_profile", args=[self.customer.phone]))
        self.assertEqual(len(response.context["documents"]), 1)
        self.assertContains(response, "سند مالکیت")
