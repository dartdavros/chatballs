"""Публичные API-базы и разрешение tenant-контекста виджета/сессии."""

from contextlib import contextmanager

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.integrations.models import IntegrationStatus
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import web_channel_route, web_widget_route
from chatballs.tenancy.lookup import load_organization
from chatballs.webchat import services
from chatballs.webchat.api_inputs import host_origin, session_token
from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus
from chatballs.webchat.session_access import resolved_web_session
from chatballs.webchat.throttling import WebchatSessionTrafficThrottle, WebchatTrafficThrottle


class _Public(APIView):
    authentication_classes: list = []  # публичные endpoint'ы: токен сессии, без CSRF/сессии Django
    permission_classes = [AllowAny]


class _PublicSession(_Public):
    """Публичный endpoint, работающий по токену анонимной сессии.

    Два контура лимитов: по адресу клиента и по самой сессии — см.
    ``webchat/throttling.py``.
    """

    throttle_classes = [WebchatTrafficThrottle, WebchatSessionTrafficThrottle]


def session_available(session, request) -> bool:
    connection = session.connection
    return bool(
        session.widget.status == WebChatWidgetStatus.PUBLISHED
        and connection.is_active and connection.status == IntegrationStatus.OK
        and connection.channel_id and connection.channel.is_active
        and connection.channel.allow_anonymous_sessions
        and services.origin_allowed(session.widget, host_origin(request))
    )


@contextmanager
def _resolved_web_widget(widget_key: str, channel_code: str = ""):
    route = web_widget_route(widget_key) if widget_key else web_channel_route(channel_code)
    if route is None:
        yield None, None
        return
    organization = load_organization(route.organization_id)
    if organization is None:
        yield None, None
        return
    context = TenantContext.for_resource(organization)
    with tenant_atomic(context):
        filters = (
            {"id": route.resource_id, "public_key": widget_key}
            if widget_key
            else {"integration_id": route.resource_id}
        )
        widget = WebChatWidget.objects.select_related(
            "integration",
            "integration__channel",
        ).filter(
            **filters,
            organization=organization,
            status=WebChatWidgetStatus.PUBLISHED,
            integration__organization=organization,
            integration__provider="WEB",
            integration__status=IntegrationStatus.OK,
            integration__is_active=True,
            integration__channel__organization=organization,
            integration__channel__is_active=True,
        ).first()
        if widget is not None and channel_code and widget.integration.channel.code != channel_code:
            widget = None
        yield context, widget


@contextmanager
def _resolved_web_session(request: Request):
    with resolved_web_session(session_token(request)) as resolved:
        yield resolved
