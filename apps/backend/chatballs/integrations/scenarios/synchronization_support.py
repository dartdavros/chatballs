"""Enabling exchange checks real adapter capabilities rather than promising them."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.integrations.models import Integration
from chatballs.integrations.service_connections.binding import resolve


def require_supported(tenant, pairs):
    for pair in pairs:
        if not pair["enabled"]:
            continue
        native_side = "left" if pair["left"]["connection"] == "chatballs" else "right"
        remote_side = "right" if native_side == "left" else "left"
        remote = pair[remote_side]
        if pair[native_side]["connection"] != "chatballs" or not str(remote["connection"]).isdecimal():
            raise ValidationError({"definition": t("scenarios.exchange_unavailable")})
        connection = Integration.objects.get(pk=int(remote["connection"]), organization_id=tenant.organization_id)
        _, adapter, _ = resolve(connection)
        entity = next((e for e in adapter.entities if e.key == remote["entity"]), None)
        binding = entity.synchronization if entity else None
        outbound = "forward" if native_side == "left" else "reverse"
        writes_remote = pair["direction"] in {"both", outbound} and (
            pair["sourceOfTruth"] in {native_side, "latest"} or pair["conflict"] == "manual")
        if binding is None or writes_remote and not binding.update_operation:
            raise ValidationError({"definition": t("scenarios.exchange_unavailable")})
