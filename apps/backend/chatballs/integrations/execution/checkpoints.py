"""Short leases and fenced commits; the caller performs I/O between them."""

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
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
        from chatballs.integrations.execution.budgets import active_effects, lock_run
        try:
            run = lock_run(tenant, public_id)
        except ScenarioRun.DoesNotExist:
            return None
        if run is None or run.state in TERMINAL or run.data_cleared_at:
            return None
        if run.definition.get("composite") and active_effects(run) >= 5:
            schedule(tenant, run, at=timezone.now() + timedelta(seconds=1))
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
        lane = None
        if step.integration_id is not None:
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
        if lane is not None:
            lane.step = step
            lane.until = step.lease_until
            lane.save(update_fields=["step", "until"])
        run.state = step.state
        run.save(update_fields=["state"])
        journal(run, "recovering" if recovering else "claimed", step)
        schedule(tenant, run, at=step.lease_until)
        if run.definition.get("composite") and run.steps.filter(state="queued", due_at__lte=now).exists():
            schedule(tenant, run)
        return Claim(run.pk, step.pk, step.fence, recovering)


def locked(tenant, token):
    # Consistent lock order for launch/claim/cancel/result: run then step.
    from chatballs.integrations.execution.budgets import lock_run
    run = lock_run(tenant, pk=token.run_id)
    step = ScenarioStep.objects.select_for_update().get(pk=token.step_id, run=run)
    valid = step.fence == token.fence and step.lease_until and step.lease_until > timezone.now()
    return run, step, bool(valid)


def finish(run, step, state, *, code=""):
    from chatballs.integrations.execution.effect_data import account_effect
    account_effect(run, step, terminal=True)
    step.state = state
    step.error_code = code
    step.lease_until = None
    step.save(update_fields=["state", "error_code", "lease_until", "content"])
    if run.definition.get("composite"):
        run.progress.filter(path=step.path).update(state="queued")
        journal(run, state, step)
        ConnectionExecutionLane.objects.filter(step=step).update(until=None, step=None)
        from chatballs.tenancy.context import TenantContext
        from chatballs.tenancy.lookup import load_organization
        schedule(TenantContext.for_resource(load_organization(run.organization_id)), run)
        return
    run.state = state
    # Unknown stops automatic execution with an honest unresolved outcome.
    # Explicit reconciliation reopens it and protects its operational data.
    if state in TERMINAL or state == "unknown":
        run.finished_at = timezone.now()
    run.save(update_fields=["state", "finished_at"])
    journal(run, state, step)
    ConnectionExecutionLane.objects.filter(step=step).update(until=None, step=None)


def defer(tenant, run, step, *, delay, state="queued", code=""):
    from chatballs.integrations.execution.effect_data import account_effect
    account_effect(run, step)
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
