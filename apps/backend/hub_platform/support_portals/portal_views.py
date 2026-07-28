from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability, HasEntitlement
from hub_platform.channels.models import Channel
from hub_platform.channels.serializers import channel_payload
from hub_platform.identity.audit import record_audit_event
from hub_platform.support_portals.api import validation_response
from hub_platform.support_portals.models import SupportPortal
from hub_platform.support_portals.domain_services import (
    set_custom_domain,
    verify_custom_domain,
)
from hub_platform.support_portals.portal_services import (
    PortalInput,
    create_portal,
    replace_product_links,
    set_portal_status,
    update_portal,
)
from hub_platform.support_portals.selectors import portal_for_context, portals_for_context
from hub_platform.support_portals.serializers import portal_payload
from hub_platform.subscriptions.errors import PolicyUnavailable
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.policy import get_effective_policy


class PortalBaseView(APIView):
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "support_department"
    required_capability = "support.view"
    required_capabilities = {
        "GET": "support.view",
        "POST": "support.operate",
        "PATCH": "support.operate",
        "PUT": "support.operate",
        "DELETE": "support.operate",
    }
    required_department_code = "support"

    def portal(self, request: Request, portal_id: int) -> SupportPortal | None:
        try:
            return portal_for_context(request.tenant_context, portal_id)
        except SupportPortal.DoesNotExist:
            return None


def _input(request: Request, current: SupportPortal | None = None) -> PortalInput:
    return PortalInput(
        slug=str(request.data.get("slug", current.slug if current else "")),
        name=str(request.data.get("name", current.name if current else "")),
        default_locale=str(
            request.data.get(
                "defaultLocale",
                current.default_locale if current else "ru",
            )
        ),
    )


class PortalListView(PortalBaseView):
    def get(self, request: Request) -> Response:
        portals = list(portals_for_context(request.tenant_context))
        try:
            quota = get_effective_policy(request.tenant_context).quota(
                QuotaKey.SUPPORT_PORTALS
            )
        except PolicyUnavailable:
            quota = None
        active_count = sum(item.status != "ARCHIVED" for item in portals)
        available = quota is not None
        can_create = available and (
            quota.limit is None or active_count < quota.limit
        )
        return Response(
            {
                "items": [portal_payload(item) for item in portals],
                "creation": {
                    "available": available,
                    "canCreate": can_create,
                    "limit": quota.limit if quota else None,
                    "used": active_count,
                },
                "address": {
                    "scheme": settings.CUS_HELP_PUBLIC_SCHEME,
                    "baseDomain": settings.CUS_HELP_BASE_DOMAIN,
                    "port": settings.CUS_HELP_PUBLIC_PORT or None,
                },
            }
        )

    def post(self, request: Request) -> Response:
        try:
            portal = create_portal(context=request.tenant_context, data=_input(request))
        except ValidationError as error:
            return validation_response(error)
        record_audit_event(
            action="support_portal.created",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="SupportPortal",
            object_id=str(portal.public_id),
            request=request,
        )
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)}, status=201)


class PortalDetailView(PortalBaseView):
    def get(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        return Response({"portal": portal_payload(portal)})

    def patch(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            update_portal(
                context=request.tenant_context,
                portal=portal,
                data=_input(request, portal),
            )
        except ValidationError as error:
            return validation_response(error)
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)})


class PortalStatusView(PortalBaseView):
    def post(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            portal = set_portal_status(
                context=request.tenant_context,
                portal=portal,
                status=str(request.data.get("status", "")),
            )
        except ValidationError as error:
            return validation_response(error)
        record_audit_event(
            action=f"support_portal.{portal.status.lower()}",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="SupportPortal",
            object_id=str(portal.public_id),
            request=request,
        )
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)})


class PortalProductsView(PortalBaseView):
    def put(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        links = request.data.get("items")
        if not isinstance(links, list):
            return Response({"detail": "items должен быть списком"}, status=400)
        try:
            replace_product_links(
                context=request.tenant_context,
                portal=portal,
                links=links,
            )
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректная привязка продукта"}, status=400)
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)})


class PortalSupportChannelsView(PortalBaseView):
    """Portal-scoped channel options available to support operators."""

    def get(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        channels = (
            Channel.objects.select_related("department", "product")
            .filter(
                organization=request.tenant_context.organization,
                department__code="support",
                product__isnull=False,
                is_active=True,
                requires_authenticated_product_identity=True,
                allow_anonymous_sessions=False,
            )
            .order_by("product__name", "name", "id")
        )
        return Response({"items": [channel_payload(channel) for channel in channels]})


class PortalDomainView(PortalBaseView):
    def put(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            portal = set_custom_domain(
                portal, str(request.data.get("customDomain", ""))
            )
        except ValidationError as error:
            return validation_response(error)
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)})


class PortalDomainVerifyView(PortalBaseView):
    def post(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            portal = verify_custom_domain(portal)
        except ValidationError as error:
            return validation_response(error)
        portal = portal_for_context(request.tenant_context, portal.id)
        return Response({"portal": portal_payload(portal)})
