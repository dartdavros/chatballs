"""Path-bound employee decisions for persistent confirmation waits."""

import hashlib
import hmac
import json

from django.utils import timezone

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution.budgets import lock_run
from chatballs.integrations.execution.events import schedule
from chatballs.integrations.execution.permissions import (
    ExecutionDenied,
    authorize_run,
    current_actor,
    view_run,
)
from chatballs.integrations.scenario_state.waits import ScenarioWait
from chatballs.tenancy.database import tenant_atomic


def decision_digest(wait):
    data = {"run": str(wait.run.public_id), "path": wait.path, "generation": str(wait.generation),
            "values": wait.definition, "deadline": wait.deadline.isoformat() if wait.deadline else None}
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def can_decide(tenant, wait):
    if wait.run.definition.get("ai"):
        from chatballs.integrations.execution.ai_policy import approver
        tenant = approver(tenant, wait.run)
        configured = wait.definition["block"].get("approver", "initiator")
        if configured != "initiator" and str(configured) != str(tenant.actor_user.pk):
            raise ExecutionDenied("permission")
        return tenant
    tenant = current_actor(tenant)
    view_run(tenant, wait.run)
    # Authority to decide never substitutes the run's effect principal.
    approver = wait.definition["block"].get("approver", "initiator")
    expected = wait.run.initiator.user_id if approver == "initiator" and wait.run.initiator_id else int(approver) if str(approver).isdecimal() else None
    if tenant.actor_user.pk != expected:
        raise ExecutionDenied("permission")
    from chatballs.tenancy.context import TenantContext
    authorize_run(TenantContext.for_membership(wait.run.initiator), wait.run)
    if wait.run.conversation_id:
        from chatballs.conversations.access import require_conversation_action
        require_conversation_action(tenant, wait.run.conversation, "conversations.operate")
    return tenant


def decide(tenant, public_id, *, path, generation, digest, accepted):
    with tenant_atomic(tenant):
        run = lock_run(tenant, public_id)
        if run.data_cleared_at:
            raise ExecutionDenied("data_cleared")
        row = ScenarioWait.objects.select_for_update().get(run=run, path=path, kind="confirmation")
        tenant = can_decide(tenant, row)
        if (row.state != "pending" or str(row.generation) != generation or row.deadline <= timezone.now()
                or not isinstance(digest, str) or not hmac.compare_digest(digest, decision_digest(row))
                or type(accepted) is not bool):
            raise ExecutionDenied("approval_changed")
        row.state = "completed" if accepted else "rejected"
        row.save(update_fields=["state"])
        run.progress.filter(path=row.path).update(state="queued")
        schedule(tenant, run)
        record_audit_event(action="integrations.wait_decision", actor=tenant.actor_user,
            organization=tenant.organization, object_type="ScenarioRun", object_id=str(run.public_id),
            payload={"path": path, "accepted": accepted, "generation": generation})
        return run
