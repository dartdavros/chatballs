from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from hub_platform.identity.policy import ResourceScope, authorize, has_capability_any_scope


class HasCapability(BasePermission):
    """DRF entry-point guard backed by the shared capability policy.

    Views declare ``required_capability`` or a method keyed
    ``required_capabilities`` mapping. Object/resource scope is still checked by the
    view after loading the canonical resource.
    """

    message = "Required capability is missing"

    def has_permission(self, request: Request, view: APIView) -> bool:
        capability = getattr(view, "required_capability", None)
        by_method = getattr(view, "required_capabilities", {})
        capability = by_method.get(request.method, capability)
        if not capability:
            return False
        profile = getattr(request.user, "employee_profile", None)
        if profile is None:
            return False
        if getattr(view, "require_organization_scope", False):
            return authorize(
                request.user,
                capability,
                ResourceScope(organization_id=profile.organization_id),
            )
        return has_capability_any_scope(request.user, capability)
