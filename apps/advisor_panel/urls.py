from django.urls import path
from . import views

app_name = "advisor_panel"

urlpatterns = [
    path("", views.AdvisorDashboardView.as_view(), name="dashboard"),
    path("املاک/", views.AdvisorPropertyListView.as_view(), name="property_list"),
    path("املاک/جدید/", views.AdvisorPropertyCreateView.as_view(), name="property_create"),
    path("املاک/<int:pk>/ویرایش/", views.AdvisorPropertyUpdateView.as_view(), name="property_edit"),
    path("املاک/<int:pk>/حذف/", views.AdvisorPropertyDeleteView.as_view(), name="property_delete"),
    path("درخواست-ها/", views.AdvisorContactRequestsView.as_view(), name="contact_requests"),
    path("درخواست-ها/<int:pk>/خوانده-شد/", views.MarkContactRequestReadView.as_view(), name="mark_request_read"),
    path("ارزیابی-ملک/", views.ValuationRequestQueueView.as_view(), name="valuation_queue"),
    path("ارزیابی-ملک/<int:pk>/گرفتن/", views.ClaimValuationRequestView.as_view(), name="claim_valuation_request"),
    path("ارزیابی-ملک/<int:pk>/وضعیت/", views.UpdateValuationRequestStatusView.as_view(), name="update_valuation_status"),
    path("مدیریت-مشاوران/", views.ManagerAdvisorListView.as_view(), name="manager_advisor_list"),
    path("مدیریت-مشاوران/جدید/", views.ManagerAdvisorCreateView.as_view(), name="manager_advisor_create"),
    path("مدیریت-مشاوران/<int:pk>/ویرایش/", views.ManagerAdvisorUpdateView.as_view(), name="manager_advisor_edit"),
    path("مدیریت-مشاوران/<int:pk>/تغییر-وضعیت/", views.ManagerAdvisorToggleActiveView.as_view(), name="manager_advisor_toggle"),
    path("فعالیت-ها/", views.ActivityLogListView.as_view(), name="activity_log_list"),
    path("فعالیت-ها/جدید/", views.ActivityLogCreateView.as_view(), name="activity_log_create"),
    path("فعالیت-ها/<int:pk>/تغییر-وضعیت/", views.ActivityLogToggleDoneView.as_view(), name="activity_log_toggle_done"),
    path("وظایف/", views.TaskListView.as_view(), name="task_list"),
    path("وظایف/جدید/", views.TaskAssignView.as_view(), name="task_assign"),
    path("وظایف/<int:pk>/وضعیت/", views.TaskUpdateStatusView.as_view(), name="task_update_status"),
    path("تقویم/", views.CalendarView.as_view(), name="calendar"),
    path("نقشه-امروز/", views.TodayMapView.as_view(), name="today_map"),
    path("قیف-فروش/", views.DealKanbanView.as_view(), name="deal_kanban"),
    path("قیف-فروش/جدید/", views.DealCreateView.as_view(), name="deal_create"),
    path("قیف-فروش/<int:pk>/مرحله/", views.DealMoveStageView.as_view(), name="deal_move_stage"),
    path("مشتریان/", views.CustomerListView.as_view(), name="customer_list"),
    path("مشتریان/<str:phone>/", views.CustomerProfileView.as_view(), name="customer_profile"),
    path("مشتریان/<str:phone>/اسناد/جدید/", views.DocumentUploadView.as_view(), name="document_upload"),
    path("عملکرد-مشاوران/", views.AdvisorPerformanceView.as_view(), name="performance"),
]
