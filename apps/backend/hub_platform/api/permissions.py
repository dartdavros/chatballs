from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from hub_platform.identity.policy import has_capability_any_scope
from hub_platform.subscriptions.policy import get_effective_policy


class HasCapability(BasePermission):
    """DRF entry-point guard backed by the shared role policy (SPEC-HUB-0031 §3).

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
        context = getattr(request, "tenant_context", None)
        if context is None or context.membership is None:
            return False
        return has_capability_any_scope(context.membership, capability)


class HasEntitlement(BasePermission):
    """DRF entry-point guard backed by the organization subscription policy.

    Unlike :class:`HasCapability` (per-membership role authorization), an
    entitlement is an organization-level feature flag derived from the active
    subscription (SPEC-HUB-0022). Views declare ``required_entitlement`` or a
    method-keyed ``required_entitlements`` mapping. The check never raises: a
    missing entitlement yields a clean 403 via DRF.
    """

    message = "Entitlement not available for this organization"

    def has_permission(self, request: Request, view: APIView) -> bool:
        entitlement = getattr(view, "required_entitlement", None)
        by_method = getattr(view, "required_entitlements", {})
        entitlement = by_method.get(request.method, entitlement)
        if not entitlement:
            # No entitlement declared -> this permission is a no-op for the view.
            return True
        context = getattr(request, "tenant_context", None)
        if context is None:
            return False
        try:
            policy = get_effective_policy(context)
        except Exception:
            # No subscription / inactive subscription -> entitlements unavailable.
            return False
        return policy.has_entitlement(entitlement)


class CloudDeliveryOnly(BasePermission):
    """Guard tenant APIs that exist only in the managed Chatbolls Cloud."""

    message = "This operation is available only in Chatbolls Cloud"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return settings.CUS_DELIVERY_MODE == "CLOUD"
