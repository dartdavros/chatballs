from django.urls import path

from hub_platform.sales import views

# Внутренний API реестра продаж (сессия сотрудника). Product Sales API вынесен
# отдельно в product_sales_urls.py и монтируется на корневой /api/v1/product-sales/.
urlpatterns = [
    path("", views.SaleListCreateView.as_view(), name="sale-list"),
    path("analytics/", views.SalesAnalyticsView.as_view(), name="sale-analytics"),
    path("attribution-tokens/", views.AttributionTokenView.as_view(), name="sale-attribution-token"),
    path("<int:sale_id>/", views.SaleDetailView.as_view(), name="sale-detail"),
    path("<int:sale_id>/<str:action>/", views.SaleActionView.as_view(), name="sale-action"),
]
