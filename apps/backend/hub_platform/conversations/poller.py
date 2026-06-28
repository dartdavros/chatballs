import logging

from hub_platform.conversations.ingest import ingest_inbound
from hub_platform.conversations.transports import max as max_transport
from hub_platform.integrations.models import Integration, IntegrationProvider

logger = logging.getLogger(__name__)


def poll_all_messengers() -> int:
    """Poll every MAX connection bound to a channel; ingest inbound. Returns count."""
    integrations = (
        Integration.objects.filter(provider=IntegrationProvider.MAX, channel__isnull=False)
        .exclude(secret="")
    )
    total = 0
    for integration in integrations:
        messages, new_marker = max_transport.poll_updates(integration)
        for inbound in messages:
            try:
                ingest_inbound(integration, inbound)
                total += 1
            except Exception:  # pragma: no cover
                logger.exception("Ingest failed for integration %s", integration.id)
        if new_marker and new_marker != integration.poll_marker:
            integration.poll_marker = new_marker
            integration.save(update_fields=["poll_marker", "updated_at"])
    return total
