"""Existing organization retention policy protects active waits and dedup IDs."""

from datetime import timedelta

from django.utils import timezone

from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.file_cleanup import cleanup as cleanup_files
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.integrations.execution.retention import effective_days, policy_for


def cleanup(context, *, limit=50):
    cleanup_files(context, limit=limit)
    days, metadata_days = effective_days(policy_for(context))
    finished = ExternalAgentRequest.objects.filter(
        organization_id=context.organization_id, active=False, terminal_at__isnull=False,
        terminal_at__lte=timezone.now() - timedelta(days=days),
    ).order_by("pk")
    ids = list(finished.exclude(seed_ciphertext="").values_list("pk", flat=True)[:limit])
    ExternalAgentRequest.objects.filter(pk__in=ids).update(seed_ciphertext="", snapshot_ciphertext="", history_ciphertext="")
    ExternalAgentReceipt.objects.filter(request_id__in=ids).update(payload_ciphertext="")
    expired = list(finished.filter(terminal_at__lte=timezone.now() - timedelta(days=metadata_days))
                   .values_list("pk", flat=True)[:limit])
    # Cover messages created before durable delivery facts were introduced, too.
    for item in ExternalAgentDeliveryItem.objects.filter(delivery__request_id__in=expired).select_related("delivery__request"):
        item.retain_message_state()
    ExternalAgentRequest.objects.filter(pk__in=expired).delete()
    return len(ids)
