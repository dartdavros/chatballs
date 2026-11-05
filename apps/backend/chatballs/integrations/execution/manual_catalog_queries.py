"""Manual one-step execution uses the same snapshot service as direct actions."""


from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    allowed_files,
    authorize,
    current_actor,
    direct_policy,
)
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.service_connections.payloads import field_payload
from chatballs.tenancy.database import tenant_atomic


def parameter_schema(data):
    result = field_payload("", read_type(data))
    def titles(field, schema):
        if schema.get("title"):
            field["title"] = schema["title"]
        for child in field.get("fields", []):
            titles(child, schema.get("properties", {}).get(child["name"], {}))
        if field.get("items"):
            titles(field["items"], schema.get("items", {}))
    titles(result, data)
    return result


def catalog(tenant, data):
    with tenant_atomic(tenant):
        tenant = current_actor(tenant)
        raw = data.get("conversation", "")
        conversation_id = int(raw) if raw.isdecimal() and len(raw) < 16 else None
        context = None
        if conversation_id is not None:
            from chatballs.conversations.access import require_conversation_action
            from chatballs.conversations.models import Conversation
            context = Conversation.objects.get(pk=conversation_id, organization_id=tenant.organization_id)
            require_conversation_action(tenant, context, "conversations.view")
            if context.archived_at is not None:
                return {"items": [], "files": []}
        connections = list(Integration.objects.filter(organization_id=tenant.organization_id,
            kind="SERVICE").select_related("service_settings"))
        connection_names = {str(row.pk): row.name for row in connections}
        items = []
        for row in ScenarioDefinition.objects.filter(organization_id=tenant.organization_id, enabled=True):
            document = row.definition
            if context is not None and document["access"]["scope"] not in {"conversation", "contact"}:
                continue
            try:
                authorize(tenant, document, conversation_id, scenario_id=row.pk)
            except ExecutionDenied:
                continue
            from chatballs.integrations.execution.snapshots import walk
            actions = [b for b in walk(document["steps"]) if b["kind"] == "action"]
            block = actions[0] if actions else {}
            available, reason = True, ""
            try:
                require_supported_sources(document)
                from chatballs.integrations.execution.snapshots import freeze
                freeze(tenant, document, scenario_id=row.public_id)
            except ExecutionDenied as error:
                available, reason = False, error_message(str(error))
            items.append({"id": str(row.public_id), "kind": "scenario", "title": row.name,
                          "available": available, "reason": reason,
                          "connectionId": block.get("connection"),
                          "connection": connection_names.get(str(block.get("connection")), ""),
                          "operationKey": block.get("target", "").removeprefix("service:"),
                          "parameters": parameter_schema(document["parameters"])})
        grants = ActionGrant.objects.filter(organization_id=tenant.organization_id, membership=tenant.membership, enabled=True)
        allowed = {(row.integration_id, row.operation_key) for row in grants}
        manager = tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
        for connection in connections:
            settings = getattr(connection, "service_settings", None)
            if settings is None:
                continue
            adapter = default_registry().adapter(settings.adapter_key)
            if not adapter or adapter.contract_version != settings.adapter_version:
                continue
            for operation in adapter.operations:
                if manager or (connection.pk, operation.key) in allowed:
                    try:
                        direct_policy(tenant, connection.pk, operation.key, conversation_id)
                    except ExecutionDenied:
                        continue
                    available, reason = True, ""
                    try:
                        resolve_action(tenant.organization_id, connection.pk, f"service:{operation.key}")
                    except ExecutionDenied as error:
                        available, reason = False, error_message(str(error))
                    items.append({"id": f"{connection.pk}:{operation.key}", "kind": "operation", "title": t(operation.title_key),
                        "available": available, "reason": reason,
                        "connectionId": connection.pk, "operationKey": operation.key, "connection": connection.name,
                        "readOnly": operation.effect == Effect.READ,
                        "parameters": field_payload("", operation.input)})
        if context is None:
            from chatballs.integrations.action_catalog.manual_catalog import manual_actions
            items.extend(manual_actions(tenant, grants, context))
        return {"items": items, "files": [{"id": str(file.public_id), "name": file.name}
                         for file in allowed_files(tenant, conversation_id)]}
