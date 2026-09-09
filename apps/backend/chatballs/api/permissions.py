from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.identity.policy import has_capability_any_scope


class HasCapability(BasePermission):
    """DRF entry-point guard backed by the shared role policy (SPEC-CHATBALLS-0031 §3).

    Views declare ``required_capability`` or a method keyed
    ``required_capabilities`` mapping. Object/resource scope is still checked by the
    view after loading the canonical resource.

    Организационная область не объявляется вьюхой и не отключается: без
    членства в организации проверка не проходит вообще. Раньше рядом стоял
    атрибут ``require_organization_scope = True``, который никто не читал — он
    выглядел как переключатель там, где переключателя нет.
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


class CloudDeliveryOnly(BasePermission):
    """Guard tenant APIs that exist only in the managed Chatballs Cloud."""

    message = "This operation is available only in Chatballs Cloud"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return settings.CHATBALLS_DELIVERY_MODE == "CLOUD"
