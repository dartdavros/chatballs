from __future__ import annotations

from rest_framework.permissions import BasePermission

from hub_platform.platform.models import PlatformOperator


class HasPlatformCapability(BasePermission):
    """Checks a platform capability declared via the view attribute
    `required_platform_capability`. The capability is read from the
    authenticating PlatformToken, not from a tenant membership."""

    message = "Required platform capability is missing"

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        required = getattr(view, "required_platform_capability", None)
        if not required:
            return False
        operator = request.user
        if not isinstance(operator, PlatformOperator) or not operator.is_active:
            return False
        token = getattr(request, "auth", None)
        if token is None or token.is_revoked:
            return False
        return required in token.capabilities
