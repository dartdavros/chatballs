"""Native effects share leases, policies, approvals, budgets and checkpoints."""

from time import monotonic

from django.db import transaction
from django.utils import timezone

from chatballs.identity.models import EmployeeRole
from chatballs.identity.policy import has_capability_any_scope
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution import checkpoints, native_results
from chatballs.integrations.execution.actions import step_target
from chatballs.integrations.execution.approvals import approved, invocation_digest
from chatballs.integrations.execution.native_context import context_for
from chatballs.integrations.execution.native_locale import native_locale
from chatballs.integrations.execution.native_system import preflight  # noqa: F401
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    authorize_run,
    validate_arguments,
)
from chatballs.integrations.execution.snapshots import check_contract
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


def require_action(tenant, action, run, arguments):
    if action.authority != "tenant":
        raise ExecutionDenied("permission")
    if action.capability and not has_capability_any_scope(tenant.membership, action.capability):
        raise ExecutionDenied("permission")
    manager = tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    grant = ActionGrant.objects.filter(organization_id=tenant.organization_id,
        membership=tenant.membership, integration__isnull=True, native_key=action.key,
        operation_key="", enabled=True).first()
    if not manager and grant is None:
        raise ExecutionDenied("permission")
    scopes = set()
    from chatballs.webchat.proactive_guards import for_run
    if for_run(run) is not None:
        scopes.add("conversation")
    cursor = run
    while cursor:
        scopes.add(cursor.definition["document"]["access"]["scope"])
        if cursor.scenario_id:
            current = ScenarioDefinition.objects.get(pk=cursor.scenario_id,
                organization_id=tenant.organization_id)
            scopes.add(current.definition["access"]["scope"])
        cursor = cursor.parent if cursor.parent_id else None
    if grant:
        scopes.add(grant.scope)
    if not scopes <= {"organization", "conversation", "contact"}:
        raise ExecutionDenied("context")
    scope = "contact" if "contact" in scopes else "conversation" if "conversation" in scopes else "organization"
    if action.scope == "organization" and scope != "organization":
        raise ExecutionDenied("context")
    if scope != "organization":
        if run.conversation_id is None:
            raise ExecutionDenied("context")
        if "conversation_id" in arguments and str(arguments["conversation_id"]) != str(run.conversation_id):
            raise ExecutionDenied("context")
    return scope


def _result(action, result):
    from chatballs.integrations.execution.budgets import size
    from chatballs.integrations.execution.errors import KNOWN
    # A confirmed domain rejection may have a durable denial audit. It is not
    # an exception/rollback or an ambiguous effect, and carries no output data.
    if isinstance(result, OperationResult) and result.state == ResultState.FAILED:
        if (result.data not in (None, {}) or result.files or result.error_code not in KNOWN
                or result.continuation or result.external_reference or result.deadline):
            raise ExecutionDenied("invalid_result")
        return result
    if (not isinstance(result, OperationResult) or result.state != ResultState.COMPLETED
            or validate_value(action.operation.output, result.data)
            or size({"data": result.data, "files": [vars(file) for file in result.files]})
                > action.operation.limits.max_response_bytes):
        raise ExecutionDenied("invalid_result")
    return result


def prepare(tenant, token):
    from chatballs.integrations.execution.actions import NativeCatalog
    from chatballs.integrations.execution.runner import _commit
    run, step, valid = checkpoints.locked(tenant, token)
    if not valid:
        return
    action = native_action(step.operation_key)
    if action is None or action.contract_version != step.adapter_version:
        raise ExecutionDenied("version_incompatible")
    check_contract(run, step_target(step), action.operation, NativeCatalog(action.contract_version))
    receipt = NativeEffectReceipt.objects.filter(step=step).first()
    if receipt is not None:
        if receipt.invocation_digest != invocation_digest(step, run):
            raise ExecutionDenied("version_incompatible")
        result = _result(action, native_results.restored(receipt))
        native_results.validate_files(action, result, step)
        _commit(tenant, token, result)
        return
    if step.sent_at is not None:
        checkpoints.finish(run, step, "unknown", code="outcome_unavailable")
        return
    actor = TenantContext.for_membership(run.initiator) if run.initiator_id else tenant
    actor, _ = authorize_run(actor, run)
    if run.cancel_requested_at:
        checkpoints.finish(run, step, "cancelled")
        return
    arguments = step.definition["arguments"]
    scope = require_action(actor, action, run, arguments)
    validate_arguments(actor, run.conversation_id, action.operation, arguments)
    from chatballs.integrations.execution.ai_policy import needs_confirmation
    if needs_confirmation(run, action.operation) and not approved(step, run):
        raise ExecutionDenied("approval_expired")
    return run, step, action, actor, scope, arguments


def _execute(tenant, token):
    from chatballs.integrations.execution.runner import _commit
    prepared = prepare(tenant, token)
    if prepared is None:
        return
    run, step, action, actor, scope, arguments = prepared
    step.sent_at = timezone.now()
    step.save(update_fields=["sent_at"])
    from chatballs.identity.audit_context import native_audit
    from chatballs.integrations.automation_events.causality import origin
    from chatballs.integrations.execution.budgets import causal_chain
    started = monotonic()
    with origin(causal_chain(run)), native_audit(run, step, actor), native_locale(actor):
        result = _result(action, action.execute(context_for(run, step, action, actor, scope, arguments), arguments))
    native_results.save(run, step, action, result, actor=actor)
    _commit(tenant, token, result, elapsed=monotonic() - started)



def run_native(tenant, token):
    with tenant_atomic(tenant):
        native = ScenarioStep.objects.filter(pk=token.step_id, run_id=token.run_id,
            organization_id=tenant.organization_id, integration__isnull=True, adapter_key="chatballs").exists()
    if not native:
        return False
    with tenant_atomic(tenant):
        key = ScenarioStep.objects.values_list("operation_key", flat=True).get(pk=token.step_id)
    action = native_action(key)
    if action is None:
        return False
    if action.execution == "io":
        from chatballs.integrations.execution.native_io import run_io
        run_io(tenant, token)
        return True
    try:
        with tenant_atomic(tenant), transaction.atomic():
            _execute(tenant, token)
    except Exception as error:
        # A local failure rolled back the domain change and its receipt.
        # Values/exceptions may contain internal text: only a safe code persists.
        code = str(error) if isinstance(error, ExecutionDenied) else "operation_rejected"
        with tenant_atomic(tenant):
            run, step, valid = checkpoints.locked(tenant, token)
            if valid:
                checkpoints.finish(run, step, "failed", code=code)
    return True
