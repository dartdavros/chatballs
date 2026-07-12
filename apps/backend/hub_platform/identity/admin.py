from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from hub_platform.identity.models import (
    AuditEvent,
    Department,
    EmployeeProfile,
    HumanUser,
    Organization,
)


@admin.register(HumanUser)
class HumanUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "is_active", "is_staff", "last_login"]
    search_fields = ["email", "full_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "currency", "timezone", "tax_regime", "vat_mode"]
    search_fields = ["slug", "name"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "status"]
    list_filter = ["organization", "status"]
    search_fields = ["code", "name"]


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "role",
        "position_title",
        "primary_department",
        "must_change_password",
        "totp_required",
        "blocked_at",
    ]
    list_filter = ["organization", "role", "primary_department", "must_change_password", "totp_required"]
    search_fields = ["user__email", "user__full_name"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "result", "actor", "organization", "object_type", "object_id"]
    list_filter = ["result", "action", "organization"]
    search_fields = ["action", "object_type", "object_id", "actor__email", "correlation_id"]
    readonly_fields = [
        "organization",
        "actor",
        "action",
        "object_type",
        "object_id",
        "result",
        "payload",
        "correlation_id",
        "source_ip",
        "created_at",
    ]
