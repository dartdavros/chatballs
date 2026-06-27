from django.contrib import admin

from hub_platform.integrations.models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "kind", "status", "last_checked_at")
    list_filter = ("provider", "kind", "status")
    search_fields = ("name",)
    readonly_fields = ("last_checked_at", "last_error", "created_at", "updated_at")
