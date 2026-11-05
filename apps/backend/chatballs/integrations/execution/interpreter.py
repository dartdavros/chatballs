"""Process a bounded queue of ready checkpoints, never scan blocked frames."""

from time import monotonic

from django.db import transaction
from django.utils import timezone

from chatballs.integrations.execution import blocks
from chatballs.integrations.execution.block_actions import action
from chatballs.integrations.execution.block_values import actual, initial
from chatballs.integrations.execution.budgets import charge, lock_run
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.frames import DONE, create, save
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.scenarios.values import InvalidValues, prepare_inputs
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


def is_composite(run):
    return bool(run.content and run.definition.get("composite"))


def advance(tenant, public_id, *, registry=None):
    with tenant_atomic(tenant):
        run = lock_run(tenant, public_id)
        if run.data_cleared_at or run.finished_at or run.state == "decision":
            return
        from chatballs.integrations.execution.waits import expire_operations
        expire_operations(tenant, run)
        if not is_composite(run):
            return
        started = monotonic()
        from chatballs.integrations.execution.nested import call
        from chatballs.integrations.execution.waits import wait
        handlers = {"sequence": blocks.step_sequence, "if": blocks.branch, "try": blocks.attempt,
                    "foreach": blocks.fanout, "parallel": blocks.fanout, "action": action,
                    "call": call, "wait": wait}
        root = run.progress.filter(path="steps").first()
        if root is None:
            root = create(run, "steps", "sequence", initial(run),
                          steps=run.definition["document"]["steps"], index=0)
        due = run.waits.filter(state="pending", deadline__lte=timezone.now()).values("path")
        run.progress.filter(path__in=due).exclude(state__in=DONE).update(state="queued")
        actor = TenantContext.for_membership(run.initiator) if run.initiator_id else tenant
        try:
            authorize_run(actor, run, check_conditions=False)
            denied = "cancelled" if run.cancel_requested_at else None
        except ExecutionDenied as error:
            denied = str(error)
        if denied:
            stop_unsent(run, denied)
        for _ in range(32):
            frame = run.progress.filter(state="queued").order_by("pk").first()
            if frame is None:
                break
            frame.state = "pending"
            frame.save(update_fields=["state"])
            try:
                with transaction.atomic():
                    handlers[frame.kind](actor, run, frame, registry)
            except (ExecutionDenied, InvalidValues, KeyError, ValueError, TypeError, IndexError) as error:
                frame.refresh_from_db()
                code = str(error) if isinstance(error, ExecutionDenied) else "arguments"
                save(frame, frame.definition, "failed", code)
            if monotonic() - started >= .1:
                break
        charge(run, started)
        aggregate(tenant, actor, run, root, registry)


def stop_unsent(run, reason):
    state = "cancelled" if reason == "cancelled" else "failed"
    run.steps.filter(sent_at__isnull=True).exclude(state__in=DONE).update(state=state, error_code=reason)
    sent_paths = run.steps.filter(sent_at__isnull=False).exclude(state__in=DONE).values("path")
    run.progress.exclude(state__in=DONE).exclude(path__in=sent_paths).update(state=state, error_code=reason)
    run.waits.filter(state="pending").exclude(kind="operation").update(state="cancelled")
    from chatballs.integrations.execution.cancellation import schedule_children
    schedule_children(run)


def aggregate(tenant, actor, run, root, registry):
    root.refresh_from_db()
    if root.state in {"failed", "cancelled"}:
        stop_unsent(run, "cancelled" if root.state == "cancelled" else root.error_code or "dependency_failed")
    states = set(run.steps.values_list("state", flat=True))
    unresolved = run.steps.filter(sent_at__isnull=False).exclude(state__in=DONE)
    children_active = run.children.filter(finished_at__isnull=True).exists()
    if root.state in DONE and not unresolved.exists() and not children_active:
        run.steps.filter(sent_at__isnull=True).exclude(state__in=DONE).update(state="cancelled", error_code="dependency_failed")
        run.progress.exclude(state__in=DONE).update(state="cancelled", error_code="dependency_failed")
        run.waits.filter(state="pending").exclude(kind="operation").update(state="cancelled")
        result = root.state
        if result == "completed":
            try:
                output = prepare_inputs(read_type(run.definition["document"]["results"]),
                    run.definition["document"]["outputs"], actual(actor, run, root.definition["values"]), registry=registry)
                data = root.definition
                data["result"] = output
                save(root, data)
            except (InvalidValues, ExecutionDenied):
                root.refresh_from_db()
                save(root, root.definition, "failed", "arguments")
                result = "failed"
        run.state, run.finished_at = result, timezone.now()
        journal(run, result)
        if run.parent_id:
            run.parent.progress.filter(path=run.call_path).update(state="queued")
            schedule(tenant, run.parent)
    elif "unknown" in states or root.state == "unknown":
        run.state = "unknown"
        if run.parent_id:
            run.parent.progress.filter(path=run.call_path).update(state="queued")
            schedule(tenant, run.parent)
    elif "approval" in states or run.waits.filter(kind="confirmation", state="pending").exists():
        run.state = "approval"
    elif states & {"running", "reconciling"}:
        run.state = "running"
    elif "queued" in states or run.progress.filter(state="queued").exists():
        run.state = "queued"
    else:
        run.state = "pending"
    if not run.finished_at and ("queued" in states or run.progress.filter(state="queued").exists()):
        schedule(tenant, run)
    run.save(update_fields=["state", "finished_at"])
    if run.definition.get("kind") == "synchronization" and (run.finished_at or run.state == "unknown"):
        from chatballs.integrations.scenarios.synchronization_runtime import schedule_exchange
        schedule_exchange(tenant, run.definition["exchange"]["checkpoint"])
