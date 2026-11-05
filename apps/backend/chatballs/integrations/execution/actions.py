"""Resolve exactly the saved adapter contract, never the latest substitute."""

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration, IntegrationStatus
from chatballs.integrations.service_connections.binding import ServiceUnavailable, resolve


def resolve_action(organization_id, connection_id, target, *, registry=None, expected=None, recovering=False):
    if connection_id == "chatballs" and target.startswith("chatballs:"):
        operation, version = native_operation(target.removeprefix("chatballs:"))
        if expected and expected != ("chatballs", version):
            raise ExecutionDenied("version_incompatible")
        return None, None, NativeCatalog(version), None, operation
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


class NativeCatalog:
    """A native contract identity, never an Integration or a service adapter."""

    key = "chatballs"

    def __init__(self, contract_version):
        self.contract_version = contract_version


def connection_key(integration):
    return integration.pk if integration is not None else "chatballs"


def step_target(step):
    return {"connection": str(step.integration_id) if step.integration_id else "chatballs",
            "target": f"{'service' if step.integration_id else 'chatballs'}:{step.operation_key}"}


def native_operation(key):
    from chatballs.integrations.action_catalog.registry import native_action
    action = native_action(key)
    if action:
        return action.operation, action.contract_version
    from chatballs.integrations.execution.native_system import operation
    return operation(key), 1
