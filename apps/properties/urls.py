from django.urls import path
from . import views
from . import wishlist_views
from . import valuation_views

app_name = "properties"

urlpatterns = [
    path("", views.PropertyListView.as_view(), name="property_list"),
    path("علاقه-مندی-ها/", wishlist_views.favorites_list, name="favorites_list"),
    path("مقایسه/", wishlist_views.compare_view, name="compare_view"),
    path("مقایسه/پاک‌کردن/", wishlist_views.clear_compare, name="clear_compare"),
    path("علاقه-مندی/<int:pk>/", wishlist_views.toggle_favorite, name="toggle_favorite"),
    path("مقایسه/<int:pk>/", wishlist_views.toggle_compare, name="toggle_compare"),
    path("نوار-مقایسه/", wishlist_views.compare_bar, name="compare_bar"),
    path("شمارنده-هدر/", wishlist_views.header_counts, name="header_counts"),
    path("ارزیابی-ملک/", valuation_views.ValuationRequestPageView.as_view(), name="valuation_request"),
    path("ارزیابی-ملک/ثبت/", valuation_views.ValuationRequestCreateView.as_view(), name="valuation_request_submit"),
    path("<uslug:slug>/", views.PropertyDetailView.as_view(), name="property_detail"),
]
