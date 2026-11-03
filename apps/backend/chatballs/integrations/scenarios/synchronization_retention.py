"""Disabled exchange does not retain obsolete operational field copies forever."""

from datetime import timedelta

from chatballs.integrations.scenario_state.synchronization import SynchronizationCheckpoint


def clear_inactive(tenant, *, now, days):
    cutoff = now - timedelta(days=days)
    rows = SynchronizationCheckpoint.objects.select_for_update(of=("self",), skip_locked=True).filter(
        organization_id=tenant.organization_id, settings__updated_at__lte=cutoff,
        state__in=("idle", "stopped")).select_related("settings", "run").order_by("due_at", "pk")[:50]
    for row in rows:
        if row.run and (row.run.finished_at is None or row.run.finished_at > cutoff):
            continue
        if row.settings.delegate_id and any(pair["id"] == row.pair_id and pair["enabled"] for pair in row.settings.definition["synchronization"]):
            continue
        row.definition = {}
        row.save(update_fields=["content"])
