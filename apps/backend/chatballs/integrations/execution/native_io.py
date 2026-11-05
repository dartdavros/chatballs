"""Native I/O never holds the runner's root/step transaction during the call."""

from time import monotonic

from django.utils import timezone

from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.automation_events.causality import origin
from chatballs.integrations.execution import checkpoints, native_results
from chatballs.integrations.execution.budgets import causal_chain
from chatballs.integrations.execution.events import journal
from chatballs.integrations.execution.native_context import context_for
from chatballs.integrations.execution.native_locale import native_locale
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.tenancy.database import tenant_atomic


def run_io(tenant, token):
    from chatballs.identity.audit_context import native_audit
    from chatballs.integrations.execution.native import _result, prepare
    from chatballs.integrations.execution.runner import _commit

    sent = False
    started = monotonic()
    try:
        with tenant_atomic(tenant):
            prepared = prepare(tenant, token)
            if prepared is None:
                return
            run, step, action, actor, scope, arguments = prepared
            context = context_for(run, step, action, actor, scope, arguments)
            chain = causal_chain(run)
            step.sent_at = timezone.now()
            step.save(update_fields=["sent_at"])
            journal(run, "request_sent", step)
        sent = True
        with origin(chain), native_audit(run, step, actor), native_locale(actor):
            result = action.execute(context, arguments)
        # A confirmed result is durable even if the worker subsequently loses
        # its lease or crashes before its fenced checkpoint can be committed.
        with tenant_atomic(tenant):
            result = _result(action, result)
            native_results.save(run, step, action, result, actor=actor)
        _commit(tenant, token, result, elapsed=monotonic() - started)
    except Exception as error:
        # No generic transport exception proves that a send had no effect.
        # Only explicit authorization/argument rejection can be definitive.
        code = str(error) if isinstance(error, ExecutionDenied | NativeAccessDenied | NativeOperationRejected) else "operation_rejected"
        definitive = not sent or isinstance(error, NativeAccessDenied | NativeOperationRejected)
        with tenant_atomic(tenant):
            run, step, valid = checkpoints.locked(tenant, token)
            if valid:
                if definitive:
                    checkpoints.finish(run, step, "failed", code=code)
                else:
                    _commit(tenant, token, OperationResult(ResultState.UNKNOWN, error_code=code),
                        elapsed=monotonic() - started)
