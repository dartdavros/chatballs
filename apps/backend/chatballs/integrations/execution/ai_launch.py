"""The agent entry point builds snapshots in the same launch/runner pipeline."""

import hashlib
from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.execution.ai_policy import current
from chatballs.integrations.execution.conditions import require_conditions
from chatballs.integrations.execution.launch import _snapshot
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.database import tenant_atomic


def launch_ai(tenant, binding, arguments, trigger_key, *, preview=False, registry=None):
    with tenant_atomic(tenant):
        grant, conversation = current(tenant, binding)
        if grant.delegate_id:
            from chatballs.integrations.execution.native_principal import delegate_context
            tenant = delegate_context(tenant, grant, binding)
        scenario = grant.scenario
        if scenario:
            document = scenario.definition
            parameters = arguments
            key = str(scenario.public_id)
        else:
            document = empty_definition()
            if grant.native_key:
                from chatballs.integrations.action_catalog.registry import native_action
                action = native_action(grant.native_key)
                if action is None:
                    raise ExecutionDenied("operation_unavailable")
                document["access"]["scope"] = action.scope
                field = action.operation.input.field("conversation_id")
                if conversation and field and field.required:
                    arguments = {"conversation_id": str(conversation.pk), **arguments}
            else:
                document["access"]["scope"] = "conversation"
            connection = "chatballs" if grant.native_key else str(grant.integration_id)
            operation = grant.native_key or grant.operation_key
            document["steps"] = [{"id": "operation", "kind": "action", "connection": connection,
                "target": f"{'chatballs' if grant.native_key else 'service'}:{operation}", "inputs": {
                    name: {"source": "constant", "value": value} for name, value in arguments.items()}}]
            parameters = {}
            key = f"operation:{connection}:{operation}"
        require_conditions(document, conversation, parameters, registry=registry)
        context_id = conversation.pk if conversation else f"test:{binding['tester']}"
        dedup = hashlib.sha256(f"ai:{binding['agent']}:{context_id}:{trigger_key}".encode()).hexdigest()
        existing = ScenarioRun.objects.filter(organization_id=tenant.organization_id,
            scenario_key=key, trigger_key=dedup).first()
        if existing and not preview:
            if existing.definition.get("ai", {}).get("grant") != grant.pk:
                raise ExecutionDenied("permission")
            return existing
        binding = {**binding, "approvalDeadline": (timezone.now() + timedelta(minutes=30)).isoformat()}
        if scenario and (len(document["steps"]) != 1 or document["steps"][0]["kind"] != "action"):
            from chatballs.integrations.execution.composite_launch import snapshot
            return snapshot(tenant, document, parameters, conversation, scenario=scenario, dedup=dedup,
                registry=registry, preview=preview, confirmation=None, ai_binding=binding)
        return _snapshot(tenant, document, parameters, conversation, scenario=scenario,
            dedup=dedup, scenario_key=key, registry=registry, preview=preview, ai_binding=binding)
