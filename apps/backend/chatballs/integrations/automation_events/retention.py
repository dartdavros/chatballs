"""Bounded receipt cleanup preserves active consumers and replay identity."""

from django.db.models import Exists, OuterRef, Q

from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.integrations.scenario_state.waits import ScenarioWait


def cleanup_receipts(tenant, *, now):
    consumers = ScenarioWait.objects.filter(receipt_id=OuterRef("pk"))
    rows = EventReceipt.objects.select_for_update(skip_locked=True).filter(
        organization_id=tenant.organization_id, expires_at__lte=now).annotate(
            active=Exists(consumers.filter(run__finished_at__isnull=True)), referenced=Exists(consumers),
        ).filter(active=False).filter(Q(cleared_at__isnull=True) | Q(referenced=False)).order_by("expires_at")[:50]
    for row in rows:
        if row.deliveries.filter(state="pending").exists():
            continue
        if row.referenced:
            row.content = ""
            row.cleared_at = now
            row.save(update_fields=["content", "cleared_at"])
        else:
            # Replay horizon was declared by the adapter, not inferred from 7/30.
            row.delete()
