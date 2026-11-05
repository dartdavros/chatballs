"""Portal settings reads shared by product entry points."""

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from chatballs.api.pagination import page_payload, paginate
from chatballs.identity.policy import has_capability_any_scope
from chatballs.integrations.models import IntegrationProvider, IntegrationStatus
from chatballs.support_portals.addressing import help_base_domain
from chatballs.support_portals.selectors import (
    portal_content_counts,
    portal_for_context,
    portals_for_context,
    portals_page_queryset,
)
from chatballs.support_portals.serializers import portal_payload
from chatballs.support_portals.statuses import PortalStatus
from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus
from chatballs.webchat.widgets import widget_payload


def require(context, capability="support.view"):
    if not has_capability_any_scope(context.membership, capability):
        raise PermissionDenied()


def listing(context, params):
    require(context)
    page = paginate(portals_page_queryset(context, params), params)
    counts = portal_content_counts(context)
    active = portals_for_context(context).exclude(status=PortalStatus.ARCHIVED).count()
    return {**page_payload(page, lambda item: portal_payload(item, counts={
        "categories": 0, "articles": 0, **counts.get(item.id, {})})),
        "creation": {"available": True, "canCreate": True, "limit": None, "used": active},
        "address": {"scheme": settings.CHATBALLS_HELP_PUBLIC_SCHEME,
            "baseDomain": help_base_domain(), "port": settings.CHATBALLS_HELP_PUBLIC_PORT or None}}


def detail(context, portal_id):
    require(context)
    portal = portal_for_context(context, portal_id)
    counts = portal_content_counts(context).get(portal.id, {})
    return {"portal": portal_payload(portal, counts=counts)}


def widgets(context, portal_id):
    require(context)
    portal_for_context(context, portal_id)
    rows = WebChatWidget.objects.select_related("integration", "integration__channel").filter(
        organization=context.organization, status=WebChatWidgetStatus.PUBLISHED,
        integration__provider=IntegrationProvider.WEB, integration__status=IntegrationStatus.OK,
        integration__is_active=True, integration__channel__is_active=True,
        integration__channel__allow_anonymous_sessions=True).order_by("name", "id")
    return {"items": [widget_payload(widget) for widget in rows]}
