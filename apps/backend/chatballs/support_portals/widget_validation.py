from django.core.exceptions import ValidationError


def validate_portal_widget(portal) -> None:
    if portal.widget_channel_id is not None:
        legacy_channel = portal.widget_channel
        if (
            legacy_channel.requires_authenticated_product_identity
            or not legacy_channel.allow_anonymous_sessions
        ):
            raise ValidationError(
                {"widget_channel": "Portal widget must allow anonymous web sessions"}
            )
    if portal.widget_id is None:
        return
    widget = portal.widget
    channel = widget.integration.channel
    if widget.mode != "ANONYMOUS":
        raise ValidationError({"widget": "Portal requires an anonymous widget"})
    if channel is None:
        raise ValidationError({"widget": "Portal widget must be bound to a channel"})
    if portal.widget_channel_id is not None and channel.id != portal.widget_channel_id:
        raise ValidationError({"widget": "Widget and legacy channel must match"})


def validate_product_support_widget(link) -> None:
    if link.support_widget_id is None:
        return
    widget = link.support_widget
    channel = widget.integration.channel
    if widget.mode != "AUTHENTICATED_PRODUCT":
        raise ValidationError(
            {"support_widget": "Product route requires an authenticated widget"}
        )
    if channel is None or channel.product_id != link.product_id:
        raise ValidationError(
            {"support_widget": "Support widget must belong to the linked product"}
        )
    if (
        link.support_channel_id is not None
        and channel.id != link.support_channel_id
    ):
        raise ValidationError(
            {"support_widget": "Widget and legacy channel must match"}
        )
