"""Control individual effects without granting authority over sibling paths."""

from datetime import timedelta

from django.utils import timezone

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.frames import save
from chatballs.integrations.execution.permissions import ExecutionDenied


def apply_control(tenant, run, *, action, digest, path):
    if action == "cancel":
        run.cancel_requested_at = run.cancel_requested_at or timezone.now()
        if run.state == "decision":
            run.state = "queued"
        run.save(update_fields=["cancel_requested_at", "state"])
        for step in run.steps.select_for_update().exclude(state__in=("completed", "failed", "cancelled")):
            # A decision is a completed read-only planning attempt, not an
            # uncertain external effect. It can stop without reconciliation.
            if (step.sent_at is None and step.state != "running") or step.state == "decision":
                step.state = "cancelled"
                step.save(update_fields=["state"])
        schedule(tenant, run)
    else:
        if not path:
            raise ExecutionDenied("state_changed")
        step = run.steps.select_for_update().get(path=path)
        if action == "approve":
            if step.state != "approval" or digest != invocation_digest(step, run):
                raise ExecutionDenied("approval_changed")
            step.confirmed_digest = digest
            if run.definition.get("ai"):
                from chatballs.integrations.execution.ai_approval import confirm
                confirm(tenant, run, step, digest)
            else:
                step.approval_expires_at = timezone.now() + timedelta(minutes=15)
                step.state = "queued"
                step.save(update_fields=["confirmed_digest", "approval_expires_at", "state"])
        elif action == "reconcile":
            if step.state != "unknown":
                raise ExecutionDenied("state_changed")
            step.state = "reconciling"
            step.due_at = timezone.now()
            step.save(update_fields=["state", "due_at"])
            # Ancestor frames may have propagated unknown. Reopen these only;
            # the completed siblings and their values remain untouched.
            for frame in run.progress.filter(state="unknown"):
                if path == frame.path or path.startswith(frame.path + "/"):
                    save(frame, frame.definition, "running")
        else:
            raise ExecutionDenied("action")
        run.state = "queued"
        run.finished_at = None
        run.save(update_fields=["state", "finished_at"])
        schedule(tenant, run)
    journal(run, action)
    record_audit_event(action=f"integrations.run_{action}", actor=tenant.actor_user,
        organization=tenant.organization, object_type="ScenarioRun", object_id=str(run.public_id),
        payload={"path": path or ""})
    return run
