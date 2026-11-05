"""Bounded exchange discovery; every cycle is one immutable common Run."""

from datetime import UTC, datetime, timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.adapters.synchronization import EntitySnapshot
from chatballs.integrations.execution.events import system_context
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.scenario_state.synchronization import (
    ServiceSynchronizationSettings,
    SynchronizationCheckpoint,
)
from chatballs.integrations.scenarios.synchronization_access import (
    active_pair,
    actor_for,
    binding_for,
)
from chatballs.integrations.scenarios.synchronization_launch import launch
from chatballs.tenancy.database import tenant_atomic


def schedule_exchange(tenant, pk):
    enqueue_event(DomainEvent(aggregate_type="synchronization", aggregate_id=str(pk), event_type="integrations.exchange",
        payload={"checkpointId": pk}, tenant_context=system_context(tenant)))


def remote_snapshot(binding, value):
    result = binding.snapshot(value)
    if (not isinstance(result, EntitySnapshot) or not isinstance(result.values, dict)
            or not isinstance(result.version, str) or not result.version or len(result.version) > 512
            or not isinstance(result.modified_at, datetime) or timezone.is_naive(result.modified_at)):
        raise ExecutionDenied("arguments")
    return {"values": result.values, "version": result.version, "deleted": result.deleted,
        "modifiedAt": result.modified_at.astimezone(UTC).isoformat()}


def discover(tenant):
    with tenant_atomic(tenant):
        for settings in ServiceSynchronizationSettings.objects.filter(organization_id=tenant.organization_id, delegate__isnull=False).iterator():
            for pair in settings.definition["synchronization"]:
                if not pair["enabled"]:
                    continue
                native = pair["left"] if pair["left"]["connection"] == "chatballs" else pair["right"]
                remote = pair["right"] if native is pair["left"] else pair["left"]
                if native["connection"] != "chatballs" or not str(remote["connection"]).isdecimal():
                    continue
                existing = SynchronizationCheckpoint.objects.filter(settings=settings, pair_id=pair["id"], link_id=OuterRef("pk"))
                links = EntityLink.objects.filter(organization_id=tenant.organization_id, active=True,
                    integration_id=int(remote["connection"]), internal_kind=native["entity"], external_kind=remote["entity"]).annotate(
                        configured=Exists(existing)).filter(configured=False).order_by("pk")[:50]
                for link in links:
                    row = SynchronizationCheckpoint(organization_id=tenant.organization_id, settings=settings, link=link,
                        pair_id=pair["id"], due_at=timezone.now())
                    row.definition = {}
                    row.save()


def tick(tenant):
    discover(tenant)
    with tenant_atomic(tenant):
        ids = list(SynchronizationCheckpoint.objects.filter(organization_id=tenant.organization_id,
            state="idle", due_at__lte=timezone.now(), link__active=True).order_by("due_at", "pk").values_list("pk", flat=True)[:50])
        for pk in ids:
            schedule_exchange(tenant, pk)


def lock(tenant, pk):
    return SynchronizationCheckpoint.objects.select_for_update(of=("self",)).select_related(
        "settings__delegate__user", "settings__delegate__organization", "link__integration", "run").get(pk=pk, organization_id=tenant.organization_id)


def start_cycle(tenant, row, *, registry=None, trigger_key=None):
    pair = active_pair(row.settings, row.pair_id)
    actor_for(tenant, row.settings)
    _, binding = binding_for(tenant, row.link, registry=registry)
    data = row.definition
    row.generation += 1
    data.update(pair=pair, link={name: getattr(row.link, name) for name in
        ("id", "integration_id", "internal_kind", "internal_id", "external_kind", "external_id", "revision")})
    data.pop("resolution", None)
    row.definition = data
    row.run = launch(tenant, row, binding, registry=registry, trigger_key=trigger_key)
    row.state, row.error_code = "running", ""
    row.save()


@register("integrations.exchange", manages_own_transaction=True)
def handle(payload, tenant):
    with tenant_atomic(tenant):
        row = lock(tenant, payload["checkpointId"])
        if row.state == "running" and row.run and row.run.state in {"failed", "unknown", "cancelled"}:
            row.state, row.error_code = "stopped", row.run.state
            row.save(update_fields=["state", "error_code"])
        if row.state != "idle" or not row.link.active or row.due_at > timezone.now():
            return
        try:
            with transaction.atomic():
                start_cycle(tenant, row)
        except (ExecutionDenied, ValueError, KeyError, TypeError):
            row.refresh_from_db()
            row.error_code = "operation_unavailable"
            row.due_at = timezone.now() + timedelta(minutes=5)
            row.save(update_fields=["error_code", "due_at"])
