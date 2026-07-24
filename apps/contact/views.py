from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .forms import ContactRequestForm


class ContactPageView(TemplateView):
    """صفحه تماس با ما"""

    template_name = "core/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = {}
        if self.request.user.is_authenticated:
            initial["name"] = self.request.user.get_full_name() or self.request.user.username
            initial["email"] = self.request.user.email
            profile = getattr(self.request.user, "profile", None)
            if profile and profile.phone:
                initial["phone"] = profile.phone
        context["form"] = ContactRequestForm(initial=initial)
        return context


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=False), name="dispatch")
class ContactCreateView(CreateView):
    """
    ثبت فرم تماس (پشتیبانی HTMX).
    محدود به ۱۰ درخواست در ساعت برای هر IP، به‌علاوه یک فیلد هانی‌پات نامرئی
    برای مسدود کردن ربات‌های اسپم که فرم‌ها را به‌صورت خودکار پر می‌کنند.
    """

    form_class = ContactRequestForm
    template_name = "core/partials/contact_form_result.html"
    success_url = reverse_lazy("contact:contact_page")

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return self.render_to_response({
                "success": False,
                "rate_limited": True,
            })
        # هانی‌پات: کاربران واقعی این فیلد مخفی را پر نمی‌کنند، فقط ربات‌ها
        if request.POST.get("website"):
            return self.render_to_response({"success": True})
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.request.user.is_authenticated:
            self.object.user = self.request.user
        self.object.save()
        try:
            from .tasks import notify_new_contact_request_task
            notify_new_contact_request_task.delay(self.object.pk)
        except Exception:
            # اگر Celery/Redis در دسترس نبود، به‌صورت همزمان (و بی‌خطر) تلاش می‌کنیم
            from .telegram_notify import notify_new_contact_request
            notify_new_contact_request(self.object)
        return self.render_to_response(self.get_context_data(success=True))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form, success=False))
