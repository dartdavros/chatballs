"""«Настройки → Голосовые и звонки»: матрица точек входа × функции.

GET   company/administration/communication/  — точки входа с флагами
PATCH company/administration/communication/  — {items: [{id, voiceMessages, audioCalls, videoCalls}]}
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.audit import record_audit_event
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


class CommunicationSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "settings.view", "PATCH": "company.manage"}

    def get(self, request: Request) -> Response:
        organization = request.tenant_context.organization
        return Response({"items": [_item(i) for i in _entry_points(organization)]})

    def patch(self, request: Request) -> Response:
        organization = request.tenant_context.organization
        items = request.data.get("items")
        if not isinstance(items, list):
            return Response({"detail": "Ожидается список items"}, status=400)
        by_id = {i.id: i for i in _entry_points(organization)}
        changed: list[dict[str, object]] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            integration = by_id.get(raw.get("id"))
            if integration is None:
                return Response({"detail": "Точка входа не найдена"}, status=404)
            fields: list[str] = []
            for key, attr in (("voiceMessages", "voice_messages_enabled"), ("audioCalls", "audio_calls_enabled"), ("videoCalls", "video_calls_enabled")):
                if key in raw:
                    setattr(integration, attr, bool(raw[key]))
                    fields.append(attr)
            if fields:
                integration.save(update_fields=[*fields, "updated_at"])
                changed.append({"id": integration.id, **{k: raw[k] for k in ("voiceMessages", "audioCalls", "videoCalls") if k in raw}})
        if changed:
            record_audit_event(
                action="administration.communication_updated",
                actor=request.user,
                organization=organization,
                object_type="Integration",
                object_id=",".join(str(c["id"]) for c in changed),
                payload={"items": changed},
                request=request,
            )
        return Response({"items": [_item(i) for i in _entry_points(organization)]})
