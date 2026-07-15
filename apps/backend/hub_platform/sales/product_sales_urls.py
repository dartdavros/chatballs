from django.urls import path

from hub_platform.sales import public_views

# Канонический Product Sales API (SPEC-HUB-0014 §4.1):
# POST https://hub.edevs.tech/api/v1/product-sales/events
urlpatterns = [
    path(
        "events",
        public_views.ProductSalesEventView.as_view(),
        name="product-sales-events",
    ),
]
