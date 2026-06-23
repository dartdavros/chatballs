from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditResult
from hub_platform.identity.permissions import is_owner


class IsOwner(BasePermission):
    """Allow only authenticated OWNER users; audit denials, as the legacy decorator did."""

    message = "Owner role required"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_owner(user):
            return True
        organization = getattr(getattr(user, "employee_profile", None), "organization", None)
        record_audit_event(
            action="identity.owner_permission_denied",
            actor=user,
            organization=organization,
            result=AuditResult.DENIED,
            request=request,
        )
        return False
