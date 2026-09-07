from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.models import IntegrationProvider, IntegrationStatus
from chatballs.support_portals.api import validation_response
from chatballs.support_portals.domain_services import (
    set_custom_domain,
    verify_custom_domain,
)
from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.portal_services import (
    PortalInput,
    create_portal,
    replace_product_links,
    set_portal_status,
    update_portal,
)
from chatballs.support_portals.selectors import (
    portal_content_counts,
    portal_for_context,
    portals_for_context,
)
from chatballs.support_portals.serializers import portal_payload
from chatballs.support_portals.themes import (
    DEFAULT_PORTAL_THEME,
    PortalThemeScheme,
)
from chatballs.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)
from chatballs.webchat.widgets import widget_payload


def _optional_id(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(
            {"widgetChannelId": "Канал веб-виджета не найден"}
        ) from error


class PortalBaseView(APIView):
    permission_classes = [HasCapability]
    required_capability = "support.view"
    required_capabilities = {
        "GET": "support.view",
        "POST": "support.operate",
        "PATCH": "support.operate",
        "PUT": "support.operate",
        "DELETE": "support.operate",
    }

    def portal(self, request: Request, portal_id: int) -> SupportPortal | None:
        try:
            return portal_for_context(request.tenant_context, portal_id)
        except SupportPortal.DoesNotExist:
            return None


def _input(request: Request, current: SupportPortal | None = None) -> PortalInput:
    if "widgetId" in request.data:
        widget_id = (
            _optional_id(request.data["widgetId"])
            if request.data.get("widgetId") not in (None, "")
            else None
        )
        widget_channel_id = None
    else:
        widget_id = current.widget_id if current is not None else None
        widget_channel_id = (
            _optional_id(request.data["widgetChannelId"])
            if request.data.get("widgetChannelId") not in (None, "")
            else (
                current.widget_channel_id
                if current is not None and "widgetChannelId" not in request.data
                else None
            )
        )
    return PortalInput(
        slug=str(request.data.get("slug", current.slug if current else "")),
        name=str(request.data.get("name", current.name if current else "")),
        default_locale=str(
            request.data.get(
                "defaultLocale",
                current.default_locale if current else "ru",
            )
        ),
        widget_id=widget_id,
        widget_channel_id=widget_channel_id,
        theme=str(
            request.data.get("theme", current.theme if current else DEFAULT_PORTAL_THEME)
        ),
        theme_scheme=str(
            request.data.get(
                "themeScheme",
                current.theme_scheme if current else PortalThemeScheme.LIGHT,
            )
        ),
        theme_settings=request.data.get(
            "themeSettings",
            current.theme_settings if current else {},
        ),
    )


class PortalListView(PortalBaseView):
    def get(self, request: Request) -> Response:
        portals = list(portals_for_context(request.tenant_context))
        counts = portal_content_counts(request.tenant_context)
        # Тарифные лимиты порталов удалены (ADR-HUB-0042 §2): создание доступно всегда.
        active_count = sum(item.status != "ARCHIVED" for item in portals)
        return Response(
            {
                "items": [
                    portal_payload(
                        item,
                        counts={
                            "categories": 0,
                            "articles": 0,
                            **counts.get(item.id, {}),
                        },
                    )
                    for item in portals
                ],
                "creation": {
                    "available": True,
                    "canCreate": True,
                    "limit": None,
                    "used": active_count,
                },
                "address": {
                    "scheme": settings.CHATBALLS_HELP_PUBLIC_SCHEME,
                    "baseDomain": settings.CHATBALLS_HELP_BASE_DOMAIN,
                    "port": settings.CHATBALLS_HELP_PUBLIC_PORT or None,
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
        counts = portal_content_counts(request.tenant_context).get(portal.id, {})
        return Response({"portal": portal_payload(portal, counts=counts)})

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
    """Portal-scoped widget options available to support operators."""

    def get(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        widgets = (
            WebChatWidget.objects.select_related(
                "integration",
                "integration__channel",
                "integration__channel__product",
            )
            .filter(
                organization=request.tenant_context.organization,
                mode=WebChatWidgetMode.AUTHENTICATED_PRODUCT,
                status=WebChatWidgetStatus.PUBLISHED,
                integration__provider=IntegrationProvider.WEB,
                integration__status=IntegrationStatus.OK,
                integration__is_active=True,
                integration__channel__product__isnull=False,
                integration__channel__is_active=True,
            )
            .order_by("integration__channel__product__name", "name", "id")
        )
        anonymous_widgets = (
            WebChatWidget.objects.select_related(
                "integration",
                "integration__channel",
                "integration__channel__product",
            )
            .filter(
                organization=request.tenant_context.organization,
                mode=WebChatWidgetMode.ANONYMOUS,
                status=WebChatWidgetStatus.PUBLISHED,
                integration__provider=IntegrationProvider.WEB,
                integration__status=IntegrationStatus.OK,
                integration__is_active=True,
                integration__channel__is_active=True,
                integration__channel__requires_authenticated_product_identity=False,
                integration__channel__allow_anonymous_sessions=True,
            )
            .order_by("name", "id")
        )
        return Response(
            {
                "items": [widget_payload(widget) for widget in widgets],
                "widgetItems": [widget_payload(widget) for widget in anonymous_widgets],
            }
        )


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
