"""Short leases and fenced commits; the caller performs I/O between them."""

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic

LEASE = timedelta(seconds=90)
TERMINAL = frozenset({"completed", "failed", "cancelled"})


@dataclass(frozen=True)
class Claim:
    run_id: int
    step_id: int
    fence: int
    recovering: bool


def claim(tenant, public_id):
    with tenant_atomic(tenant):
        run = ScenarioRun.objects.select_for_update().filter(public_id=public_id, organization_id=tenant.organization_id).first()
        if run is None or run.state in TERMINAL or run.data_cleared_at:
            return None
        now = timezone.now()
        step = run.steps.select_for_update().filter(
            state__in=("queued", "running", "pending", "reconciling"), due_at__lte=now,
        ).filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now)).order_by("due_at", "id").first()
        if step is None:
            return None
        if run.cancel_requested_at and step.sent_at is None:
            finish(run, step, "cancelled")
            return None
        Integration.objects.select_for_update().get(pk=step.integration_id)
        lane, _ = ConnectionExecutionLane.objects.get_or_create(
            organization_id=tenant.organization_id, integration_id=step.integration_id)
        wait_until = max((t for t in (lane.until, lane.cooldown_until) if t and t > now), default=None)
        if wait_until:
            defer(tenant, run, step, delay=(wait_until - now).total_seconds())
            return None
        recovering = step.sent_at is not None
        step.fence += 1
        step.attempt += 1
        step.lease_until = now + LEASE
        step.due_at = step.lease_until
        step.state = "reconciling" if recovering else "running"
        step.save(update_fields=["fence", "attempt", "lease_until", "due_at", "state"])
        lane.step = step
        lane.until = step.lease_until
        lane.save(update_fields=["step", "until"])
        run.state = step.state
        run.save(update_fields=["state"])
        journal(run, "recovering" if recovering else "claimed", step)
        schedule(tenant, run, at=step.lease_until)
        return Claim(run.pk, step.pk, step.fence, recovering)


def locked(tenant, token):
    # Consistent lock order for launch/claim/cancel/result: run then step.
    run = ScenarioRun.objects.select_for_update().get(pk=token.run_id, organization_id=tenant.organization_id)
    step = ScenarioStep.objects.select_for_update().get(pk=token.step_id, run=run)
    valid = step.fence == token.fence and step.lease_until and step.lease_until > timezone.now()
    return run, step, bool(valid)


def finish(run, step, state, *, code=""):
    step.state = state
    step.error_code = code
    step.lease_until = None
    step.save(update_fields=["state", "error_code", "lease_until", "content"])
    run.state = state
    # Unknown stops automatic execution with an honest unresolved outcome.
    # Explicit reconciliation reopens it and protects its operational data.
    if state in TERMINAL or state == "unknown":
        run.finished_at = timezone.now()
    run.save(update_fields=["state", "finished_at"])
    journal(run, state, step)
    ConnectionExecutionLane.objects.filter(step=step).update(until=None, step=None)


def defer(tenant, run, step, *, delay, state="queued", code=""):
    step.state = state
    step.error_code = code
    step.lease_until = None
    step.due_at = timezone.now() + timedelta(seconds=delay)
    step.save(update_fields=["state", "error_code", "lease_until", "due_at", "content"])
    run.state = state
    run.save(update_fields=["state"])
    journal(run, "retry_scheduled", step)
    ConnectionExecutionLane.objects.filter(step=step).update(until=None, step=None)
    schedule(tenant, run, at=step.due_at)
