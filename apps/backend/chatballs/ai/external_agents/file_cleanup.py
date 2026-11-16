"""Bounded orphan cleanup; active grants and conversation bytes are pinned."""

from django.db.models import Exists, OuterRef
from django.utils import timezone

from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.ai.external_agents.file_uploads import abandon
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.conversations.models import Message
from chatballs.tenancy.storage import adjust_storage_usage


def cleanup(context, *, limit=50):
    orphan_ids = list(ExternalAgentFile.objects.filter(organization_id=context.organization_id,
        owned=False, source_message__isnull=True, grants__isnull=True).values_list("pk", flat=True)[:limit])
    ExternalAgentFile.objects.filter(pk__in=orphan_ids).delete()
    records = ExternalAgentFile.objects.select_for_update().filter(
        organization_id=context.organization_id, owned=True, released=False,
        expires_at__lte=timezone.now()).annotate(
            published=Exists(Message.including_tests.filter(attachment=OuterRef("file"))),
            active=Exists(ExternalAgentRequest.objects.filter(session_id=OuterRef("session_id"), active=True)),
        ).filter(published=False, active=False).order_by("pk")[:limit]
    count = 0
    for record in records:
        if Message.including_tests.filter(attachment=record.file.name).exists():
            continue
        if record.grants.filter(request__active=True).exists():
            continue
        if record.session_id and record.session.externalagentrequest_set.filter(active=True).exists():
            continue
        if record.complete:
            record.file.delete(save=False)
            adjust_storage_usage(context=context, delta_bytes=-record.size)
            record.released = True
            record.save(update_fields=["released"])
        else:
            abandon(context, record)
        count += 1
    return count


def release_conversation(context, conversation_id):
    """The native deletion command also removes uploads not yet made into Messages."""
    records = ExternalAgentFile.objects.select_for_update().filter(
        session__conversation_id=conversation_id, organization_id=context.organization_id,
        owned=True, released=False)
    for record in records:
        if not record.complete:
            abandon(context, record)
            continue
        record.file.storage.delete(record.file.name)
        adjust_storage_usage(context=context, delta_bytes=-record.size)
        record.released = True
        record.save(update_fields=["released"])
