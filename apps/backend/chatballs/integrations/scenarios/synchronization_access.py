"""Exchange authority derives from explicit settings and a native entity link."""

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.synchronization import ServiceSynchronizationSettings
from chatballs.integrations.service_connections.binding import resolve
from chatballs.tenancy.context import TenantContext


def actor_for(tenant, settings):
    if settings.delegate_id is None:
        raise ExecutionDenied("permission")
    actor = current_actor(TenantContext.for_membership(settings.delegate))
    if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN} or actor.organization_id != tenant.organization_id:
        raise ExecutionDenied("permission")
    return actor


def active_pair(settings, pair_id):
    pair = next((p for p in settings.definition["synchronization"] if p["id"] == pair_id and p["enabled"]), None)
    if pair is None:
        raise ExecutionDenied("scenario_disabled")
    return pair


def conversation_for(tenant, link):
    if link.internal_kind == "conversation":
        row = Conversation.objects.select_related("contact", "channel").filter(pk=link.internal_id, organization_id=tenant.organization_id).first()
    else:
        row = Conversation.objects.select_related("contact", "channel").filter(contact_id=link.internal_id, organization_id=tenant.organization_id).order_by("-pk").first()
    if row:
        require_conversation_action(tenant, row, "conversations.operate")
    return row


def binding_for(tenant, link, *, registry=None):
    connection = Integration.objects.get(pk=link.integration_id, organization_id=tenant.organization_id)
    if not connection.is_active or connection.status != "OK":
        raise ExecutionDenied("connection_paused")
    _, adapter, _ = resolve(connection, registry)
    entity = next((e for e in adapter.entities if e.key == link.external_kind and link.internal_kind in e.native_entities), None)
    if entity is None or entity.synchronization is None:
        raise ExecutionDenied("operation_unavailable")
    return connection, entity.synchronization


def authorize_exchange(tenant, run):
    data = run.definition["exchange"]
    settings = ServiceSynchronizationSettings.objects.select_related("delegate__user", "delegate__organization").get(
        pk=data["settings"], organization_id=tenant.organization_id)
    actor = actor_for(tenant, settings)
    if actor.membership_id != run.initiator_id or tenant.membership_id != run.initiator_id:
        raise ExecutionDenied("permission")
    active_pair(settings, data["pair"]["id"])
    from chatballs.integrations.execution.permissions import authorize
    return authorize(actor, run.definition["document"], run.conversation_id)
