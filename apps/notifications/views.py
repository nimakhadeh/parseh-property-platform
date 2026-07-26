from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """مرکز اعلان‌ها: لیست کامل و صفحه‌بندی‌شده‌ی اعلان‌های کاربر جاری"""

    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 20
    login_url = "accounts:login"

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


@login_required
def bell_partial(request):
    """ویجت زنگوله در هدر: تعداد نخوانده‌ها + چند اعلان اخیر برای دراپ‌داون"""
    qs = Notification.objects.filter(recipient=request.user)
    return render(request, "notifications/partials/bell.html", {
        "unread_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:8],
    })


@login_required
def go_to_notification(request, pk):
    """کلیک روی یک اعلان: خوانده‌شده علامت می‌زند و به لینک مقصدش هدایت می‌کند"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return HttpResponseRedirect(notification.url or "/")


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
