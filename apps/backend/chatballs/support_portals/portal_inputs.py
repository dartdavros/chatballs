"""Portal settings parsing shared by HTTP and native commands."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.portal_services import PortalInput
from chatballs.support_portals.themes import DEFAULT_PORTAL_THEME, PortalThemeScheme


def _optional_id(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(
            {"widgetChannelId": t("portals.widget_channel_missing")}
        ) from error


def portal_input(data: dict, current: SupportPortal | None = None) -> PortalInput:
    if "widgetId" in data:
        widget_id = (
            _optional_id(data["widgetId"])
            if data.get("widgetId") not in (None, "")
            else None
        )
        widget_channel_id = None
    else:
        widget_id = current.widget_id if current is not None else None
        widget_channel_id = (
            _optional_id(data["widgetChannelId"])
            if data.get("widgetChannelId") not in (None, "")
            else (
                current.widget_channel_id
                if current is not None and "widgetChannelId" not in data
                else None
            )
        )
    return PortalInput(
        slug=str(data.get("slug", current.slug if current else "")),
        name=str(data.get("name", current.name if current else "")),
        default_locale=str(
            data.get(
                "defaultLocale",
                current.default_locale if current else "ru",
            )
        ),
        widget_id=widget_id,
        widget_channel_id=widget_channel_id,
        theme=str(
            data.get("theme", current.theme if current else DEFAULT_PORTAL_THEME)
        ),
        theme_scheme=str(
            data.get(
                "themeScheme",
                current.theme_scheme if current else PortalThemeScheme.LIGHT,
            )
        ),
        theme_settings=data.get(
            "themeSettings",
            current.theme_settings if current else {},
        ),
    )
