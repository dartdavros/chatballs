"""Manual one-step execution uses the same snapshot service as direct actions."""

from rest_framework.response import Response

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.launch import launch, launch_direct
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    allowed_files,
    authorize,
    current_actor,
    direct_policy,
)
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.execution.views import RunAPIView
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.service_connections.payloads import field_payload


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


class ManualActionsView(RunAPIView):
    def get(self, request):
        tenant = current_actor(request.tenant_context)
        raw = request.query_params.get("conversation", "")
        conversation_id = int(raw) if raw.isdecimal() and len(raw) < 16 else None
        context = None
        if conversation_id is not None:
            from chatballs.conversations.access import require_conversation_action
            from chatballs.conversations.models import Conversation
            context = Conversation.objects.get(pk=conversation_id, organization_id=tenant.organization_id)
            require_conversation_action(tenant, context, "conversations.view")
        items = []
        for row in ScenarioDefinition.objects.filter(organization_id=tenant.organization_id, enabled=True):
            document = row.definition
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
                          "operationKey": block.get("target", "").removeprefix("service:"),
                          "parameters": parameter_schema(document["parameters"])})
        grants = ActionGrant.objects.filter(organization_id=tenant.organization_id, membership=tenant.membership, enabled=True)
        allowed = {(row.integration_id, row.operation_key) for row in grants}
        manager = tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
        for connection in Integration.objects.filter(organization_id=tenant.organization_id,
                kind="SERVICE").select_related("service_settings"):
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
                        "parameters": field_payload("", operation.input)})
        from chatballs.integrations.action_catalog.manual_catalog import manual_actions
        items.extend(manual_actions(tenant, grants, context))
        return Response({"items": items, "files": [{"id": str(file.public_id), "name": file.name}
                         for file in allowed_files(tenant, conversation_id)]})

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        preview = data.get("preview") is True
        confirmation = data.get("confirmation")
        if data.get("kind") == "operation":
            run, created = launch_direct(tenant=request.tenant_context, connection_id=data.get("connectionId"),
                operation_key=data.get("operationKey", ""), trigger_key=data.get("triggerKey"),
                arguments=data.get("parameters", {}), conversation_id=data.get("conversationId"), preview=preview, confirmation=confirmation)
        else:
            run, created = launch(tenant=request.tenant_context, scenario_id=data.get("scenarioId"),
                trigger_key=data.get("triggerKey"), parameters=data.get("parameters", {}), conversation_id=data.get("conversationId"), preview=preview, confirmation=confirmation)
        if preview:
            return Response({"preview": run})
        if created:
            record_audit_event(action="integrations.run_created", actor=request.user,
                organization=request.tenant_context.organization, object_type="ScenarioRun", object_id=str(run.public_id))
        return Response({"run": run_payload(run, detail=True, tenant=request.tenant_context)}, status=201 if created else 200)
