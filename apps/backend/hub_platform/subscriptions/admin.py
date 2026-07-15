from django.contrib import admin

from hub_platform.subscriptions.models import (
    EntitlementDefinition,
    EntitlementGrant,
    Plan,
    PlanVersion,
    QuotaDefinition,
    QuotaGrant,
    Subscription,
    SubscriptionOverride,
    UsageCounter,
    UsageLedgerEntry,
    UsagePeriod,
)


class EntitlementGrantInline(admin.TabularInline):
    model = EntitlementGrant
    extra = 0


class QuotaGrantInline(admin.TabularInline):
    model = QuotaGrant
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "saleable")
    list_filter = ("saleable",)


@admin.register(PlanVersion)
class PlanVersionAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "version",
        "agent_unit_price_minor",
        "currency",
        "published_at",
    )
    list_filter = ("plan", "currency", "published_at")
    readonly_fields = ("public_id", "created_at")
    inlines = (EntitlementGrantInline, QuotaGrantInline)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan_version",
        "ai_agent_quantity",
        "status",
        "current_period_end",
    )
    list_filter = ("status", "plan_version__plan")
    search_fields = ("organization__name", "organization__slug")


@admin.register(SubscriptionOverride)
class SubscriptionOverrideAdmin(admin.ModelAdmin):
    list_display = ("organization", "target", "operation", "starts_at", "ends_at")
    list_filter = ("target", "operation")
    readonly_fields = ("created_at", "correlation_id")


@admin.register(UsagePeriod)
class UsagePeriodAdmin(admin.ModelAdmin):
    list_display = ("organization", "starts_at", "ends_at", "status")
    list_filter = ("status",)


@admin.register(UsageCounter)
class UsageCounterAdmin(admin.ModelAdmin):
    list_display = ("organization", "quota_definition", "used_value", "reserved_value")
    readonly_fields = ("organization", "period", "quota_definition", "used_value", "reserved_value")


@admin.register(UsageLedgerEntry)
class UsageLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("organization", "quota_definition", "quantity", "kind", "occurred_at")
    list_filter = ("kind", "quota_definition")
    readonly_fields = tuple(field.name for field in UsageLedgerEntry._meta.fields)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


admin.site.register(EntitlementDefinition)
admin.site.register(QuotaDefinition)
