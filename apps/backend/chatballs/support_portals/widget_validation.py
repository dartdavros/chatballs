from django.core.exceptions import ValidationError

from chatballs.i18n import t


def validate_portal_widget(portal) -> None:
    if portal.widget_channel_id is not None:
        if not portal.widget_channel.allow_anonymous_sessions:
            raise ValidationError(
                {"widget_channel": t("portals.widget_needs_anonymous")}
            )
    if portal.widget_id is None:
        return
    widget = portal.widget
    channel = widget.integration.channel
    if channel is None:
        raise ValidationError({"widget": t("portals.widget_needs_channel")})
    if portal.widget_channel_id is not None and channel.id != portal.widget_channel_id:
        raise ValidationError({"widget": t("portals.widget_channel_mismatch")})
