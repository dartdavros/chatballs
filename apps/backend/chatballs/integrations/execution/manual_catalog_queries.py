"""Current manual choices and lazy form metadata; never an execution grant."""

from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.manual_eligibility import ManualEligibility
from chatballs.integrations.execution.manual_initial_values import initial_values
from chatballs.integrations.execution.manual_presentation import (
    native_presentation,
    parameter_schema,  # noqa: F401 -- retained public import
    scenario_presentation,
    service_presentation,
)
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    allowed_files,
    current_actor,
    direct_policy,
)
from chatballs.integrations.execution.snapshots import walk
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.service_connections.binding import ServiceUnavailable, resolve
from chatballs.integrations.service_connections.payloads import field_payload
from chatballs.tenancy.database import tenant_atomic


def _selection(data):
    if "kind" not in data and "id" not in data:
        return None
    kind, identity = data.get("kind"), data.get("id", "")
    if kind not in {"scenario", "operation"} or not isinstance(identity, str) or not 0 < len(identity) <= 300:
        raise ExecutionDenied("arguments")
    if kind == "scenario":
        try:
            identity = str(UUID(identity))
        except (ValueError, TypeError):
            raise ExecutionDenied("arguments") from None
    else:
        connection, separator, key = identity.partition(":")
        if not separator or not key or (connection != "chatballs" and (not connection.isascii() or not connection.isdecimal() or len(connection) >= 16)):
            raise ExecutionDenied("arguments")
    return kind, identity


def _conversation(tenant, data):
    if "conversation" not in data:
        return None
    raw = data.get("conversation")
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdecimal() or not 0 < len(raw) < 16:
        raise ExecutionDenied("context")
    from chatballs.conversations.access import require_conversation_action
    from chatballs.conversations.models import Conversation
    conversation = Conversation.objects.select_related("contact", "channel").get(
        pk=int(raw), organization_id=tenant.organization_id)
    require_conversation_action(tenant, conversation, "conversations.view")
    return conversation


def _scenario_items(tenant, conversation, connections, eligibility, selection, summary):
    if selection and selection[0] != "scenario":
        return
    rows = ScenarioDefinition.objects.filter(organization_id=tenant.organization_id, enabled=True)
    if selection:
        rows = rows.filter(public_id=selection[1])
    names = {str(row.pk): row.name for row in connections}
    for row in rows:
        document = row.definition
        if conversation is not None and document["access"]["scope"] not in {"conversation", "contact"}:
            continue
        try:
            frozen = eligibility.scenario(row)
        except (ExecutionDenied, ServiceUnavailable, ObjectDoesNotExist):
            continue
        actions = [block for block in walk(document["steps"]) if block["kind"] == "action"]
        first = actions[0] if actions else {}
        item = {"id": str(row.public_id), "kind": "scenario", "title": row.name,
                "available": True, "reason": "", "connectionId": first.get("connection"),
                "connection": names.get(str(first.get("connection")), ""),
                "operationKey": first.get("target", "").removeprefix("service:"),
                "presentation": scenario_presentation(row)}
        if not summary:
            item["parameters"] = parameter_schema(document["parameters"])
            item["plan"] = [block.get("name") or t(frozen["contracts"][
                f"{block['connection']}:{block['target']}"]["title_key"]) for block in actions
                ] if all(block["kind"] == "action" for block in document["steps"]) else []
        yield item


def _service_items(tenant, conversation, connections, grants, selection, summary):
    if selection and (selection[0] != "operation" or selection[1].startswith("chatballs:")):
        return
    allowed = {(row.integration_id, row.operation_key): row for row in grants if row.integration_id is not None}
    manager = tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    conversation_id = conversation.pk if conversation else None
    policies = {}
    registry = default_registry()
    for connection in connections:
        if not connection.is_active or connection.status != "OK" or getattr(connection, "service_settings", None) is None:
            continue
        try:
            _, adapter, _ = resolve(connection, registry)
        except ServiceUnavailable:
            continue
        for operation in adapter.operations:
            identity = f"{connection.pk}:{operation.key}"
            if selection and identity != selection[1]:
                continue
            grant = allowed.get((connection.pk, operation.key))
            if not manager and grant is None:
                continue
            # All SERVICE operations require the same dialog capability. Exact
            # targets are checked above; authorize once per effective grant scope.
            scope = grant.scope if grant else "conversation" if conversation else "organization"
            if scope not in policies:
                try:
                    direct_policy(tenant, connection.pk, operation.key, conversation_id)
                    policies[scope] = True
                except ExecutionDenied:
                    policies[scope] = False
            if not policies[scope]:
                continue
            item = {"id": identity, "kind": "operation", "title": t(operation.title_key),
                    "available": True, "reason": "", "connectionId": connection.pk,
                    "operationKey": operation.key, "connection": connection.name,
                    "readOnly": operation.effect == Effect.READ,
                    "presentation": service_presentation(connection, adapter, operation)}
            if not summary:
                item.update(parameters=field_payload("", operation.input), initialValues=initial_values(operation, conversation))
            yield item


def catalog(tenant, data):
    with tenant_atomic(tenant):
        tenant = current_actor(tenant)
        selection = _selection(data)
        summary = data.get("summary") == "1" and selection is None
        conversation = _conversation(tenant, data)
        if conversation is not None and conversation.archived_at is not None:
            if selection:
                raise ExecutionDenied("context")
            return {"items": [], "files": []}
        connections = Integration.objects.filter(organization_id=tenant.organization_id, kind="SERVICE").select_related("service_settings")
        if selection and selection[0] == "operation":
            connection_id = selection[1].partition(":")[0]
            connections = connections.none() if connection_id == "chatballs" else connections.filter(pk=int(connection_id))
        connections = list(connections)
        grants = list(ActionGrant.objects.filter(organization_id=tenant.organization_id, membership=tenant.membership, enabled=True))
        eligibility = ManualEligibility(tenant, conversation, grants=grants)
        items = list(_scenario_items(tenant, conversation, connections, eligibility, selection, summary))
        items.extend(_service_items(tenant, conversation, connections, grants, selection, summary))
        if conversation is None and (selection is None or (selection[0] == "operation" and selection[1].startswith("chatballs:"))):
            from chatballs.integrations.action_catalog.manual_catalog import manual_actions
            native_key = selection[1].removeprefix("chatballs:") if selection else None
            for item in manual_actions(tenant, grants, conversation, summary=summary, operation_key=native_key):
                item["presentation"] = native_presentation()
                items.append(item)
        if selection and not items:
            raise ExecutionDenied("operation_unavailable")
        files = [] if summary else [{"id": str(file.public_id), "name": file.name}
            for file in allowed_files(tenant, conversation.pk if conversation else None)]
        return {"item": items[0], "files": files} if selection else {"items": items, "files": files}
