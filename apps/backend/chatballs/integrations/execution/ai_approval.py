"""One employee leases an exact request; edits never alter its scenario."""

import secrets
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.integrations.execution.ai_policy import approver
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.permissions import ExecutionDenied


def active_editor(step):
    editor = step.definition.get("editor", {})
    until = parse_datetime(editor["until"]) if editor else None
    return editor if until and until > timezone.now() else {}


def confirm(tenant, run, step, digest):
    editor = active_editor(step)
    if editor and editor["membership"] != tenant.membership_id:
        raise ExecutionDenied("state_changed")
    if step.state != "approval" or digest != invocation_digest(step, run):
        raise ExecutionDenied("approval_changed")
    tenant = approver(tenant, run)
    step.confirmed_digest = digest
    step.approval_expires_at = parse_datetime(run.definition["ai"]["approvalDeadline"])
    data = step.definition
    data.pop("editor", None)
    step.definition = {**data, "approvedBy": tenant.membership_id}
    step.state = "queued"
    step.save(update_fields=["confirmed_digest", "approval_expires_at", "state", "content"])


def edit(tenant, run, step, *, digest, arguments=None, token=None, release=False):
    approver(tenant, run)
    if step.state != "approval" or digest != invocation_digest(step, run):
        raise ExecutionDenied("approval_changed")
    editor = active_editor(step)
    if editor and editor["membership"] != tenant.membership_id:
        raise ExecutionDenied("state_changed")
    data = step.definition
    if release:
        if not editor or not secrets.compare_digest(editor["token"], token or ""):
            raise ExecutionDenied("state_changed")
        data.pop("editor", None)
        step.definition = data
        step.save(update_fields=["content"])
        return
    if arguments is None:
        data["editor"] = {"membership": tenant.membership_id, "token": secrets.token_urlsafe(24),
            "until": min(timezone.now() + timedelta(minutes=5), parse_datetime(run.definition["ai"]["approvalDeadline"])).isoformat()}
        step.definition = data
        step.save(update_fields=["content"])
        return
    if not editor or not secrets.compare_digest(editor["token"], token or "") or not isinstance(arguments, dict):
        raise ExecutionDenied("state_changed")
    from chatballs.integrations.execution.actions import resolve_action, step_target
    from chatballs.integrations.execution.permissions import validate_arguments
    target = step_target(step)
    _, _, _, _, operation = resolve_action(run.organization_id, target["connection"], target["target"],
                                           expected=(step.adapter_key, step.adapter_version))
    validate_arguments(tenant, run.conversation_id, operation, arguments)
    from chatballs.integrations.execution.files import lock_input_files, own_input_files
    own_input_files(step, lock_input_files(tenant, operation, arguments))
    data["arguments"] = arguments
    data.pop("approvedBy", None)
    step.definition = data
    step.confirmed_digest = ""
    step.approval_expires_at = None
    step.save(update_fields=["content", "confirmed_digest", "approval_expires_at"])
    confirm(tenant, run, step, invocation_digest(step, run))
