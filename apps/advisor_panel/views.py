"""
پنل مدیریت اختصاصی مشاوران:
- هر مشاور فقط ملک‌های خودش را می‌بیند/ویرایش می‌کند
- درخواست‌های تماس مربوط به ملک‌های خودش را مدیریت می‌کند
- کارمندان (is_staff) به همه‌ی ملک‌ها دسترسی دارند (برای پشتیبانی)
"""
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View
from django.db import transaction
from django.db.models import Count, Q

from apps.properties.models import Property, PropertyValuationRequest
from apps.contact.models import ContactRequest
from apps.team.models import TeamMember
from .forms import AdvisorPropertyForm, ManagerAdvisorForm
from .mixins import AdvisorRequiredMixin, ManagerRequiredMixin


class AdvisorDashboardView(AdvisorRequiredMixin, TemplateView):
    """داشبورد اصلی مشاور: خلاصه آماری از ملک‌ها و درخواست‌های تماس"""

    template_name = "advisor_panel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        advisor = self.get_advisor()
        properties = Property.objects.all() if self.request.user.is_staff and not advisor else Property.objects.filter(advisor=advisor)

        context["advisor"] = advisor
        context["total_properties"] = properties.count()
        context["published_count"] = properties.filter(is_published=True).count()
        context["total_views"] = sum(p.views_count for p in properties)
        context["top_properties"] = properties.order_by("-views_count")[:5]

        contact_qs = ContactRequest.objects.filter(property__in=properties) if not (self.request.user.is_staff and not advisor) else ContactRequest.objects.all()
        context["unread_requests_count"] = contact_qs.filter(is_read=False).count()
        context["recent_requests"] = contact_qs.select_related("property").order_by("-created_at")[:5]

        context["pending_valuation_count"] = PropertyValuationRequest.objects.filter(status="pending").count()
        return context


class AdvisorPropertyListView(AdvisorRequiredMixin, ListView):
    """لیست ملک‌های مشاور جاری"""

    model = Property
    template_name = "advisor_panel/property_list.html"
    context_object_name = "properties"
    paginate_by = 10

    def get_queryset(self):
        advisor = self.get_advisor()
        qs = Property.objects.all() if (self.request.user.is_staff and not advisor) else Property.objects.filter(advisor=advisor)
        return qs.order_by("-created_at")


class AdvisorPropertyCreateView(AdvisorRequiredMixin, CreateView):
    """افزودن ملک جدید توسط مشاور"""

    model = Property
    form_class = AdvisorPropertyForm
    template_name = "advisor_panel/property_form.html"
    success_url = reverse_lazy("advisor_panel:property_list")

    def form_valid(self, form):
        advisor = self.get_advisor()
        if advisor is None:
            messages.error(self.request, "حساب شما به هیچ مشاوری متصل نیست؛ امکان افزودن ملک وجود ندارد.")
            return redirect("advisor_panel:dashboard")
        form.instance.advisor = advisor
        messages.success(self.request, "ملک جدید با موفقیت ثبت شد.")
        return super().form_valid(form)


class AdvisorPropertyUpdateView(AdvisorRequiredMixin, UpdateView):
    """ویرایش ملک متعلق به مشاور جاری"""

    model = Property
    form_class = AdvisorPropertyForm
    template_name = "advisor_panel/property_form.html"
    success_url = reverse_lazy("advisor_panel:property_list")

    def get_queryset(self):
        advisor = self.get_advisor()
        # مشاور فقط به ملک‌های خودش دسترسی دارد؛ staff بدون پروفایل مشاور به همه دسترسی دارد
        if self.request.user.is_staff and not advisor:
            return Property.objects.all()
        return Property.objects.filter(advisor=advisor)

    def form_valid(self, form):
        messages.success(self.request, "تغییرات ملک با موفقیت ذخیره شد.")
        return super().form_valid(form)


class AdvisorPropertyDeleteView(AdvisorRequiredMixin, View):
    """
    'حذف' ملک توسط مشاور - در واقع فقط از حالت انتشار خارج می‌شود (حذف نرم)
    تا سابقه بازدید/علاقه‌مندی/درخواست‌های تماس مرتبط از بین نروند.
    """

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = Property.objects.all() if (request.user.is_staff and not advisor) else Property.objects.filter(advisor=advisor)
        property_obj = get_object_or_404(qs, pk=pk)
        property_obj.is_published = False
        property_obj.save(update_fields=["is_published"])
        messages.success(request, f"ملک «{property_obj.title}» از انتشار خارج شد.")
        return redirect("advisor_panel:property_list")


class AdvisorContactRequestsView(AdvisorRequiredMixin, ListView):
    """درخواست‌های تماس مربوط به ملک‌های مشاور جاری"""

    model = ContactRequest
    template_name = "advisor_panel/contact_requests.html"
    context_object_name = "requests"
    paginate_by = 15

    def get_queryset(self):
        advisor = self.get_advisor()
        qs = ContactRequest.objects.all() if (self.request.user.is_staff and not advisor) else ContactRequest.objects.filter(property__advisor=advisor)
        return qs.select_related("property").order_by("-created_at")


class MarkContactRequestReadView(AdvisorRequiredMixin, View):
    """علامت‌گذاری یک درخواست تماس به‌عنوان خوانده‌شده"""

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = ContactRequest.objects.all() if (request.user.is_staff and not advisor) else ContactRequest.objects.filter(property__advisor=advisor)
        contact_request = get_object_or_404(qs, pk=pk)
        contact_request.is_read = True
        contact_request.save(update_fields=["is_read"])
        return redirect("advisor_panel:contact_requests")


class ValuationRequestQueueView(AdvisorRequiredMixin, ListView):
    """
    صف درخواست‌های ارزیابی ملک: درخواست‌های 'در انتظار بررسی' برای همه‌ی مشاوران قابل مشاهده است
    (چون هنوز مشخص نیست کدام مشاور آن را پیگیری می‌کند)، به‌همراه درخواست‌هایی که مشاور جاری بر عهده گرفته است.
    """

    model = PropertyValuationRequest
    template_name = "advisor_panel/valuation_queue.html"
    context_object_name = "valuation_requests"
    paginate_by = 15

    def get_queryset(self):
        advisor = self.get_advisor()
        if self.request.user.is_staff and not advisor:
            return PropertyValuationRequest.objects.select_related("assigned_advisor").all().order_by("-created_at")
        return PropertyValuationRequest.objects.select_related("assigned_advisor").filter(
            Q(status="pending") | Q(assigned_advisor=advisor)
        ).order_by("-created_at")


class ClaimValuationRequestView(AdvisorRequiredMixin, View):
    """مشاور یک درخواست ارزیابی را برای پیگیری به نام خودش برمی‌دارد"""

    def post(self, request, pk):
        advisor = self.get_advisor()
        if advisor is None:
            messages.error(request, "حساب شما به هیچ مشاوری متصل نیست.")
            return redirect("advisor_panel:valuation_queue")
        with transaction.atomic():
            claimed = PropertyValuationRequest.objects.filter(
                pk=pk,
                status="pending",
                assigned_advisor__isnull=True,
            ).update(
                assigned_advisor=advisor,
                status="reviewed",
            )

        if claimed:
            messages.success(request, "درخواست برای پیگیری به شما اختصاص یافت.")
        else:
            messages.warning(request, "این درخواست قبلاً توسط مشاور دیگری دریافت شده است.")
        return redirect("advisor_panel:valuation_queue")


class UpdateValuationRequestStatusView(AdvisorRequiredMixin, View):
    """به‌روزرسانی وضعیت یک درخواست ارزیابی (فقط توسط مشاور مسئول یا staff)"""

    VALID_STATUSES = {choice[0] for choice in PropertyValuationRequest.STATUS_CHOICES}

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = PropertyValuationRequest.objects.all() if (request.user.is_staff and not advisor) else PropertyValuationRequest.objects.filter(assigned_advisor=advisor)
        valuation_request = get_object_or_404(qs, pk=pk)

        new_status = request.POST.get("status")
        if new_status in self.VALID_STATUSES:
            valuation_request.status = new_status
            valuation_request.save(update_fields=["status"])
            messages.success(request, "وضعیت درخواست به‌روزرسانی شد.")
        return redirect("advisor_panel:valuation_queue")


# =============================================================================
# مدیریت مشاوران (فقط برای مدیر مجموعه - is_staff)
# =============================================================================

class ManagerAdvisorListView(ManagerRequiredMixin, ListView):
    """لیست همه‌ی مشاوران برای مدیریت توسط مدیر مجموعه"""

    model = TeamMember
    template_name = "advisor_panel/manager_advisor_list.html"
    context_object_name = "advisors"

    def get_queryset(self):
        return (
            TeamMember.objects.all()
            .select_related("user")
            .annotate(property_count=Count("properties", distinct=True))
            .order_by("order", "name")
        )


class ManagerAdvisorCreateView(ManagerRequiredMixin, CreateView):
    """افزودن مشاور جدید توسط مدیر مجموعه"""

    model = TeamMember
    form_class = ManagerAdvisorForm
    template_name = "advisor_panel/manager_advisor_form.html"
    success_url = reverse_lazy("advisor_panel:manager_advisor_list")

    def form_valid(self, form):
        messages.success(self.request, "مشاور جدید با موفقیت اضافه شد.")
        return super().form_valid(form)


class ManagerAdvisorUpdateView(ManagerRequiredMixin, UpdateView):
    """ویرایش اطلاعات مشاور توسط مدیر مجموعه"""

    model = TeamMember
    form_class = ManagerAdvisorForm
    template_name = "advisor_panel/manager_advisor_form.html"
    success_url = reverse_lazy("advisor_panel:manager_advisor_list")

    def form_valid(self, form):
        messages.success(self.request, "تغییرات مشاور با موفقیت ذخیره شد.")
        return super().form_valid(form)


class ManagerAdvisorToggleActiveView(ManagerRequiredMixin, View):
    """فعال/غیرفعال کردن سریع یک مشاور (بدون حذف - برای حفظ سابقه ملک‌ها)"""

    def post(self, request, pk):
        advisor = get_object_or_404(TeamMember, pk=pk)
        advisor.is_active = not advisor.is_active
        advisor.save(update_fields=["is_active"])
        status = "فعال" if advisor.is_active else "غیرفعال"
        messages.success(request, f"مشاور «{advisor.name}» {status} شد.")
        return redirect("advisor_panel:manager_advisor_list")
