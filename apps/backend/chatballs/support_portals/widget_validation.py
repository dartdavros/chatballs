from django.core.exceptions import ValidationError


def validate_portal_widget(portal) -> None:
    if portal.widget_channel_id is not None:
        if not portal.widget_channel.allow_anonymous_sessions:
            raise ValidationError(
                {"widget_channel": "Portal widget must allow anonymous web sessions"}
            )
    if portal.widget_id is None:
        return
    widget = portal.widget
    channel = widget.integration.channel
    if channel is None:
        raise ValidationError({"widget": "Portal widget must be bound to a channel"})
    if portal.widget_channel_id is not None and channel.id != portal.widget_channel_id:
        raise ValidationError({"widget": "Widget and legacy channel must match"})
