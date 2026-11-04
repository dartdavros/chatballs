"""Durable approval deadlines release unsent work without inventing an outcome."""

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.execution.events import system_context


def schedule_expiry(tenant, run, step):
    binding = run.definition.get("ai", {})
    if binding.get("mode") != "ask":
        return
    enqueue_event(DomainEvent(aggregate_type="scenario_run", aggregate_id=str(run.public_id),
        event_type="integrations.ai_approval_expire", payload={"runId": str(run.public_id), "path": step.path},
        tenant_context=system_context(tenant)), available_at=parse_datetime(binding["approvalDeadline"]))


@register("integrations.ai_approval_expire")
def expire(payload, tenant):
    from chatballs.integrations.execution.budgets import lock_run
    from chatballs.integrations.execution.checkpoints import finish
    run = lock_run(tenant, payload["runId"])
    if run is None or run.data_cleared_at or not run.definition.get("ai"):
        return
    if parse_datetime(run.definition["ai"]["approvalDeadline"]) > timezone.now():
        return
    step = run.steps.select_for_update().filter(path=payload["path"]).first()
    if step and step.sent_at is None and step.state in {"approval", "queued", "running"}:
        finish(run, step, "cancelled", code="approval_expired")
