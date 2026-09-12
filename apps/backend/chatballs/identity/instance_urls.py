"""Настройки установки: путь без организации в адресе.

Адрес, почта, TURN и хранилище файлов общие для всех организаций, поэтому
они не живут под ``/api/v1/organizations/<uuid>/`` и не проходят tenant
middleware. Доступ — по признаку администратора установки
(см. ``identity.instance_access``).
"""

from django.urls import path

from chatballs.identity import instance_views
from chatballs.tenancy import storage_views

urlpatterns = [
    path("settings/", instance_views.InstanceAddressView.as_view(), name="instance-settings"),
    path(
        "settings/email-check/",
        instance_views.InstanceEmailCheckView.as_view(),
        name="instance-email-check",
    ),
    path("storage/", storage_views.StorageSettingsView.as_view(), name="instance-storage"),
    path("storage/check/", storage_views.StorageCheckView.as_view(), name="instance-storage-check"),
    path(
        "storage/migrate/",
        storage_views.StorageMigrateView.as_view(),
        name="instance-storage-migrate",
    ),
]
