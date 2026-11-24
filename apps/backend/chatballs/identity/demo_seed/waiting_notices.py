"""Claim reminders derived by the queue worker from a registered demo dialog."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from chatballs.conversations.models import Conversation
from chatballs.notifications.models import Notification, NotificationType


def register_waiting_notices(dataset):
    from chatballs.identity.demo_seed.registry import recording

    conversations = dataset.records.filter(
        content_type=ContentType.objects.get_for_model(Conversation),
    ).values("object_id")
    notices = Notification.objects.filter(
        organization_id=dataset.organization_id,
        type=NotificationType.DIALOG_WAITING_LONG,
        source_type="Conversation",
        source_id__in=conversations,
        target_id=F("source_id"),
        dedup_key__startswith="waiting:",
    )
    with recording(dataset) as recorder:
        for notice in notices:
            recorder.record_existing(notice)
