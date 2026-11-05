"""One transaction creates an immutable snapshot, effect identity and outbox."""

import hashlib

from django.utils import timezone

from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.actions import connection_key, resolve_action
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    allowed_files,
    authorize,
    context_values,
    direct_policy,
    view_run,
)
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.scenarios.values import RunValues, prepare_inputs
from chatballs.tenancy.database import tenant_atomic


def launch(*, tenant, scenario_id, trigger_key, parameters, conversation_id=None, registry=None, preview=False, confirmation=None, automatic=None):
    if not isinstance(trigger_key, str) or not 1 <= len(trigger_key) <= 200:
        raise ExecutionDenied("trigger")
    dedup = hashlib.sha256(trigger_key.encode()).hexdigest()
    with tenant_atomic(tenant):
        # The scenario lock also serializes competing manual launches. DB unique
        # constraint is the final guard; revision never participates in dedup.
        scenario = ScenarioDefinition.objects.select_for_update().get(
            public_id=scenario_id, organization_id=tenant.organization_id,
        )
        document = scenario.definition
        kind = automatic["trigger"]["kind"] if automatic else "staff"
        if automatic:
            from chatballs.integrations.execution.automation import check
            check(tenant, document, scenario.pk, automatic["trigger"])
        tenant, conversation = authorize(tenant, document, conversation_id, scenario_id=scenario.pk, trigger_kind=kind)
        if not any(t["kind"] == kind for t in document["triggers"]):
            raise ExecutionDenied("permission")
        existing = ScenarioRun.objects.filter(organization_id=tenant.organization_id,
            scenario_key=str(scenario.public_id), trigger_key=dedup).first()
        if existing and not preview:
            view_run(tenant, existing)
            # Reuse is identity only: changed input cannot replace the snapshot.
            return existing, False
        from chatballs.integrations.execution.conditions import require_conditions
        from chatballs.integrations.scenarios.values import RunValues
        require_conditions(document, conversation, parameters, registry=registry,
            values=RunValues(parameters=parameters, context=context_values(conversation), event=automatic["event"]) if automatic else None)
        if automatic or len(document["steps"]) != 1 or document["steps"][0]["kind"] != "action":
            from chatballs.integrations.execution.composite_launch import snapshot
            return snapshot(tenant, document, parameters, conversation, scenario=scenario, dedup=dedup,
                            registry=registry, preview=preview, confirmation=confirmation, automatic=automatic), True
        return _snapshot(tenant, document, parameters, conversation, scenario=scenario, dedup=dedup,
                         scenario_key=str(scenario.public_id), registry=registry, preview=preview, confirmation=confirmation), True


def launch_direct(*, tenant, connection_id, operation_key, trigger_key, arguments, conversation_id=None, registry=None, preview=False, confirmation=None):
    if not isinstance(trigger_key, str) or not 1 <= len(trigger_key) <= 200 or not isinstance(arguments, dict):
        raise ExecutionDenied("arguments")
    from chatballs.integrations.models import Integration
    if connection_id == "chatballs" and conversation_id is not None:
        from chatballs.integrations.action_catalog.registry import native_action
        action = native_action(operation_key)
        field = action.operation.input.field("conversation_id") if action else None
        if field and field.required:
            arguments = {"conversation_id": str(conversation_id), **arguments}
    with tenant_atomic(tenant):
        if connection_id != "chatballs":
            Integration.objects.select_for_update().get(pk=connection_id, organization_id=tenant.organization_id)
        tenant, document, grant, conversation = direct_policy(tenant, connection_id, operation_key, conversation_id)
        document["steps"] = [{"id": "operation", "kind": "action", "connection": str(connection_id),
            "target": f"{'chatballs' if connection_id == 'chatballs' else 'service'}:{operation_key}", "inputs": {key: {"source": "constant", "value": value} for key, value in arguments.items()}}]
        key = f"operation:{connection_id}:{operation_key}"
        dedup = hashlib.sha256(trigger_key.encode()).hexdigest()
        existing = ScenarioRun.objects.filter(organization_id=tenant.organization_id, scenario_key=key, trigger_key=dedup).first()
        if existing and not preview:
            view_run(tenant, existing)
            return existing, False
        return _snapshot(tenant, document, {}, conversation, scenario=None, dedup=dedup, scenario_key=key,
            registry=registry, grant_id=grant.pk if grant else None, preview=preview, confirmation=confirmation), True


def _snapshot(tenant, document, parameters, conversation, *, scenario, dedup, scenario_key, registry, grant_id=None, preview=False, confirmation=None, ai_binding=None):
    spec = read_type(document["parameters"])
    if validate_value(spec, parameters):
        raise ExecutionDenied("arguments")
    block = document["steps"][0]
    integration, _row, adapter, _method, operation = resolve_action(
        tenant.organization_id, block.get("connection"), block["target"], registry=registry,
    )
    files = {str(pk) for pk in allowed_files(tenant, conversation.pk if conversation else None).values_list("public_id", flat=True)}
    context = ai_binding.get("testContext", {}) if ai_binding and ai_binding.get("tester") else context_values(conversation)
    arguments = prepare_inputs(operation.input, block["inputs"],
        RunValues(parameters=parameters, context=context, files=files), registry=registry)
    now = timezone.now()
    from chatballs.integrations.execution.plans import sign_plan, verify_plan
    plan = {"document": document, "parameters": parameters, "context": context, "arguments": arguments,
            "scenarioKey": scenario_key, "revision": scenario.revision if scenario else 1,
            "connection": connection_key(integration), "adapter": adapter.key, "version": adapter.contract_version, "grant": grant_id}
    from chatballs.integrations.execution.contract_schemas import write_spec
    from chatballs.integrations.execution.snapshots import signature
    contract = {"adapter": adapter.key, "version": adapter.contract_version, "signature": signature(operation),
                "input": write_spec(operation.input), "output": write_spec(operation.output), "title_key": operation.title_key}
    plan["contract"] = contract
    if preview:
        from chatballs.ai.diagnostic_redaction import integration_secrets
        from chatballs.i18n import t
        from chatballs.integrations.execution.payloads import clean_value
        from chatballs.integrations.service_connections.payloads import field_payload
        return {"confirmation": sign_plan(tenant, plan), "operation": t(operation.title_key),
                "note": t(operation.description_key) if operation.description_key else "",
                "inputSchema": field_payload("", operation.input),
                "arguments": clean_value(operation.input, arguments, integration_secrets([integration] if integration else []))}
    expires = verify_plan(tenant, plan, confirmation) if confirmation is not None else None
    from chatballs.integrations.execution.files import lock_input_files, own_input_files
    input_files = lock_input_files(tenant, operation, arguments)
    run = ScenarioRun(organization_id=tenant.organization_id, scenario=scenario,
        scenario_key=scenario_key, trigger_key=dedup, revision=scenario.revision if scenario else 1,
        initiator=tenant.membership, conversation=conversation)
    run.definition = {"document": document, "parameters": parameters, "context": context,
                      "kind": "scenario" if scenario else "direct", "grantId": grant_id,
                      "contracts": {f"{connection_key(integration)}:{block['target']}": contract}}
    if ai_binding:
        run.definition = {**run.definition, "ai": ai_binding}
    from chatballs.integrations.scenarios.entity_links import snapshot as link_snapshot
    data = run.definition
    data["links"] = link_snapshot(conversation)
    run.definition = data
    run.structure = {"name": scenario.name if scenario else "", "operationTitle": operation.title_key,
                     "connection": (integration.name if integration else ""), "definitionUpdatedAt": scenario.updated_at.isoformat() if scenario else None}
    if ai_binding:
        from chatballs.ai.models import AIAgent
        run.structure = {**run.structure, "agentName": AIAgent.objects.get(pk=ai_binding["agent"]).channel.name,
                         "testChat": bool(ai_binding.get("tester"))}
    run.save()
    step = ScenarioStep(organization_id=tenant.organization_id, run=run,
        path=f"steps/{block['id']}", integration=integration, adapter_key=adapter.key,
        adapter_version=adapter.contract_version, operation_key=operation.key,
        retry_strategy=operation.retry, due_at=now)
    step.definition = {"arguments": arguments}
    from chatballs.integrations.execution.ai_policy import (
        needs_confirmation as confirmation_required,
    )
    needs_confirmation = confirmation_required(run, operation)
    step.state = "approval" if needs_confirmation and expires is None else "queued"
    if expires is not None:
        from chatballs.integrations.execution.approvals import invocation_digest
        step.confirmed_digest = invocation_digest(step, run)
        step.approval_expires_at = expires
    step.save()
    own_input_files(step, input_files)
    run.state = step.state
    run.save(update_fields=["state"])
    journal(run, "created", step)
    if ai_binding:
        from chatballs.integrations.execution.ai_deadlines import schedule_expiry
        schedule_expiry(tenant, run, step)
    if step.state == "queued":
        schedule(tenant, run)
    return run
