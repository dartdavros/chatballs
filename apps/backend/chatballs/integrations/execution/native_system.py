"""Transactional native effects with a result receipt in the domain transaction."""

from django.core.exceptions import ValidationError

from chatballs.conversations.models import Conversation
from chatballs.integrations.action_catalog.registry import action_schemas
from chatballs.integrations.adapters.contracts import (
    Effect,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import load_organization


def execute(context, operation, arguments):
    try:
        return _execute(context, operation, arguments)
    except (ExecutionDenied, ValidationError, Conversation.DoesNotExist) as error:
        # A known domain rejection rolled back the local transaction, including
        # its receipt. Transport/commit failures retain the unknown protocol.
        code = str(error) if isinstance(error, ExecutionDenied) else "arguments"
        return OperationResult(ResultState.FAILED, error_code=code)


def preflight(tenant, run, operation, arguments, *, registry=None):
    if operation.key == "entity_link.create":
        from chatballs.integrations.scenarios.entity_links import endpoint
        endpoint(tenant, arguments["connection"], arguments["entity"], run.conversation, registry=registry)


def _execute(context, operation, arguments):
    tenant = TenantContext.for_resource(load_organization(context.organization_id))
    with tenant_atomic(tenant):
        from chatballs.integrations.execution.budgets import lock_run
        run = lock_run(tenant, context.run_id)
        step = ScenarioStep.objects.select_for_update().get(run=run, path=context.step_path, effect_key=context.effect_key)
        values = step.definition
        if "nativeResult" in values:
            return OperationResult(ResultState.COMPLETED, data=values["nativeResult"])
        actor, conversation = authorize_run(TenantContext.for_membership(run.initiator), run)
        if run.cancel_requested_at:
            raise ExecutionDenied("permission")
        arguments = values["arguments"]
        if operation.key == "entity_link.create":
            from chatballs.integrations.scenarios.entity_links import link
            row = link(actor, conversation, arguments["connection"], arguments["entity"], arguments["external_id"])
            result = {"id": str(row.pk)}
        elif operation.key.startswith("synchronization."):
            from chatballs.integrations.scenarios.synchronization_effects import execute as exchange
            result = exchange(actor, run, operation.key, arguments)
            if isinstance(result, OperationResult):
                return result
        else:
            raise ExecutionDenied("operation_unavailable")
        values["nativeResult"] = result
        step.definition = values
        from chatballs.integrations.execution.effect_data import account_effect
        account_effect(run, step)
        step.save(update_fields=["content"])
        return OperationResult(ResultState.COMPLETED, data=result)


def operation(key):
    if key in {"synchronization.local", "synchronization.finish", "synchronization.plan", "synchronization.validate"}:
        inputs = TypeSpec("object", properties=(("expected", TypeSpec("string", required=True)),
            ("changes", TypeSpec("object", open=True, required=True)), ("delete", TypeSpec("boolean", required=True)))) if key.endswith("local") else TypeSpec("object")
        read = key in {"synchronization.plan", "synchronization.validate"}
        return OperationDescriptor(key, f"runs.{key.replace('.', '_')}", Effect.READ if read else Effect.UPDATE, inputs, TypeSpec("object", open=True),
            OperationHandlers(execute=execute, reconcile=execute), retry=RetryStrategy.SAFE_READ if read else RetryStrategy.IDEMPOTENCY_KEY)
    schema = next((s for s in action_schemas() if s.key == key), None)
    if schema is None or key != "entity_link.create":
        raise ExecutionDenied("operation_unavailable")
    return OperationDescriptor(key, schema.title_key, Effect.UPDATE, schema.input, schema.output,
        OperationHandlers(execute=execute, reconcile=execute), retry=RetryStrategy.IDEMPOTENCY_KEY,
        permission_scope=schema.permission_scope)
