"""
تست‌های خودکار اپ CRM (لاگ فعالیت مشاور).
اجرا: python manage.py test apps.crm
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from apps.team.models import TeamMember

from .models import ActivityLog, Customer, Deal, Task
from .tasks import send_due_activity_reminders


class ActivityLogAccessControlTests(TestCase):
    """مشاور A نباید فعالیت مشاور B را ببیند یا تغییر دهد"""

    def setUp(self):
        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.user_b = User.objects.create_user(username="advisor_b", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=self.user_b)

        self.log_a = ActivityLog.objects.create(advisor=self.advisor_a, activity_type="call", customer_name="مشتری الف")
        self.log_b = ActivityLog.objects.create(advisor=self.advisor_b, activity_type="call", customer_name="مشتری ب")

    def test_advisor_sees_only_own_activity_logs(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:activity_log_list"))
        names = [a.customer_name for a in response.context["activity_logs"]]
        self.assertIn("مشتری الف", names)
        self.assertNotIn("مشتری ب", names)

    def test_advisor_cannot_toggle_other_advisors_activity(self):
        self.client.force_login(self.user_a)
        url = reverse("advisor_panel:activity_log_toggle_done", args=[self.log_b.pk])
        self.client.post(url)
        self.log_b.refresh_from_db()
        self.assertFalse(self.log_b.is_done)  # نباید تغییر کرده باشد

    def test_advisor_can_toggle_own_activity(self):
        self.client.force_login(self.user_a)
        url = reverse("advisor_panel:activity_log_toggle_done", args=[self.log_a.pk])
        self.client.post(url)
        self.log_a.refresh_from_db()
        self.assertTrue(self.log_a.is_done)

    def test_create_activity_log_assigns_current_advisor(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:activity_log_create"), {
            "activity_type": "visit", "customer_name": "مشتری جدید",
            "customer_phone": "", "note": "", "scheduled_at": "", "is_done": "",
        })
        new_log = ActivityLog.objects.get(customer_name="مشتری جدید")
        self.assertEqual(new_log.advisor, self.advisor_a)


class ActivityReminderTaskTests(TestCase):
    """تست تسک Celery یادآوری خودکار"""

    def setUp(self):
        self.user = User.objects.create_user(username="advisor", password="testpass123")
        self.advisor = TeamMember.objects.create(name="مشاور", role="sale", user=self.user)

    def test_sends_reminder_for_activity_due_within_30_minutes(self):
        activity = ActivityLog.objects.create(
            advisor=self.advisor, activity_type="visit", customer_name="مشتری",
            scheduled_at=timezone.now() + timedelta(minutes=10),
        )
        sent_count = send_due_activity_reminders()
        self.assertEqual(sent_count, 1)
        activity.refresh_from_db()
        self.assertTrue(activity.reminder_sent)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)

    def test_does_not_remind_twice(self):
        ActivityLog.objects.create(
            advisor=self.advisor, activity_type="visit", customer_name="مشتری",
            scheduled_at=timezone.now() + timedelta(minutes=10), reminder_sent=True,
        )
        sent_count = send_due_activity_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_activity_without_linked_user(self):
        advisor_no_user = TeamMember.objects.create(name="مشاور بدون حساب", role="sale")
        ActivityLog.objects.create(
            advisor=advisor_no_user, activity_type="visit", customer_name="مشتری",
            scheduled_at=timezone.now() + timedelta(minutes=10),
        )
        sent_count = send_due_activity_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_activity_too_far_in_future(self):
        ActivityLog.objects.create(
            advisor=self.advisor, activity_type="visit", customer_name="مشتری",
            scheduled_at=timezone.now() + timedelta(hours=5),
        )
        sent_count = send_due_activity_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_completed_activity(self):
        ActivityLog.objects.create(
            advisor=self.advisor, activity_type="visit", customer_name="مشتری",
            scheduled_at=timezone.now() + timedelta(minutes=10), is_done=True,
        )
        sent_count = send_due_activity_reminders()
        self.assertEqual(sent_count, 0)


class TaskBoardTests(TestCase):
    """کارتابل وظایف: محول‌کردن توسط مدیر، جداسازی دسترسی بین مشاوران، اعلان خودکار"""

    def setUp(self):
        self.manager = User.objects.create_user(username="manager", password="testpass123", is_staff=True)
        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.user_b = User.objects.create_user(username="advisor_b", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=self.user_b)

    def test_non_staff_cannot_assign_task(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:task_assign"))
        self.assertEqual(response.status_code, 403)

    def test_manager_assigning_task_notifies_assignee(self):
        self.client.force_login(self.manager)
        self.client.post(reverse("advisor_panel:task_assign"), {
            "title": "بازدید فوری از ملک", "description": "", "assignee": self.advisor_a.pk,
            "property": "", "due_date": "",
        })
        task = Task.objects.get(title="بازدید فوری از ملک")
        self.assertEqual(task.assignee, self.advisor_a)
        self.assertEqual(task.assigner, self.manager)
        self.assertEqual(Notification.objects.filter(recipient=self.user_a).count(), 1)

    def test_advisor_sees_only_own_tasks(self):
        Task.objects.create(title="کار الف", assignee=self.advisor_a)
        Task.objects.create(title="کار ب", assignee=self.advisor_b)
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:task_list"))
        titles = [t.title for t in response.context["tasks"]]
        self.assertIn("کار الف", titles)
        self.assertNotIn("کار ب", titles)

    def test_advisor_cannot_update_other_advisors_task_status(self):
        task_b = Task.objects.create(title="کار ب", assignee=self.advisor_b)
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:task_update_status", args=[task_b.pk]), {"status": "done"})
        task_b.refresh_from_db()
        self.assertEqual(task_b.status, "pending")

    def test_advisor_updating_status_notifies_assigner(self):
        task = Task.objects.create(title="کار الف", assignee=self.advisor_a, assigner=self.manager)
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:task_update_status", args=[task.pk]), {"status": "done"})
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertEqual(Notification.objects.filter(recipient=self.manager).count(), 1)

    def test_marking_task_done_sets_completed_at(self):
        task = Task.objects.create(title="کار الف", assignee=self.advisor_a)
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:task_update_status", args=[task.pk]), {"status": "done"})
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)

    def test_reopening_done_task_clears_completed_at(self):
        task = Task.objects.create(title="کار الف", assignee=self.advisor_a)
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:task_update_status", args=[task.pk]), {"status": "done"})
        self.client.post(reverse("advisor_panel:task_update_status", args=[task.pk]), {"status": "in_progress"})
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)


class CustomerSyncSignalTests(TestCase):
    """تست ساخت خودکار پرونده‌ی مشتری هنگام ثبت درخواست تماس/ارزیابی/لاگ فعالیت"""

    def test_contact_request_creates_customer(self):
        from apps.contact.models import ContactRequest

        ContactRequest.objects.create(name="علی رضایی", phone="09121234567", message="سلام")
        customer = Customer.objects.get(phone="09121234567")
        self.assertEqual(customer.name, "علی رضایی")

    def test_valuation_request_creates_customer(self):
        from apps.properties.models import PropertyValuationRequest

        PropertyValuationRequest.objects.create(
            name="مریم احمدی", phone="09121112233", transaction_type="sale", address="-",
        )
        customer = Customer.objects.get(phone="09121112233")
        self.assertEqual(customer.name, "مریم احمدی")

    def test_activity_log_with_phone_creates_customer(self):
        advisor = TeamMember.objects.create(name="مشاور", role="sale")
        ActivityLog.objects.create(
            advisor=advisor, activity_type="call", customer_name="حسین کریمی", customer_phone="09123334455",
        )
        customer = Customer.objects.get(phone="09123334455")
        self.assertEqual(customer.name, "حسین کریمی")

    def test_repeated_contact_from_same_phone_does_not_duplicate_customer(self):
        from apps.contact.models import ContactRequest

        ContactRequest.objects.create(name="علی رضایی", phone="09121234567", message="اول")
        ContactRequest.objects.create(name="", phone="09121234567", message="دوم")
        self.assertEqual(Customer.objects.filter(phone="09121234567").count(), 1)

    def test_activity_log_without_phone_does_not_create_customer(self):
        advisor = TeamMember.objects.create(name="مشاور", role="sale")
        ActivityLog.objects.create(advisor=advisor, activity_type="call", customer_name="بدون شماره")
        self.assertEqual(Customer.objects.count(), 0)


class DealAndCustomerProfileTests(TestCase):
    """قیف فروش: جداسازی دسترسی بین مشاوران + پرونده‌ی یکپارچه مشتری که بین همه مشترک است"""

    def setUp(self):
        self.user_a = User.objects.create_user(username="advisor_a", password="testpass123")
        self.user_b = User.objects.create_user(username="advisor_b", password="testpass123")
        self.advisor_a = TeamMember.objects.create(name="مشاور الف", role="sale", user=self.user_a)
        self.advisor_b = TeamMember.objects.create(name="مشاور ب", role="sale", user=self.user_b)

    def test_create_deal_creates_customer_and_links_advisor(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:deal_create"), {
            "title": "خرید آپارتمان", "customer_name": "رضا قاسمی", "customer_phone": "09121239876",
            "property": "", "value": "", "note": "",
        })
        deal = Deal.objects.get(title="خرید آپارتمان")
        self.assertEqual(deal.advisor, self.advisor_a)
        self.assertEqual(deal.customer.phone, "09121239876")
        self.assertEqual(deal.stage, "new")

    def test_second_deal_with_same_phone_reuses_customer(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:deal_create"), {
            "title": "معامله اول", "customer_name": "رضا قاسمی", "customer_phone": "09121239876",
            "property": "", "value": "", "note": "",
        })
        self.client.post(reverse("advisor_panel:deal_create"), {
            "title": "معامله دوم", "customer_name": "رضا قاسمی", "customer_phone": "09121239876",
            "property": "", "value": "", "note": "",
        })
        self.assertEqual(Customer.objects.filter(phone="09121239876").count(), 1)
        self.assertEqual(Deal.objects.filter(customer__phone="09121239876").count(), 2)

    def test_advisor_sees_only_own_deals_in_kanban(self):
        customer = Customer.objects.create(phone="09121112233", name="مشتری")
        Deal.objects.create(title="فرصت الف", customer=customer, advisor=self.advisor_a)
        Deal.objects.create(title="فرصت ب", customer=customer, advisor=self.advisor_b)
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("advisor_panel:deal_kanban"))
        all_titles = [d.title for col in response.context["columns"] for d in col["deals"]]
        self.assertIn("فرصت الف", all_titles)
        self.assertNotIn("فرصت ب", all_titles)

    def test_advisor_cannot_move_other_advisors_deal(self):
        customer = Customer.objects.create(phone="09121112233", name="مشتری")
        deal_b = Deal.objects.create(title="فرصت ب", customer=customer, advisor=self.advisor_b)
        self.client.force_login(self.user_a)
        self.client.post(reverse("advisor_panel:deal_move_stage", args=[deal_b.pk]), {"stage": "won"})
        deal_b.refresh_from_db()
        self.assertEqual(deal_b.stage, "new")

    def test_customer_profile_aggregates_across_sources(self):
        from apps.contact.models import ContactRequest

        ContactRequest.objects.create(name="سارا محمدی", phone="09129998877", message="سوال داشتم")
        customer = Customer.objects.get(phone="09129998877")
        Deal.objects.create(title="فرصت", customer=customer, advisor=self.advisor_a)
        ActivityLog.objects.create(advisor=self.advisor_a, activity_type="call", customer_phone="09129998877")

        # پرونده مشتری بین همه‌ی مشاوران مشترک است — مشاور ب هم باید بتواند آن را ببیند
        self.client.force_login(self.user_b)
        response = self.client.get(reverse("advisor_panel:customer_profile", args=["09129998877"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deals"]), 1)
        self.assertEqual(len(response.context["contact_requests"]), 1)
        self.assertEqual(len(response.context["activity_logs"]), 1)


class DocumentExpiryReminderTaskTests(TestCase):
    """تست تسک Celery یادآوری انقضای اسناد"""

    def setUp(self):
        from apps.crm.models import Document

        self.Document = Document
        self.user = User.objects.create_user(username="advisor", password="testpass123")
        self.advisor = TeamMember.objects.create(name="مشاور", role="sale", user=self.user)
        self.customer = Customer.objects.create(phone="09121110000", name="مشتری سند")

    def _make_document(self, **kwargs):
        from django.core.files.uploadedfile import SimpleUploadedFile

        defaults = {
            "customer": self.customer, "uploaded_by": self.advisor,
            "file": SimpleUploadedFile("contract.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
        }
        defaults.update(kwargs)
        return self.Document.objects.create(**defaults)

    def test_sends_reminder_for_document_expiring_within_7_days(self):
        from apps.crm.tasks import send_document_expiry_reminders

        document = self._make_document(expiry_date=timezone.localdate() + timedelta(days=3))
        sent_count = send_document_expiry_reminders()
        self.assertEqual(sent_count, 1)
        document.refresh_from_db()
        self.assertTrue(document.expiry_reminder_sent)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)

    def test_does_not_remind_twice(self):
        from apps.crm.tasks import send_document_expiry_reminders

        self._make_document(expiry_date=timezone.localdate() + timedelta(days=3), expiry_reminder_sent=True)
        sent_count = send_document_expiry_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_document_without_uploader_account(self):
        from apps.crm.tasks import send_document_expiry_reminders

        advisor_no_user = TeamMember.objects.create(name="مشاور بدون حساب", role="sale")
        self._make_document(expiry_date=timezone.localdate() + timedelta(days=3), uploaded_by=advisor_no_user)
        sent_count = send_document_expiry_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_document_expiring_far_in_future(self):
        from apps.crm.tasks import send_document_expiry_reminders

        self._make_document(expiry_date=timezone.localdate() + timedelta(days=30))
        sent_count = send_document_expiry_reminders()
        self.assertEqual(sent_count, 0)

    def test_does_not_remind_for_document_without_expiry_date(self):
        from apps.crm.tasks import send_document_expiry_reminders

        self._make_document(expiry_date=None)
        sent_count = send_document_expiry_reminders()
        self.assertEqual(sent_count, 0)


class SatisfactionSurveyTests(TestCase):
    """فرم عمومی نظرسنجی رضایت مشتری (بدون نیاز به ورود)"""

    def setUp(self):
        user = User.objects.create_user(username="advisor", password="testpass123")
        advisor = TeamMember.objects.create(name="مشاور", role="sale", user=user)
        customer = Customer.objects.create(phone="09121110001", name="مشتری")
        self.deal = Deal.objects.create(title="معامله موفق", customer=customer, advisor=advisor, stage="won")

    def test_survey_form_renders_without_login(self):
        response = self.client.get(reverse("crm:survey_submit", args=[self.deal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نظرسنجی رضایت مشتری")

    def test_submitting_survey_creates_record(self):
        response = self.client.post(reverse("crm:survey_submit", args=[self.deal.pk]), {
            "rating": 5, "comment": "عالی بود",
        })
        self.assertEqual(response.status_code, 200)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.survey.rating, 5)
        self.assertEqual(self.deal.survey.comment, "عالی بود")

    def test_cannot_submit_survey_twice_for_same_deal(self):
        self.client.post(reverse("crm:survey_submit", args=[self.deal.pk]), {"rating": 5, "comment": ""})
        response = self.client.post(reverse("crm:survey_submit", args=[self.deal.pk]), {"rating": 1, "comment": "بد"})
        self.assertContains(response, "قبلاً ثبت شده است")
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.survey.rating, 5)
