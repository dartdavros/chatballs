import logging
from datetime import timedelta

from django.db.models import CharField, Exists, OuterRef
from django.db.models.functions import Cast
from django.utils import timezone

from chatballs.conversations.demo_protection import inactivity_protection_records
from chatballs.conversations.lifecycle_services import _close_stale_locked
from chatballs.conversations.models import Conversation, LifecycleState
from chatballs.tenancy.database import tenant_atomic

logger = logging.getLogger(__name__)
AUTOCLOSE_DAYS = 7


def close_stale_conversations(context, days: int = AUTOCLOSE_DAYS) -> int:
    cutoff = timezone.now() - timedelta(days=days)
    closed = 0
    with tenant_atomic(context):
        conversations = Conversation.objects.select_for_update().filter(
            organization=context.organization, lifecycle=LifecycleState.OPEN,
            last_activity_at__lte=cutoff,
        ).filter(
            ~Exists(inactivity_protection_records(
                organization_id=context.organization_id,
                object_id=Cast(OuterRef("pk"), output_field=CharField()),
            )),
        )
        for conversation in conversations:
            _close_stale_locked(context=context, conversation=conversation)
            closed += 1
    if closed:
        logger.info("Auto-closed %s stale conversations (>%sd inactive)", closed, days)
    return closed
