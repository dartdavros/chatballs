"""Create a composite Run from a signed, read-only plan."""

from chatballs.ai.diagnostic_redaction import integration_secrets
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.permissions import allowed_files, context_values
from chatballs.integrations.execution.payloads import clean_value
from chatballs.integrations.execution.plans import sign_plan, verify_plan
from chatballs.integrations.execution.snapshots import freeze
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.scenarios.values import RunValues, prepare_inputs
from chatballs.integrations.service_connections.payloads import field_payload


def snapshot(tenant, document, parameters, conversation, *, scenario, dedup, registry, preview, confirmation):
    spec = read_type(document["parameters"])
    files = {str(pk) for pk in allowed_files(tenant, conversation.pk if conversation else None).values_list("public_id", flat=True)}
    # The same boundary validates optional/nested/file inputs at launch.
    prepare_inputs(spec, {k: {"source": "constant", "value": v} for k, v in parameters.items()}, RunValues(files=files), registry=registry)
    frozen = freeze(tenant, document, scenario_id=scenario.public_id, registry=registry)
    context = context_values(conversation)
    plan = {"document": document, "parameters": parameters, "context": context, **frozen,
            "scenarioKey": str(scenario.public_id), "revision": scenario.revision}
    from chatballs.integrations.execution.budgets import MAX_SNAPSHOT, size
    from chatballs.integrations.execution.permissions import ExecutionDenied
    if size(plan) > MAX_SNAPSHOT:
        raise ExecutionDenied("budget_volume")
    if preview:
        secrets = integration_secrets(list(Integration.objects.filter(organization_id=tenant.organization_id)))
        return {"confirmation": sign_plan(tenant, plan), "operation": scenario.name, "note": "",
                "inputSchema": field_payload("", spec), "arguments": clean_value(spec, parameters, secrets)}
    if confirmation is not None:
        verify_plan(tenant, plan, confirmation)
    run = ScenarioRun(organization_id=tenant.organization_id, scenario=scenario, scenario_key=str(scenario.public_id),
        trigger_key=dedup, revision=scenario.revision, initiator=tenant.membership, conversation=conversation)
    run.definition = {"document": document, "parameters": parameters, "context": context,
                      "kind": "scenario", "composite": True, **frozen}
    run.structure = {"name": scenario.name, "definitionUpdatedAt": scenario.updated_at.isoformat()}
    run.save()
    from chatballs.integrations.execution.budgets import account_data, size
    account_data(run, size(run.definition))
    # Retain input files before a source run can lose its ownership.
    from chatballs.integrations.execution.files import lock_input_files, own_input_files
    from chatballs.integrations.adapters.contracts import OperationDescriptor, OperationHandlers, Effect
    from chatballs.integrations.adapters.schema import TypeSpec
    from chatballs.integrations.scenario_state.steps import ScenarioStep
    from django.utils import timezone
    operation = OperationDescriptor("inputs", "", Effect.READ, spec, TypeSpec("object"), OperationHandlers())
    input_files = lock_input_files(tenant, operation, parameters)
    if input_files:
        owner = ScenarioStep(organization_id=run.organization_id, run=run, path="inputs",
            adapter_version=1, operation_key="", retry_strategy="none", state="completed", due_at=timezone.now())
        owner.definition = {}
        owner.save()
        own_input_files(owner, input_files)
    journal(run, "created")
    schedule(tenant, run)
    return run
