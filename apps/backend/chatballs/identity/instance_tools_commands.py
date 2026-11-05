"""Shared local-network policy commands; global administrator only."""
from django.db import transaction
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.instance_settings import InstanceSettings
from chatballs.integrations.action_catalog.authority import require_instance

_FIELDS = ["tools_private_network", "tools_private_network_enabled_by", "tools_private_network_enabled_at", "updated_at"]

def tools_network_payload(row: InstanceSettings) -> dict[str, object]:
    actor = row.tools_private_network_enabled_by
    enabled_at = row.tools_private_network_enabled_at
    return {
        "enabled": row.tools_private_network,
        "enabledBy": {"id": actor.id, "name": actor.full_name or actor.email} if actor else None,
        "enabledAt": enabled_at.isoformat() if enabled_at else None,
    }


def read(user):
    require_instance(user)
    return CommandOutcome({"toolsNetwork": tools_network_payload(InstanceSettings.load())})


@transaction.atomic
def update(user, body, *, request=None):
    user = require_instance(user)
    body = body if isinstance(body, dict) else {}
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        message = t("settings.tools_network_enabled_required")
        return CommandOutcome({"detail": message, "errors": {"enabled": message}}, status=400)
    row = InstanceSettings.load()
    row = InstanceSettings.objects.select_for_update().get(pk=row.pk)
    if enabled != row.tools_private_network:
        row.tools_private_network = enabled
        row.tools_private_network_enabled_by = user if enabled else None
        row.tools_private_network_enabled_at = timezone.now() if enabled else None
        row.save(update_fields=_FIELDS)
        record_audit_event(
            action=(
                "administration.tools_private_network_enabled"
                if enabled
                else "administration.tools_private_network_disabled"
            ),
            actor=user,
            organization=None,
            object_type="InstanceSettings",
            object_id=str(row.pk),
            request=request,
        )
    return CommandOutcome({"toolsNetwork": tools_network_payload(row)})
