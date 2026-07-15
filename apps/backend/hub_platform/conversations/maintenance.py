import logging
from datetime import timedelta

from django.utils import timezone

from hub_platform.conversations.models import Conversation, LifecycleState

logger = logging.getLogger(__name__)

# ADR-HUB-0002: семь дней без активности переводят OPEN в CLOSED.
AUTOCLOSE_DAYS = 7


def close_stale_conversations(context, days: int = AUTOCLOSE_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=days)
    closed = Conversation.objects.filter(
        organization=context.organization,
        lifecycle=LifecycleState.OPEN,
        last_activity_at__lte=cutoff,
    ).update(
        lifecycle=LifecycleState.CLOSED
    )
    if closed:
        logger.info("Auto-closed %s stale conversations (>%sd inactive)", closed, days)
    return closed
