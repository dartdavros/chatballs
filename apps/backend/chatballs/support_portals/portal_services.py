from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.i18n import t
from chatballs.integrations.models import IntegrationProvider, IntegrationStatus
from chatballs.support_portals.addressing import hosted_domain
from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.statuses import PortalStatus
from chatballs.support_portals.themes import (
    DEFAULT_PORTAL_THEME,
    PortalThemeScheme,
    normalize_theme,
    normalize_theme_scheme,
    validate_theme_scheme,
    validate_theme_settings,
)
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus


@dataclass(frozen=True)
class PortalInput:
    slug: str
    name: str
    default_locale: str = "ru"
    widget_id: int | None = None
    widget_channel_id: int | None = None
    theme: str = DEFAULT_PORTAL_THEME
    theme_scheme: str = PortalThemeScheme.LIGHT
    theme_settings: dict | None = None


def _theme_scheme(value: str | None) -> str:
    scheme = normalize_theme_scheme(value)
    validate_theme_scheme(scheme)
    return scheme


@transaction.atomic
def create_portal(*, context: TenantContext, data: PortalInput) -> SupportPortal:
    widget = _widget(context, data.widget_id, data.widget_channel_id)
    portal = SupportPortal(
        organization=context.organization,
        slug=data.slug.strip().lower(),
        hosted_domain=hosted_domain(data.slug.strip().lower()),
        name=data.name.strip(),
        default_locale=data.default_locale.strip().lower() or "ru",
        theme=normalize_theme(data.theme),
        theme_scheme=_theme_scheme(data.theme_scheme),
        theme_settings=validate_theme_settings(data.theme_settings),
        widget=widget,
        widget_channel=widget.integration.channel if widget else None,
    )
    portal.full_clean()
    portal.save()
    return portal


def update_portal(
    *, context: TenantContext, portal: SupportPortal, data: PortalInput
) -> SupportPortal:
    _check_tenant(context, portal)
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError({"portal": t("portals.restore_to_edit_settings")})
    portal.slug = data.slug.strip().lower()
    portal.hosted_domain = hosted_domain(portal.slug)
    portal.name = data.name.strip()
    portal.default_locale = data.default_locale.strip().lower() or "ru"
    portal.theme = normalize_theme(data.theme)
    portal.theme_scheme = _theme_scheme(data.theme_scheme)
    portal.theme_settings = validate_theme_settings(data.theme_settings)
    widget = _widget(context, data.widget_id, data.widget_channel_id)
    portal.widget = widget
    portal.widget_channel = widget.integration.channel if widget else None
    portal.full_clean()
    portal.save()
    return portal


def _widget(
    context: TenantContext,
    widget_id: int | None,
    legacy_channel_id: int | None,
) -> WebChatWidget | None:
    if widget_id is None and legacy_channel_id is None:
        return None
    widgets = WebChatWidget.objects.select_related(
        "integration",
        "integration__channel",
    ).filter(
        organization=context.organization,
        status=WebChatWidgetStatus.PUBLISHED,
        integration__provider=IntegrationProvider.WEB,
        integration__status=IntegrationStatus.OK,
        integration__is_active=True,
        integration__channel__is_active=True,
        integration__channel__allow_anonymous_sessions=True,
    )
    if widget_id is not None:
        widget = widgets.filter(id=widget_id).first()
    else:
        matches = list(
            widgets.filter(integration__channel_id=legacy_channel_id)
            .order_by("id")[:2]
        )
        widget = matches[0] if len(matches) == 1 else None
    if widget is None:
        raise ValidationError(
            {"widgetId": t("portals.anonymous_widget_missing")}
        )
    return widget


@transaction.atomic
def set_portal_status(
    *, context: TenantContext, portal: SupportPortal, status: str
) -> SupportPortal:
    _check_tenant(context, portal)
    if status not in PortalStatus.values:
        raise ValidationError({"status": t("portals.unknown_status")})
    if status == portal.status:
        return portal
    portal.transition_version += 1
    if status == PortalStatus.ARCHIVED:
        portal.published_at = None
    elif portal.status == PortalStatus.ARCHIVED:
        status = PortalStatus.DRAFT
    elif status == PortalStatus.PUBLISHED:
        portal.published_at = timezone.now()
    else:
        portal.published_at = None
    portal.status = status
    portal.save(update_fields=["status", "transition_version", "published_at", "updated_at"])
    return portal


def _check_tenant(context: TenantContext, portal: SupportPortal) -> None:
    if portal.organization_id != context.organization_id:
        raise ValidationError({"portal": t("portals.other_organization")})
