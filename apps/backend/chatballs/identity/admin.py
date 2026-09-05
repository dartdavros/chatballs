from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from chatballs.identity.models import (
    AuditEvent,
    EmployeeGroup,
    HumanUser,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
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


@admin.register(EmployeeGroup)
class EmployeeGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "created_at"]
    list_filter = ["organization"]
    search_fields = ["name"]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "role",
        "position_title",
        "must_change_password",
        "totp_required",
        "blocked_at",
    ]
    list_filter = [
        "organization",
        "role",
        "user__must_change_password",
        "totp_required",
    ]
    search_fields = ["user__email", "user__full_name"]

    @admin.display(boolean=True, ordering="user__must_change_password")
    def must_change_password(self, membership: OrganizationMembership) -> bool:
        return membership.user.must_change_password


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "organization", "role", "expires_at", "accepted_at", "revoked_at"]
    list_filter = ["organization", "role"]
    search_fields = ["email", "organization__name"]
    readonly_fields = ["token_hash", "created_at", "accepted_at", "revoked_at"]

    def has_add_permission(self, request) -> bool:  # noqa: ANN001
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ANN001
        return False


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
