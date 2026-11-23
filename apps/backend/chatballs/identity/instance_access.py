"""Current organization managers control Platform. TURN and storage retain global authority."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.identity.models import EmployeeRole, HumanUser, OrganizationMembership
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user


def is_instance_admin(user: object) -> bool:
    return (
        isinstance(user, HumanUser)
        and user.is_active
        and bool(getattr(user, "is_instance_admin", False))
    )


def can_view_instance_settings(user: object) -> bool:
    return can_manage_platform(user)


def can_manage_platform(user: object) -> bool:
    """Resolve platform authority from current, active memberships on every call."""
    if is_instance_admin(user):
        return True
    if not isinstance(user, HumanUser) or not user.is_active:
        return False
    for route in membership_routes_for_user(user.id):
        with tenant_atomic(route.organization_id):
            if OrganizationMembership.objects.filter(
                pk=route.resource_id, user=user, blocked_at__isnull=True,
                role__in=(EmployeeRole.OWNER, EmployeeRole.ADMIN),
            ).exists():
                return True
    return False


class InstanceSettingsPermission(BasePermission):
    """Platform reads and writes use the same current management authority."""

    message = "Instance administrator rights are required"

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return can_view_instance_settings(request.user)
        return can_manage_platform(request.user)


class CanManagePlatform(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return can_manage_platform(request.user)


class IsInstanceAdmin(BasePermission):
    message = "Instance administrator rights are required"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_instance_admin(request.user)
