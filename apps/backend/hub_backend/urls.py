from django.contrib import admin
from django.urls import include, path
from rest_framework.schemas import get_schema_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/schema/", get_schema_view(title="Edevs Hub API", version="0.1.0"), name="openapi-schema"),
    path("api/v1/auth/", include("hub_platform.identity.auth_urls")),
    path("api/v1/company/", include("hub_platform.identity.company_urls")),
    path("api/v1/employees/", include("hub_platform.identity.employee_urls")),
    path("api/v1/health/", include("hub_platform.health.urls")),
]
