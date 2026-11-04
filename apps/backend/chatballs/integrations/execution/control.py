"""Explicit approval, cancellation and reconciliation share locking and audit."""

from datetime import timedelta

from django.utils import timezone

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution import checkpoints
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run, view_run
from chatballs.tenancy.database import tenant_atomic


def available_controls(tenant, run):
    if run.data_cleared_at:
        return []
    tenant = view_run(tenant, run)
    from chatballs.identity.models import EmployeeRole
    manages = tenant.membership_id == run.initiator_id or tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    actions = []
    if manages:
        if run.state not in checkpoints.TERMINAL and not run.cancel_requested_at:
            actions.append("cancel")
        if run.state == "unknown" and run.steps.filter(state="unknown").exists():
            actions.append("reconcile")
    try:
        if run.definition.get("ai"):
            from chatballs.integrations.execution.ai_policy import approver
            approver(tenant, run)
        else:
            authorize_run(tenant, run)
    except ExecutionDenied:
        return actions
    if run.state == "approval" and run.steps.filter(state="approval").exists():
        actions.append("approve")
        if run.definition.get("ai") and "cancel" not in actions:
            actions.append("cancel")
    if not run.definition.get("ai") and (run.state in checkpoints.TERMINAL or run.state == "unknown"):
        actions.append("repeat")
    return actions


def control(*, tenant, public_id, action, digest=None, path=None, arguments=None, edit_token=None):
    with tenant_atomic(tenant):
        from chatballs.integrations.execution.budgets import lock_run
        run = lock_run(tenant, public_id)
        if run.data_cleared_at:
            raise ExecutionDenied("data_cleared")
        tenant = view_run(tenant, run)
        if action in {"approve", "edit", "revise", "release-edit"}:
            if run.definition.get("ai"):
                from chatballs.integrations.execution.ai_policy import approver
                tenant = approver(tenant, run)
            else:
                tenant, _ = authorize_run(tenant, run)
        elif tenant.membership_id != run.initiator_id:
            from chatballs.identity.models import EmployeeRole
            if tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
                if action == "cancel" and run.definition.get("ai"):
                    from chatballs.integrations.execution.ai_policy import approver
                    approver(tenant, run)
                else:
                    raise ExecutionDenied("permission")
        if run.definition.get("composite"):
            from chatballs.integrations.execution.composite_control import apply_control
            if action not in {"edit", "revise", "release-edit"}:
                return apply_control(tenant, run, action=action, digest=digest, path=path)
        step = run.steps.select_for_update().get(path=path) if path else run.steps.select_for_update().get()
        if action in {"edit", "revise", "release-edit"}:
            if not run.definition.get("ai"):
                raise ExecutionDenied("action")
            from chatballs.integrations.execution.ai_approval import edit
            if action == "revise" and not isinstance(arguments, dict):
                raise ExecutionDenied("arguments")
            edit(tenant, run, step, digest=digest, arguments=arguments if action == "revise" else None,
                 token=edit_token, release=action == "release-edit")
            if action == "revise":
                run.state = "queued"
                run.save(update_fields=["state"])
                journal(run, "approve", step)
                record_audit_event(action="integrations.run_approve", actor=tenant.actor_user,
                    organization=tenant.organization, object_type="ScenarioRun", object_id=str(run.public_id),
                    payload={"path": step.path, "parametersChanged": True})
                schedule(tenant, run)
            return run
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
            step.save(update_fields=["confirmed_digest", "approval_expires_at", "state", "content"])
            run.state = "queued"
            run.save(update_fields=["state"])
            schedule(tenant, run)
        elif action == "cancel":
            if run.state in checkpoints.TERMINAL:
                return run
            run.cancel_requested_at = run.cancel_requested_at or timezone.now()
            run.save(update_fields=["cancel_requested_at"])
            if step.sent_at is None and step.state != "running":
                checkpoints.finish(run, step, "cancelled")
            elif step.state == "unknown":
                # Cancellation does not establish an already sent outcome.
                journal(run, "cancel_requested", step)
        elif action == "reconcile":
            if step.state != "unknown":
                raise ExecutionDenied("state_changed")
            step.state = "reconciling"
            step.due_at = timezone.now()
            step.save(update_fields=["state", "due_at"])
            run.state = "reconciling"
            run.finished_at = None
            run.save(update_fields=["state", "finished_at"])
            schedule(tenant, run)
        else:
            raise ExecutionDenied("action")
        journal(run, action, step)
        record_audit_event(action=f"integrations.run_{action}", actor=tenant.actor_user,
            organization=tenant.organization, object_type="ScenarioRun", object_id=str(run.public_id),
            payload={"path": step.path, "fence": step.fence})
        return run
