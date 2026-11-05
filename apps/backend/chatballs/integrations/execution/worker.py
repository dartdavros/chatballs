"""Bounded in-process lane keeps service I/O off the message/AI dispatcher."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import BoundedSemaphore

from django.db import close_old_connections
from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.integrations.execution.checkpoints import claim
from chatballs.integrations.execution.events import schedule
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="service-effect")
_SLOTS = BoundedSemaphore(2)


def submit_io(function, *args):
    """Share the same bounded lane with event polling; never block dispatch."""
    if not _SLOTS.acquire(blocking=False):
        return False
    def invoke():
        close_old_connections()
        try:
            function(*args)
        finally:
            close_old_connections()
            _SLOTS.release()
    try:
        _POOL.submit(invoke)
    except Exception:
        _SLOTS.release()
        raise
    return True


def _run(tenant, public_id, token):
    close_old_connections()
    try:
        run_one(tenant, public_id, token=token)
    finally:
        close_old_connections()
        _SLOTS.release()


@register("integrations.run", manages_own_transaction=True)
def dispatch_run(payload, tenant):
    if tenant is None:
        raise ValueError("Service execution requires tenant")
    public_id = payload["runId"]
    if not _SLOTS.acquire(blocking=False):
        with tenant_atomic(tenant):
            run = ScenarioRun.objects.get(public_id=public_id, organization_id=tenant.organization_id)
            schedule(tenant, run, at=timezone.now() + timedelta(seconds=3))
        return
    try:
        # Claim and its watchdog commit before asynchronous handoff / outbox
        # ACK. Every crash boundary therefore has a durable next job.
        from chatballs.integrations.execution.interpreter import advance
        advance(tenant, public_id)
        token = claim(tenant, public_id)
        if token is None:
            _SLOTS.release()
            return
        _POOL.submit(_run, tenant, public_id, token)
    except Exception:
        _SLOTS.release()
        raise
