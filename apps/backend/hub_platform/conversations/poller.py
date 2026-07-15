import logging

from hub_platform.conversations import transports
from hub_platform.conversations.ingest import ingest_inbound
from hub_platform.integrations.models import Integration

logger = logging.getLogger(__name__)


def poll_all_messengers(context) -> int:
    """Poll every messenger connection bound to a channel; ingest inbound. Returns count."""
    # Сервисные боты уведомлений поллятся отдельно (notifications.binding).
    # Фильтр по config — в Python: JSON-lookup в .exclude() отбрасывает и строки
    # без ключа purpose (NULL в SQL), т.е. все клиентские боты.
    integrations = [
        integration
        for integration in Integration.objects.filter(
            organization=context.organization,
            provider__in=transports.SUPPORTED_PROVIDERS,
            channel__isnull=False,
        ).exclude(secret="")
        if integration.config.get("purpose") != "notifications"
    ]
    total = 0
    for integration in integrations:
        messages, new_marker = transports.poll(integration)
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
