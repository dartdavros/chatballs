"""Communication feature matrix shared by HTTP and native settings actions."""

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import has_capability_any_scope
from chatballs.integrations.features import supports_calls
from chatballs.integrations.models import Integration, IntegrationKind


def _item(integration: Integration) -> dict[str, object]:
    return {
        "id": integration.id,
        "name": integration.name,
        "provider": integration.provider,
        "isActive": integration.is_active,
        "agentName": integration.channel.name if integration.channel_id else "",
        "supportsCalls": supports_calls(integration),
        "voiceMessages": integration.voice_messages_enabled,
        "audioCalls": integration.audio_calls_enabled and supports_calls(integration),
        "videoCalls": integration.video_calls_enabled and supports_calls(integration),
    }


def _entry_points(organization):
    return (
        Integration.objects.filter(organization=organization, kind=IntegrationKind.MESSENGER)
        .select_related("channel")
        .order_by("channel__name", "provider", "name", "id")
    )


def read_communication(context):
    if not has_capability_any_scope(context.membership, "settings.view"):
        raise PermissionDenied()
    organization = context.organization
    return {"items": [_item(i) for i in _entry_points(organization)]}


@transaction.atomic
def update_communication(context, body, *, request=None):
    if not has_capability_any_scope(context.membership, "company.manage"):
        raise PermissionDenied()
    organization = context.organization
    items = body.get("items")
    if not isinstance(items, list):
        raise ValidationError({"detail": t("settings.items_list_expected")})
    by_id = {i.id: i for i in _entry_points(organization)}
    changed: list[dict[str, object]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        integration = by_id.get(raw.get("id"))
        if integration is None:
            raise NotFound({"detail": t("settings.entry_point_not_found")})
        fields: list[str] = []
        for key, attr in (
            ("voiceMessages", "voice_messages_enabled"),
            ("audioCalls", "audio_calls_enabled"),
            ("videoCalls", "video_calls_enabled"),
        ):
            if key in raw:
                setattr(integration, attr, bool(raw[key]))
                fields.append(attr)
        if fields:
            if integration.provider == "WEB" and "voiceMessages" in raw:
                from chatballs.webchat.recording_configuration import recording_settings

                if recording_settings(integration)["microphoneMode"] != "dictation":
                    integration.config = {**integration.config,
                        "microphoneMode": "voice_message" if integration.voice_messages_enabled else "off"}
                    fields.append("config")
            integration.save(update_fields=[*fields, "updated_at"])
            changed.append(
                {
                    "id": integration.id,
                    **{
                        k: raw[k] for k in ("voiceMessages", "audioCalls", "videoCalls") if k in raw
                    },
                }
            )
    if changed:
        record_audit_event(
            action="administration.communication_updated",
            actor=context.actor_user,
            organization=organization,
            object_type="Integration",
            object_id=",".join(str(c["id"]) for c in changed),
            payload={"items": changed},
            request=request,
        )
    return {"items": [_item(i) for i in _entry_points(organization)]}
