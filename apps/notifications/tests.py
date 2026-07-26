"""
تست‌های خودکار اپ اعلان‌ها.
اجرا: python manage.py test apps.notifications
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Notification
from .services import notify, notify_many


class NotifyServiceTests(TestCase):
    """تست تابع مشترک notify() که سایر اپ‌ها برای ساخت اعلان صدا می‌زنند"""

    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")

    def test_notify_creates_notification(self):
        notify(self.user, "پیام تستی", url="/some-url/")
        self.assertEqual(Notification.objects.count(), 1)
        n = Notification.objects.first()
        self.assertEqual(n.recipient, self.user)
        self.assertEqual(n.message, "پیام تستی")
        self.assertFalse(n.is_read)

    def test_notify_links_related_object_via_generic_fk(self):
        other_user = User.objects.create_user(username="u2", password="pass12345")
        n = notify(self.user, "مرتبط با یک کاربر دیگر", related_object=other_user)
        self.assertEqual(n.related_object, other_user)

    def test_notify_many_creates_one_per_recipient(self):
        user2 = User.objects.create_user(username="u2", password="pass12345")
        notify_many([self.user, user2], "اعلان گروهی")
        self.assertEqual(Notification.objects.count(), 2)


class NotificationViewsTests(TestCase):
    """تست ویوهای زنگوله، لیست، و علامت‌گذاری خوانده‌شده"""

    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")
        self.other_user = User.objects.create_user(username="u2", password="pass12345")

    def test_bell_partial_requires_login(self):
        response = self.client.get(reverse("notifications:bell_partial"))
        self.assertEqual(response.status_code, 302)  # ریدایرکت به صفحه‌ی ورود

    def test_bell_partial_shows_correct_unread_count(self):
        notify(self.user, "یک")
        notify(self.user, "دو")
        n3 = notify(self.user, "سه")
        n3.is_read = True
        n3.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications:bell_partial"))
        self.assertEqual(response.context["unread_count"], 2)

    def test_go_to_notification_marks_read_and_redirects(self):
        n = notify(self.user, "پیام", url="/test-target/")
        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications:go", args=[n.pk]))
        self.assertRedirects(response, "/test-target/", fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_user_cannot_read_another_users_notification(self):
        """یک کاربر نباید بتواند با حدس‌زدن pk، اعلان کاربر دیگری را باز کند"""
        n = notify(self.other_user, "محرمانه")
        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications:go", args=[n.pk]))
        self.assertEqual(response.status_code, 404)

    def test_mark_all_read_only_affects_current_user(self):
        notify(self.user, "یک")
        notify(self.user, "دو")
        notify(self.other_user, "برای کاربر دیگر")
        self.client.force_login(self.user)
        self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.other_user, is_read=False).count(), 1)

    def test_notification_list_only_shows_own_notifications(self):
        notify(self.user, "مال من")
        notify(self.other_user, "مال کاربر دیگر")
        self.client.force_login(self.user)
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(len(response.context["notifications"]), 1)
        self.assertEqual(response.context["notifications"][0].message, "مال من")
