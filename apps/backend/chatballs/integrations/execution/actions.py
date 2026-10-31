"""Resolve exactly the saved adapter contract, never the latest substitute."""

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.models import Integration, IntegrationStatus
from chatballs.integrations.service_connections.binding import ServiceUnavailable, resolve
from chatballs.integrations.execution.permissions import ExecutionDenied


def resolve_action(organization_id, connection_id, target, *, registry=None, expected=None, recovering=False):
    registry = registry or default_registry()
    if not str(connection_id).isdecimal() or not target.startswith("service:"):
        raise ExecutionDenied("operation_unavailable")
    integration = Integration.objects.select_related("service_settings").filter(
        pk=int(connection_id), organization_id=organization_id,
    ).first()
    if integration is None:
        raise ExecutionDenied("connection_missing")
    if not recovering and (not integration.is_active or integration.status != IntegrationStatus.OK):
        raise ExecutionDenied("connection_paused")
    try:
        row, adapter, method = resolve(integration, registry)
    except ServiceUnavailable as error:
        raise ExecutionDenied(error.code) from None
    if expected and (adapter.key, adapter.contract_version) != expected:
        raise ExecutionDenied("version_incompatible")
    operation = adapter.operation(target.removeprefix("service:"))
    if operation is None:
        raise ExecutionDenied("operation_unavailable")
    return integration, row, adapter, method, operation
