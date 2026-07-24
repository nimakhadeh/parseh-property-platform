"""ویوهای عمومی صفحه‌ی ثبت درخواست ارزیابی آنلاین ملک"""
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .valuation_forms import PropertyValuationRequestForm


class ValuationRequestPageView(TemplateView):
    """صفحه معرفی + فرم ثبت درخواست ارزیابی ملک"""

    template_name = "properties/valuation_request.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = {}
        if self.request.user.is_authenticated:
            initial["name"] = self.request.user.get_full_name() or self.request.user.username
            initial["email"] = self.request.user.email
            profile = getattr(self.request.user, "profile", None)
            if profile and profile.phone:
                initial["phone"] = profile.phone
        context["form"] = PropertyValuationRequestForm(initial=initial)
        return context


@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=False), name="dispatch")
class ValuationRequestCreateView(CreateView):
    """ثبت درخواست ارزیابی ملک (پشتیبانی HTMX + rate limit + هانی‌پات ضداسپم)"""

    form_class = PropertyValuationRequestForm
    template_name = "properties/partials/valuation_request_result.html"
    success_url = reverse_lazy("properties:valuation_request")

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return self.render_to_response({"rate_limited": True})
        # هانی‌پات: کاربران واقعی این فیلد مخفی را پر نمی‌کنند، فقط ربات‌ها
        if request.POST.get("website"):
            return self.render_to_response({"success": True})
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        try:
            from .tasks import notify_new_valuation_request_task
            notify_new_valuation_request_task.delay(self.object.pk)
        except Exception:
            from .valuation_notify import notify_new_valuation_request
            notify_new_valuation_request(self.object)
        return self.render_to_response(self.get_context_data(success=True))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form, success=False))
