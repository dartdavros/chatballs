"""Agent actions retain product authorization, AI runtime and effect boundaries."""

from functools import partial

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as APIValidationError

from chatballs.ai import agent_card_commands as commands
from chatballs.ai import agent_card_queries as queries
from chatballs.ai.agent_card import agent_card_for_context
from chatballs.ai.diagnostic_redaction import DiagnosticRedactor, integration_secrets
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.ai.test_chat_service import run_test_chat
from chatballs.integrations.action_catalog import agent_test_schemas
from chatballs.integrations.action_catalog.agent_schemas import (
    DIRECTORY,
    EDIT,
    FILTERS,
    ID,
    OUTPUT,
    PAGE,
    TOOLS,
    field,
)
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.execution.payloads import clean_value
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


def invoke(context, values, *, service, body=False, by_id=False, connection=False):
    with tenant_atomic(context.tenant):
        if by_id:
            try:
                agent_card_for_context(context=context.tenant, agent_id=values["agent_id"])
            except ObjectDoesNotExist:
                raise NativeAccessDenied("context") from None
        args = [context.tenant]
        if by_id:
            args.append(values["agent_id"])
        if connection:
            args.append(values["integration_id"])
        if body:
            args.append({key: value for key, value in values.items() if key != "agent_id"})
        try:
            result = service(*args)
        except PermissionDenied:
            raise NativeAccessDenied("permission") from None
        except ValidationError:
            raise NativeOperationRejected("arguments") from None
        result = json_data(result)
        secrets = integration_secrets(Integration.objects.filter(organization_id=context.tenant.organization_id))
        redactor = DiagnosticRedactor(Pseudonymizer(), secrets)
        cards = result.get("items", []) if service is queries.listing else [result.get("agent", {})]
        servers = list(result.get("tools", []))
        for card in cards:
            servers.extend(card.get("tools", []))
            if "modelParams" in card:
                card["modelParams"] = redactor.clean(card["modelParams"])
        for server in servers:
            server["lastError"] = redactor.text(server["lastError"])
    return OperationResult(ResultState.COMPLETED, result)


def test_chat(context, values):
    with tenant_atomic(context.tenant):
        try:
            queries.require(context.tenant, "ai.manage")
            agent_card_for_context(context=context.tenant, agent_id=values["agent_id"])
        except (PermissionDenied, ObjectDoesNotExist):
            raise NativeAccessDenied("context") from None
    try:
        status, result = run_test_chat(context.tenant, values["agent_id"], values)
    except APIValidationError:
        raise NativeOperationRejected("arguments") from None
    if status in (400, 404):
        raise NativeOperationRejected("arguments")
    if status != 200:
        return OperationResult(ResultState.FAILED, error_code="conditions_unavailable")
    with tenant_atomic(context.tenant):
        secrets = integration_secrets(Integration.objects.filter(organization_id=context.tenant.organization_id))
        result["serviceActions"] = clean_value(None, result["serviceActions"], secrets)
    return OperationResult(ResultState.COMPLETED, json_data(result))


for key, inputs, outputs, handler, method, route, view, capability, effect, execution in (
    ("agents.get", FILTERS, PAGE, partial(invoke, service=queries.listing, body=True), "GET", "", "AgentCardListView", "ai.view", Effect.READ, "local"),
    ("agents.directory.get", obj(q=field("search")), DIRECTORY, partial(invoke, service=queries.directory, body=True), "GET", "directory/", "AgentDirectoryView", "ai.view", Effect.READ, "local"),
    ("agents.post", obj(name=required(EDIT["name"]), groupId=EDIT["groupId"]), OUTPUT, partial(invoke, service=commands.create, body=True), "POST", "", "AgentCardListView", "ai.manage", Effect.CREATE, "local"),
    ("agents.detail.get", obj(agent_id=ID), OUTPUT, partial(invoke, service=queries.detail, by_id=True), "GET", "<int:agent_id>/", "AgentCardDetailView", "ai.view", Effect.READ, "io"),
    ("agents.detail.patch", obj(agent_id=ID, **EDIT), OUTPUT, partial(invoke, service=commands.update, by_id=True, body=True), "PATCH", "<int:agent_id>/", "AgentCardDetailView", "ai.manage", Effect.UPDATE, "io"),
    ("agents.detail.delete", obj(agent_id=ID), obj(), partial(invoke, service=commands.delete, by_id=True), "DELETE", "<int:agent_id>/", "AgentCardDetailView", "ai.manage", Effect.DELETE, "local"),
    ("agents.tools.get", obj(agent_id=ID), obj(tools=TOOLS), partial(invoke, service=queries.tools, by_id=True), "GET", "<int:agent_id>/tools/", "AgentCardToolsView", "ai.view", Effect.READ, "local"),
    ("agents.activate.post", obj(agent_id=ID), OUTPUT, partial(invoke, service=partial(commands.set_active, active=True), by_id=True), "POST", "<int:agent_id>/activate/", "AgentCardActivateView", "ai.manage", Effect.UPDATE, "local"),
    ("agents.deactivate.post", obj(agent_id=ID), OUTPUT, partial(invoke, service=partial(commands.set_active, active=False), by_id=True), "POST", "<int:agent_id>/deactivate/", "AgentCardDeactivateView", "ai.manage", Effect.UPDATE, "local"),
    ("agents.connections.post", obj(agent_id=ID, integrationId=field("integrationId", "integer", required=True), force=field("force", "boolean")), OUTPUT, partial(invoke, service=commands.bind, by_id=True, body=True), "POST", "<int:agent_id>/connections/", "AgentCardConnectionsView", "integrations.manage", Effect.UPDATE, "local"),
    ("agents.connection.delete", obj(agent_id=ID, integration_id=field("integrationId", "integer", required=True)), OUTPUT, partial(invoke, service=commands.unbind, by_id=True, connection=True), "DELETE", "<int:agent_id>/connections/<int:integration_id>/", "AgentCardConnectionDetailView", "integrations.manage", Effect.DELETE, "local"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"agents/{route}",
        view=f"chatballs.ai.agent_card_views.{view}", method=method, effect=effect, execution=execution)

action(key="agents.test_chat.post", title="native.agents.test_chat.post", input=agent_test_schemas.INPUT,
    output=agent_test_schemas.OUTPUT, handler=test_chat, capability="ai.manage", scope="organization",
    route="agents/<int:agent_id>/test-chat/", view="chatballs.ai.test_chat_views.AgentCardTestChatView",
    method="POST", effect=Effect.OTHER, execution="io")
