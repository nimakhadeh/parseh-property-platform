"""
پنل مدیریت اختصاصی مشاوران:
- هر مشاور فقط ملک‌های خودش را می‌بیند/ویرایش می‌کند
- درخواست‌های تماس مربوط به ملک‌های خودش را مدیریت می‌کند
- کارمندان (is_staff) به همه‌ی ملک‌ها دسترسی دارند (برای پشتیبانی)
"""
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View, FormView
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from apps.crm.models import ActivityLog, Customer, Deal, Document, Task
from apps.notifications.services import notify
from apps.properties.models import Property, PropertyValuationRequest
from apps.contact.models import ContactRequest
from apps.team.models import TeamMember
from .forms import ActivityLogForm, AdvisorPropertyForm, DealForm, DocumentUploadForm, ManagerAdvisorForm, TaskAssignForm
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
        valuation_request = get_object_or_404(PropertyValuationRequest, pk=pk)
        valuation_request.assigned_advisor = advisor
        valuation_request.status = "reviewed"
        valuation_request.save(update_fields=["assigned_advisor", "status"])
        messages.success(request, "درخواست برای پیگیری به شما اختصاص یافت.")
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


class ActivityLogListView(AdvisorRequiredMixin, ListView):
    """لاگ فعالیت‌های مشاور جاری (یا همه‌ی فعالیت‌ها برای staff پشتیبان)"""

    model = ActivityLog
    template_name = "advisor_panel/activity_log_list.html"
    context_object_name = "activity_logs"
    paginate_by = 15

    def get_queryset(self):
        advisor = self.get_advisor()
        qs = ActivityLog.objects.all() if (self.request.user.is_staff and not advisor) else ActivityLog.objects.filter(advisor=advisor)
        return qs.select_related("advisor", "property")


class ActivityLogCreateView(AdvisorRequiredMixin, CreateView):
    """ثبت سریع یک لاگ فعالیت جدید توسط مشاور"""

    model = ActivityLog
    form_class = ActivityLogForm
    template_name = "advisor_panel/activity_log_form.html"
    success_url = reverse_lazy("advisor_panel:activity_log_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["advisor"] = self.get_advisor()
        return kwargs

    def form_valid(self, form):
        advisor = self.get_advisor()
        if advisor is None:
            messages.error(self.request, "حساب شما به هیچ مشاوری متصل نیست؛ امکان ثبت فعالیت وجود ندارد.")
            return redirect("advisor_panel:dashboard")
        form.instance.advisor = advisor
        messages.success(self.request, "فعالیت با موفقیت ثبت شد.")
        return super().form_valid(form)


class ActivityLogToggleDoneView(AdvisorRequiredMixin, View):
    """علامت‌گذاری سریع یک فعالیت به‌عنوان انجام‌شده/نشده"""

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = ActivityLog.objects.all() if (request.user.is_staff and not advisor) else ActivityLog.objects.filter(advisor=advisor)
        activity = get_object_or_404(qs, pk=pk)
        activity.is_done = not activity.is_done
        activity.save(update_fields=["is_done"])
        return redirect("advisor_panel:activity_log_list")


class TaskListView(AdvisorRequiredMixin, ListView):
    """کارتابل وظایف: مشاور وظایف محول‌شده به خودش را می‌بیند، مدیر همه را می‌بیند"""

    model = Task
    template_name = "advisor_panel/task_list.html"
    context_object_name = "tasks"
    paginate_by = 15

    def get_queryset(self):
        advisor = self.get_advisor()
        qs = Task.objects.all() if (self.request.user.is_staff and not advisor) else Task.objects.filter(assignee=advisor)
        return qs.select_related("assignee", "assigner", "property")


class TaskAssignView(ManagerRequiredMixin, CreateView):
    """محول‌کردن وظیفه‌ی جدید به یک مشاور (فقط مدیر مجموعه)"""

    model = Task
    form_class = TaskAssignForm
    template_name = "advisor_panel/task_form.html"
    success_url = reverse_lazy("advisor_panel:task_list")

    def form_valid(self, form):
        form.instance.assigner = self.request.user
        response = super().form_valid(form)
        if self.object.assignee.user_id:
            notify(
                self.object.assignee.user,
                f"وظیفه‌ی جدید به شما محول شد: {self.object.title}",
                url=reverse_lazy("advisor_panel:task_list"),
                actor=self.request.user,
                related_object=self.object,
            )
        messages.success(self.request, "وظیفه با موفقیت محول شد.")
        return response


class TaskUpdateStatusView(AdvisorRequiredMixin, View):
    """تغییر وضعیت یک وظیفه توسط مشاور مسئول (یا staff برای پشتیبانی)"""

    VALID_STATUSES = {choice[0] for choice in Task.STATUS_CHOICES}

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = Task.objects.all() if (request.user.is_staff and not advisor) else Task.objects.filter(assignee=advisor)
        task = get_object_or_404(qs, pk=pk)
        new_status = request.POST.get("status")
        if new_status in self.VALID_STATUSES:
            task.status = new_status
            task.completed_at = timezone.now() if new_status == "done" else None
            task.save(update_fields=["status", "completed_at"])
            if task.assigner_id:
                notify(
                    task.assigner,
                    f"وضعیت وظیفه‌ی «{task.title}» به «{task.get_status_display()}» تغییر کرد",
                    url=reverse_lazy("advisor_panel:task_list"),
                    actor=request.user,
                    related_object=task,
                )
            messages.success(request, "وضعیت وظیفه به‌روزرسانی شد.")
        return redirect("advisor_panel:task_list")


class CalendarView(AdvisorRequiredMixin, TemplateView):
    """تقویم فعالیت‌های برنامه‌ریزی‌شده: گروه‌بندی‌شده بر اساس تاریخ"""

    template_name = "advisor_panel/calendar.html"

    def get_context_data(self, **kwargs):
        from itertools import groupby

        context = super().get_context_data(**kwargs)
        advisor = self.get_advisor()
        qs = ActivityLog.objects.all() if (self.request.user.is_staff and not advisor) else ActivityLog.objects.filter(advisor=advisor)
        activities = qs.filter(scheduled_at__isnull=False).select_related("advisor", "property").order_by("scheduled_at")

        grouped = []
        for day, items in groupby(activities, key=lambda a: timezone.localtime(a.scheduled_at).date()):
            grouped.append((day, list(items)))
        context["grouped_activities"] = grouped
        return context


ADVISOR_MAP_COLORS = ["#0E5D50", "#C68A3D", "#B6512E", "#3B82F6", "#8B5CF6", "#EC4899", "#059669", "#DC2626"]


class TodayMapView(ManagerRequiredMixin, TemplateView):
    """نقشه‌ی امروز مدیر: همه‌ی بازدیدهای امروز که به یک ملک (و مختصات) متصل‌اند، رنگی به‌ازای هر مشاور"""

    template_name = "advisor_panel/today_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        activities = ActivityLog.objects.filter(
            scheduled_at__date=today,
            property__isnull=False,
            property__latitude__isnull=False,
            property__longitude__isnull=False,
        ).select_related("advisor", "property").order_by("scheduled_at")

        advisor_colors = {}
        points = []
        for activity in activities:
            if activity.advisor_id not in advisor_colors:
                advisor_colors[activity.advisor_id] = ADVISOR_MAP_COLORS[len(advisor_colors) % len(ADVISOR_MAP_COLORS)]
            points.append({
                "lat": activity.property.latitude,
                "lng": activity.property.longitude,
                "title": activity.property.title,
                "advisor_name": activity.advisor.name,
                "activity_type": activity.get_activity_type_display(),
                "time": timezone.localtime(activity.scheduled_at).strftime("%H:%M"),
                "url": activity.property.get_absolute_url(),
                "color": advisor_colors[activity.advisor_id],
            })

        context["points"] = points
        context["advisor_legend"] = [
            {"name": TeamMember.objects.get(pk=advisor_id).name, "color": color}
            for advisor_id, color in advisor_colors.items()
        ]
        return context


class DealKanbanView(AdvisorRequiredMixin, TemplateView):
    """قیف فروش به‌صورت کانبان: هر مشاور فرصت‌های خودش را می‌بیند، staff همه را می‌بیند"""

    template_name = "advisor_panel/deal_kanban.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        advisor = self.get_advisor()
        qs = Deal.objects.all() if (self.request.user.is_staff and not advisor) else Deal.objects.filter(advisor=advisor)
        qs = qs.select_related("customer", "property", "advisor")

        columns = []
        for value, label in Deal.STAGE_CHOICES:
            columns.append({"value": value, "label": label, "deals": [d for d in qs if d.stage == value]})
        context["columns"] = columns
        return context


class DealCreateView(AdvisorRequiredMixin, FormView):
    """ثبت فرصت فروش جدید (مشتری با شماره تلفن پیدا یا ساخته می‌شود)"""

    form_class = DealForm
    template_name = "advisor_panel/deal_form.html"
    success_url = reverse_lazy("advisor_panel:deal_kanban")

    def form_valid(self, form):
        advisor = self.get_advisor()
        if advisor is None:
            messages.error(self.request, "حساب شما به هیچ مشاوری متصل نیست؛ امکان ثبت فرصت فروش وجود ندارد.")
            return redirect("advisor_panel:dashboard")

        phone = form.cleaned_data["customer_phone"]
        name = form.cleaned_data["customer_name"]
        customer, created = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
        if not created and name and not customer.name:
            customer.name = name
            customer.save(update_fields=["name"])

        Deal.objects.create(
            title=form.cleaned_data["title"],
            customer=customer,
            property=form.cleaned_data["property"],
            advisor=advisor,
            value=form.cleaned_data["value"],
            note=form.cleaned_data["note"],
        )
        messages.success(self.request, "فرصت فروش جدید ثبت شد.")
        return super().form_valid(form)


class DealMoveStageView(AdvisorRequiredMixin, View):
    """تغییر مرحله‌ی یک فرصت فروش در قیف"""

    VALID_STAGES = {choice[0] for choice in Deal.STAGE_CHOICES}

    def post(self, request, pk):
        advisor = self.get_advisor()
        qs = Deal.objects.all() if (request.user.is_staff and not advisor) else Deal.objects.filter(advisor=advisor)
        deal = get_object_or_404(qs, pk=pk)
        new_stage = request.POST.get("stage")
        if new_stage in self.VALID_STAGES:
            deal.stage = new_stage
            deal.save(update_fields=["stage", "updated_at"])
        return redirect("advisor_panel:deal_kanban")


class CustomerListView(AdvisorRequiredMixin, ListView):
    """
    فهرست پرونده‌های مشتریان. برخلاف بقیه‌ی بخش‌های پنل، این لیست مختص یک مشاور نیست —
    عمداً برای همه‌ی مشاوران/staff یکسان است، چون هدف پرونده‌ی یکپارچه جلوگیری از
    پیگیری موازی و ناآگاهانه‌ی یک مشتری توسط چند مشاور است.
    """

    model = Customer
    template_name = "advisor_panel/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        return qs


class CustomerProfileView(AdvisorRequiredMixin, TemplateView):
    """پرونده‌ی یکپارچه‌ی یک مشتری: همه‌ی تعاملات (درخواست تماس، ارزیابی، لاگ فعالیت، فرصت فروش)"""

    template_name = "advisor_panel/customer_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = get_object_or_404(Customer, phone=kwargs["phone"])
        context["customer"] = customer
        context["contact_requests"] = customer.contact_requests()
        context["valuation_requests"] = customer.valuation_requests()
        context["activity_logs"] = customer.activity_logs()
        context["deals"] = customer.deals.select_related("property", "advisor").order_by("-updated_at")
        context["documents"] = customer.documents.select_related("deal", "uploaded_by").order_by("-created_at")
        context["document_form"] = DocumentUploadForm(customer=customer)
        return context


class DocumentUploadView(AdvisorRequiredMixin, View):
    """آپلود سند جدید برای پرونده‌ی یک مشتری (قرارداد/وکالت‌نامه/سند مالکیت/مدرک شناسایی)"""

    def post(self, request, phone):
        customer = get_object_or_404(Customer, phone=phone)
        form = DocumentUploadForm(request.POST, request.FILES, customer=customer)
        if form.is_valid():
            document = form.save(commit=False)
            document.customer = customer
            document.uploaded_by = self.get_advisor()
            document.save()
            messages.success(request, "سند با موفقیت آپلود شد.")
        else:
            messages.error(request, "آپلود سند ناموفق بود؛ فایل یا اطلاعات وارد شده را بررسی کنید.")
        return redirect("advisor_panel:customer_profile", phone=phone)


def _heatmap_level(count):
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 4:
        return 2
    if count <= 6:
        return 3
    return 4


class AdvisorPerformanceView(ManagerRequiredMixin, TemplateView):
    """جدول امتیاز مشاوران، سرعت پاسخ‌دهی (SLA) به لیدها، و نقشه حرارتی فعالیت (مثل گیت‌هاب).
    فقط برای مدیر مجموعه — مقایسه‌ی عملکرد مشاوران داده‌ی حساس مدیریتی است، مثل نقشه‌ی امروز."""

    template_name = "advisor_panel/performance.html"
    HEATMAP_WEEKS = 26
    SCORE_WEIGHTS = {"activity": 1, "task_done": 2, "deal_won": 10}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        window_start = timezone.now() - timedelta(days=30)
        advisors = list(TeamMember.objects.filter(is_active=True).order_by("order", "name"))

        activity_counts = dict(
            ActivityLog.objects.filter(created_at__gte=window_start)
            .values("advisor_id").annotate(c=Count("id")).values_list("advisor_id", "c")
        )
        tasks_done_counts = dict(
            Task.objects.filter(status="done", completed_at__gte=window_start)
            .values("assignee_id").annotate(c=Count("id")).values_list("assignee_id", "c")
        )
        deals_won_counts = dict(
            Deal.objects.filter(stage="won", updated_at__gte=window_start)
            .values("advisor_id").annotate(c=Count("id")).values_list("advisor_id", "c")
        )

        leaderboard = []
        for advisor in advisors:
            a_count = activity_counts.get(advisor.pk, 0)
            t_count = tasks_done_counts.get(advisor.pk, 0)
            d_count = deals_won_counts.get(advisor.pk, 0)
            score = (
                a_count * self.SCORE_WEIGHTS["activity"]
                + t_count * self.SCORE_WEIGHTS["task_done"]
                + d_count * self.SCORE_WEIGHTS["deal_won"]
            )
            leaderboard.append({
                "advisor": advisor, "activities": a_count, "tasks_done": t_count,
                "deals_won": d_count, "score": score,
            })
        leaderboard.sort(key=lambda row: -row["score"])
        for i, row in enumerate(leaderboard, start=1):
            row["rank"] = i
        context["leaderboard"] = leaderboard

        sla_rows = []
        for advisor in advisors:
            activities_by_phone = {}
            logs = (
                ActivityLog.objects.filter(advisor=advisor)
                .exclude(customer_phone="")
                .order_by("created_at")
                .values_list("customer_phone", "created_at")
            )
            for phone, created_at in logs:
                activities_by_phone.setdefault(phone, []).append(created_at)

            leads = list(
                PropertyValuationRequest.objects.filter(assigned_advisor=advisor).values_list("phone", "created_at")
            ) + list(
                ContactRequest.objects.filter(property__advisor=advisor).values_list("phone", "created_at")
            )

            response_hours = []
            pending_count = 0
            for phone, created_at in leads:
                candidates = [t for t in activities_by_phone.get(phone, []) if t >= created_at]
                if candidates:
                    response_hours.append((min(candidates) - created_at).total_seconds() / 3600)
                else:
                    pending_count += 1

            sla_rows.append({
                "advisor": advisor,
                "total_leads": len(leads),
                "responded": len(response_hours),
                "pending": pending_count,
                "avg_hours": (sum(response_hours) / len(response_hours)) if response_hours else None,
            })
        context["sla_rows"] = sla_rows

        selected_advisor_id = self.request.GET.get("advisor", "").strip()
        heatmap_qs = ActivityLog.objects.all()
        if selected_advisor_id:
            heatmap_qs = heatmap_qs.filter(advisor_id=selected_advisor_id)

        today = timezone.localdate()
        sat_index = (today.weekday() - 5) % 7  # هفته از شنبه شروع می‌شود
        grid_start = today - timedelta(days=sat_index + 7 * (self.HEATMAP_WEEKS - 1))
        grid_start_dt = timezone.make_aware(datetime.combine(grid_start, time.min))

        counts = (
            heatmap_qs.filter(created_at__gte=grid_start_dt)
            .annotate(local_date=TruncDate("created_at", tzinfo=timezone.get_current_timezone()))
            .values("local_date").annotate(c=Count("id"))
        )
        counts_map = {row["local_date"]: row["c"] for row in counts}

        weeks = []
        for w in range(self.HEATMAP_WEEKS):
            week_start = grid_start + timedelta(weeks=w)
            days = []
            for d in range(7):
                date = week_start + timedelta(days=d)
                if date > today:
                    days.append(None)
                else:
                    c = counts_map.get(date, 0)
                    days.append({"date": date, "count": c, "level": _heatmap_level(c)})
            weeks.append(days)

        context["heatmap_weeks"] = weeks
        context["heatmap_day_labels"] = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        context["advisors"] = advisors
        context["selected_advisor_id"] = selected_advisor_id
        return context
