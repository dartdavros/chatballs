from django.urls import path

from hub_platform.orders import views

urlpatterns = [
    path("", views.OrderListCreateView.as_view(), name="order-list"),
    path("<int:order_id>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("<int:order_id>/mark-paid/", views.OrderMarkPaidView.as_view(), name="order-mark-paid"),
    path("<int:order_id>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
    path("<int:order_id>/fulfillment/", views.OrderFulfillmentView.as_view(), name="order-fulfillment"),
]
