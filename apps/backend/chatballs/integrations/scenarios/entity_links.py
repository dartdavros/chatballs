"""Link commands preserve domain visibility and never merge identities."""

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.service_connections.binding import resolve


def endpoint(tenant, connection_id, entity, conversation, *, registry=None):
    connection = Integration.objects.select_for_update().get(pk=connection_id, organization_id=tenant.organization_id)
    if not connection.is_active or connection.status != "OK":
        raise ExecutionDenied("connection_paused")
    _, adapter, _ = resolve(connection, registry or default_registry())
    descriptor = next((e for e in adapter.entities if e.key == entity), None)
    if descriptor is None or conversation is None:
        raise ExecutionDenied("context")
    kind = "contact" if "contact" in descriptor.native_entities else "conversation" if "conversation" in descriptor.native_entities else None
    identity = conversation.contact_id if kind == "contact" else conversation.pk
    if kind is None or not identity:
        raise ExecutionDenied("context")
    return connection, kind, identity


def link(tenant, conversation, connection_id, entity, external_id, *, revision=None, replace=False, registry=None):
    if not isinstance(external_id, str) or not 1 <= len(external_id.strip()) <= 512:
        raise ExecutionDenied("arguments")
    connection, kind, identity = endpoint(tenant, connection_id, entity, conversation, registry=registry)
    row = EntityLink.objects.select_for_update().filter(integration=connection, internal_kind=kind,
        internal_id=identity, external_kind=entity).first()
    if row is not None:
        if row.active and row.external_id == external_id:
            return row
        if not replace or row.revision != revision:
            raise ExecutionDenied("state_changed")
        row.external_id, row.active, row.revision = external_id, True, row.revision + 1
        row.save()
        return row
    return EntityLink.objects.create(organization_id=tenant.organization_id, integration=connection,
        internal_kind=kind, internal_id=identity, external_kind=entity, external_id=external_id)


def snapshot(conversation):
    if conversation is None:
        return []
    from django.db.models import Q
    return list(EntityLink.objects.filter(organization_id=conversation.organization_id, active=True).filter(
        Q(internal_kind="conversation", internal_id=conversation.pk) | Q(internal_kind="contact", internal_id=conversation.contact_id)
    ).values("id", "integration_id", "internal_kind", "internal_id", "external_kind", "external_id", "revision"))


def has_link(conversation, connection_id, entity):
    if conversation is None:
        raise ExecutionDenied("context")
    from django.db.models import Q
    connection = Integration.objects.filter(pk=connection_id, organization_id=conversation.organization_id).first()
    if connection is None:
        raise ExecutionDenied("connection_missing")
    _, adapter, _ = resolve(connection)
    if not any(item.key == entity for item in adapter.entities):
        raise ExecutionDenied("operation_unavailable")
    return EntityLink.objects.filter(organization_id=conversation.organization_id, active=True,
        integration_id=connection_id, external_kind=entity).filter(Q(internal_kind="conversation", internal_id=conversation.pk)
            | Q(internal_kind="contact", internal_id=conversation.contact_id)).exists()
