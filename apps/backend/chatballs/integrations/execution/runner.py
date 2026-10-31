"""One bounded step: claim → prepare → fenced send marker → I/O → commit."""

from dataclasses import replace

from django.db import connection
from django.utils import timezone

from chatballs.integrations.adapters.contracts import OperationResult, READ_EFFECTS, ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.adapters.files import file_store
from chatballs.integrations.execution import checkpoints, recovery
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.approvals import approved
from chatballs.integrations.execution.events import journal
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run, validate_arguments
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.service_connections.binding import build_context
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.integrations.service_connections.oauth import fresh_credentials
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


def _prepare(tenant, token, registry):
    with tenant_atomic(tenant):
        run, step, valid = checkpoints.locked(tenant, token)
        if not valid:
            return None
        resolved = resolve_action(tenant.organization_id, step.integration_id, f"service:{step.operation_key}",
            registry=registry, expected=(step.adapter_key, step.adapter_version), recovering=token.recovering)
        integration, row, adapter, method, operation = resolved
        if operation.retry != step.retry_strategy:
            raise ExecutionDenied("version_incompatible")
        actor = TenantContext.for_membership(run.initiator) if run.initiator_id else tenant
        # Reconciliation reads the outcome of an already sent request. It does
        # not require the revoked actor to be allowed to create a new effect.
        handler = recovery.recovery_handler(step, operation) if token.recovering else "execute"
        data = step.definition
        if token.recovering and data.get("continuation") and operation.handlers.resume:
            handler = "resume"
        if handler not in {None, "reconcile"}:
            try:
                actor, _conversation = authorize_run(actor, run)
            except ExecutionDenied:
                if token.recovering and operation.handlers.reconcile:
                    handler = "reconcile"
                else:
                    raise
            if run.cancel_requested_at:
                handler = "reconcile" if operation.handlers.reconcile else None
            elif handler != "reconcile" and not approved(step, run) and (operation.effect not in READ_EFFECTS
                    or run.definition["document"]["access"]["confirm"] == "always"):
                raise ExecutionDenied("approval_expired")
        if handler is None:
            checkpoints.finish(run, step, "unknown", code="outcome_unavailable")
            return None
        arguments = data["arguments"] if handler == "execute" else {
            **data.get("continuation", {}), "effect_key": str(step.effect_key),
            "external_reference": data.get("external_reference", ""),
        }
        if handler == "execute" and validate_value(operation.input, arguments):
            raise ExecutionDenied("arguments")
        return run, step, actor, resolved, handler, arguments


def _send_marker(tenant, token, handler, registry=None):
    with tenant_atomic(tenant):
        run, step, valid = checkpoints.locked(tenant, token)
        if not valid:
            return False
        if handler != "reconcile":
            actor = TenantContext.for_membership(run.initiator) if run.initiator_id else tenant
            actor, _conversation = authorize_run(actor, run)
            if run.cancel_requested_at:
                checkpoints.finish(run, step, "unknown" if step.sent_at else "cancelled")
                return False
            integration, _row, _adapter, _method, operation = resolve_action(
                tenant.organization_id, step.integration_id, f"service:{step.operation_key}",
                expected=(step.adapter_key, step.adapter_version), registry=registry)
            if (operation.effect not in READ_EFFECTS or run.definition["document"]["access"]["confirm"] == "always") and not approved(step, run):
                raise ExecutionDenied("approval_expired")
            validate_arguments(actor, run.conversation_id, operation, step.definition["arguments"])
        step.sent_at = step.sent_at or timezone.now()
        step.save(update_fields=["sent_at"])
        journal(run, "reconcile_sent" if handler == "reconcile" else "request_sent", step)
        return True


def _commit(tenant, token, result):
    with tenant_atomic(tenant):
        run, step, valid = checkpoints.locked(tenant, token)
        if not valid:
            return False
        state = recovery.outcome(step, result)
        # No unbounded remote text is copied into the safe journal.
        code = result.error_code if result.error_code in recovery.TRANSIENT else "operation_rejected"
        values = step.definition
        if state == "completed":
            values.update(result=result.data, files=[f.file_id for f in result.files])
        if result.continuation or result.external_reference:
            values.update(continuation=result.continuation, external_reference=result.external_reference)
        step.definition = values
        delay = recovery.backoff(step.attempt, result.retry_after_seconds)
        if result.error_code == "rate_limited":
            from datetime import timedelta
            ConnectionExecutionLane.objects.filter(integration_id=step.integration_id).update(
                cooldown_until=timezone.now() + timedelta(seconds=delay))
        if state in {"retry", "pending"}:
            checkpoints.defer(tenant, run, step, delay=delay,
                              state="pending" if state == "pending" else "queued", code=code)
        else:
            checkpoints.finish(run, step, state, code=code if state != "completed" else "")
        return True


def run_one(tenant, public_id, *, registry=None, token=None):
    # A default outbox transaction or caller transaction would defeat the
    # external I/O boundary, even if the inner tenant_atomic block exits.
    if connection.in_atomic_block:
        raise RuntimeError("Execution must start outside a transaction")
    token = token or checkpoints.claim(tenant, public_id)
    if token is None:
        return
    try:
        prepared = _prepare(tenant, token, registry)
        if prepared is None:
            return
        run, step, actor, resolved, handler, arguments = prepared
        integration, row, adapter, method, operation = resolved
        credentials = fresh_credentials(tenant=tenant, integration=integration, row=row, method=method)
        context = build_context(tenant=tenant, integration=integration, method=method, settings=row.settings,
            credentials=credentials, registry=registry, effect_key=str(step.effect_key), transport_ref=adapter.transport)
        context = replace(context, run_id=str(run.public_id), step_path=step.path,
                          deadline_seconds=min(operation.limits.timeout_seconds, 30),
                          store_file=file_store(context=tenant, integration=integration, step=step))
        operation = replace(operation, limits=replace(operation.limits, timeout_seconds=min(operation.limits.timeout_seconds, 30)))
        if not _send_marker(tenant, token, handler, registry):
            return
        try:
            result = getattr(operation.handlers, handler)(context, operation, arguments)
            if result.state == ResultState.FAILED and result.error_code in recovery.TRANSIENT and operation.effect not in READ_EFFECTS:
                result = replace(result, state=ResultState.UNKNOWN)
            if result.state == ResultState.COMPLETED and validate_value(operation.output, result.data):
                result = OperationResult(ResultState.UNKNOWN, error_code="invalid_result")
        except Exception:
            # An arbitrary adapter exception may occur after send. Do not log
            # its message, arguments, credentials or remote response.
            result = OperationResult(ResultState.UNKNOWN, error_code="no_response")
        _commit(tenant, token, result)
    except (ExecutionDenied, ServiceCheckFailed) as error:
        with tenant_atomic(tenant):
            run, step, valid = checkpoints.locked(tenant, token)
            if valid:
                code = str(error) if isinstance(error, ExecutionDenied) else error.code
                checkpoints.finish(run, step, "unknown" if step.sent_at else "failed", code=code)
