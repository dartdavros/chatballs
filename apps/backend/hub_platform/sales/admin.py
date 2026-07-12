from django.contrib import admin

from hub_platform.sales.models import (
    AttributionToken,
    ExternalCustomerIdentity,
    Sale,
    SaleEvent,
    SalesSource,
)


class SaleEventInline(admin.TabularInline):
    model = SaleEvent
    extra = 0
    fields = ("event_type", "source_type", "processing_status", "occurred_at", "received_at")
    readonly_fields = fields
    # Append-only журнал: события не редактируются и не удаляются из админки.
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "product", "status", "source_type", "amount_minor", "refunded_amount_minor", "currency", "occurred_at")
    list_filter = ("status", "source_type", "environment", "attribution_method")
    search_fields = ("id", "external_sale_id", "external_customer_id", "contact__name")
    readonly_fields = ("net_amount_minor",)
    inlines = [SaleEventInline]


@admin.register(SaleEvent)
class SaleEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "source_type", "processing_status", "sale", "occurred_at", "received_at")
    list_filter = ("event_type", "source_type", "processing_status", "environment")
    search_fields = ("id", "external_event_id", "sale__id")

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False


@admin.register(SalesSource)
class SalesSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "product", "code", "type", "environment", "status", "last_event_at")
    list_filter = ("type", "environment", "status")
    search_fields = ("code", "product__code")
    readonly_fields = ("credential_hash", "credential_hint", "last_event_at", "last_error_at", "last_error")


@admin.register(AttributionToken)
class AttributionTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "product", "actor_type", "issued_at", "expires_at", "revoked_at")
    list_filter = ("actor_type",)
    search_fields = ("id",)
    readonly_fields = ("token_hash", "issued_at", "first_seen_at", "last_seen_at")


@admin.register(ExternalCustomerIdentity)
class ExternalCustomerIdentityAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "product", "environment", "external_customer_id", "contact", "verified_at")
    list_filter = ("environment", "verification_method")
    search_fields = ("external_customer_id", "contact__name")
