from django.contrib import admin
from django.urls import include, path
from rest_framework.schemas import get_schema_view

from hub_platform.webchat.views import WidgetLoaderView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("chat-widget.js", WidgetLoaderView.as_view(), name="chat-widget-loader"),
    path("api/v1/schema/", get_schema_view(title="CustoCRM API", version="0.1.0"), name="openapi-schema"),
    path("api/v1/auth/", include("hub_platform.identity.auth_urls")),
    path("api/v1/company/", include("hub_platform.identity.company_urls")),
    path("api/v1/company/", include("hub_platform.products.urls")),
    path("api/v1/employees/", include("hub_platform.identity.employee_urls")),
    path("api/v1/ai/", include("hub_platform.ai.urls")),
    path("api/v1/integrations/", include("hub_platform.integrations.urls")),
    path("api/v1/channels/", include("hub_platform.channels.urls")),
    path("api/v1/conversations/", include("hub_platform.conversations.urls")),
    path("api/v1/orders/", include("hub_platform.orders.urls")),
    path("api/v1/sales/", include("hub_platform.sales.urls")),
    path("api/v1/product-sales/", include("hub_platform.sales.product_sales_urls")),
    path("api/v1/notifications/", include("hub_platform.notifications.urls")),
    path("api/v1/webchat/", include("hub_platform.webchat.urls")),
    path("api/v1/health/", include("hub_platform.health.urls")),
    path("api/v1/support/", include("hub_platform.support.urls")),
    path("api/v1/calls/", include("hub_platform.calls.urls")),
]
