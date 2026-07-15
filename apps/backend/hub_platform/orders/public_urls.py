from django.urls import path

from hub_platform.orders import views

urlpatterns = [
    path("ingest/", views.OrderIngestView.as_view(), name="order-ingest"),
]
