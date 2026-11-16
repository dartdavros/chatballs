"""Shared tenant/owner boundary and secret-free administrative projection."""

from django.core.exceptions import PermissionDenied
from django.http import Http404

from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.ai.external_agents.config_policy import POLICY_FIELDS
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.operation_modes import lock_organization


def owner(context):
    membership = context.membership
    if membership is None or context.actor_user is None or not OrganizationMembership.objects.filter(
        pk=membership.pk, organization_id=context.organization_id, user=context.actor_user,
        role__in=["OWNER", "ADMIN"], blocked_at__isnull=True,
    ).exists():
        raise PermissionDenied
    return lock_organization(context.organization_id)


def connection_for(context, connection_id, *, lock=False):
    rows = ExternalAgentConnection.objects.select_related("integration__service_settings").filter(
        organization_id=context.organization_id,
    )
    row = (rows.select_for_update(of=("self",)) if lock else rows).filter(pk=connection_id).first()
    if row is None:
        raise Http404
    return row


def binding_payload(binding):
    from chatballs.ai.external_agents.grant_definitions import stale_grants

    return {"agentId": binding.agent_id, "externalAgentId": binding.external_agent_id,
            "staleGrants": stale_grants(binding),
            "previousFields": binding.accepted_definitions.get("customLabels", []),
            "channelId": binding.agent.channel_id, "agentName": binding.agent.channel.name,
            "enabled": binding.enabled, "revision": binding.revision,
            "policyVersion": binding.policy_version,
            **{key: getattr(binding, field) for key, field in POLICY_FIELDS.items()}}


def connection_payload(row):
    service = row.integration.service_settings
    return {"id": row.pk, "integrationId": row.integration_id, "name": row.integration.name,
            "baseUrl": service.settings["base_url"], "enabled": row.enabled,
            "revision": row.revision, "keyConfigured": bool(row.inbound_key_hash),
            "compatible": bool(row.checked_at and row.capabilities),
            "checkedAt": row.checked_at.isoformat() if row.checked_at else None,
            "contentTypes": list(row.capabilities.get("contentTypes", [])),
            "checkFailure": row.integration.last_error_code if row.integration.last_error_code in {
                "access", "unavailable", "incompatible"} else None,
            "bindings": [binding_payload(binding) for binding in row.bindings.filter(enabled=True).order_by("agent_id")]}
