"""Collect native executor effects with explicit ownership before a reset."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from chatballs.ai.external_agents.delivery_models import (
    ExternalAgentDelivery,
    ExternalAgentDeliveryItem,
)
from chatballs.ai.external_agents.file_models import ExternalAgentFile, ExternalAgentFileGrant
from chatballs.ai.external_agents.file_uploads import reservation_key
from chatballs.ai.external_agents.notice_models import ExternalAgentNotice
from chatballs.ai.external_agents.operation_models import ExternalAgentOperation
from chatballs.ai.external_agents.receipt_models import ExternalAgentReceipt, ExternalAgentTombstone
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.session_models import ExternalAgentSession
from chatballs.ai.external_agents.template_models import ExternalAgentTemplateVersion
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.ai.skills_models import Skill
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.domain_events import operation_key
from chatballs.conversations.models import Conversation, Message
from chatballs.events.models import OutboxEvent
from chatballs.notifications.models import Notification
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.models import StorageReservation
from chatballs.tenancy.storage import adjust_storage_usage
from chatballs.tenancy.storage_quota import release_storage


def register_executor_artifacts(dataset):
    from chatballs.identity.demo_seed.registry import recording

    binding = dataset.shop_state.get("externalExecutor")
    if not binding:
        return
    tenant = dataset.organization_id
    tests = ExternalAgentTestSession.objects.filter(
        organization_id=tenant, agent_id=binding["agentId"], conversation__is_test=True,
    )
    test_ids = list(tests.values_list("conversation_id", flat=True))
    conversation_ids = [binding["conversationId"], *test_ids]
    sessions = ExternalAgentSession.objects.filter(
        organization_id=tenant, connection_id=binding["connectionId"], conversation_id__in=conversation_ids,
    )
    requests = ExternalAgentRequest.objects.filter(session__in=sessions, conversation_id__in=conversation_ids)
    deliveries = ExternalAgentDeliveryItem.objects.filter(delivery__request__in=requests)
    test_messages = Message.including_tests.filter(organization_id=tenant, conversation_id__in=test_ids)
    registered_messages = dataset.records.filter(content_type=ContentType.objects.get_for_model(Message))
    registered_ids = [int(key) for key in registered_messages.values_list("object_id", flat=True)]
    files = ExternalAgentFile.objects.filter(organization_id=tenant).filter(
        Q(session__in=sessions) | Q(owned=False, source_message__conversation_id__in=conversation_ids) & (
            Q(source_message_id__in=deliveries.values("message_id"))
            | Q(source_message_id__in=test_messages.values("pk"))
            | Q(source_message_id__in=registered_ids)
        ),
    )
    reservation_keys = [reservation_key(row) for row in files.filter(owned=True).exclude(file="")]
    notices = ExternalAgentNotice.objects.filter(organization_id=tenant, conversation_id__in=conversation_ids)
    handoffs = list(notices.values_list("operation_id", flat=True))
    replies = [operation_key("reply", message_id) for message_id in deliveries.values_list("message_id", flat=True)]
    with recording(dataset) as recorder:
        for rows in (
            Conversation.including_tests.filter(organization_id=tenant, pk__in=test_ids, is_test=True),
            tests,
            test_messages,
            Message.objects.filter(organization_id=tenant, pk__in=deliveries.values("message_id")),
            sessions,
            requests,
            ExternalAgentTombstone.objects.filter(organization_id=tenant, connection_id=binding["connectionId"]),
            ExternalAgentReceipt.objects.filter(request__in=requests),
            ExternalAgentDelivery.objects.filter(request__in=requests),
            deliveries,
            ExternalAgentOperation.objects.filter(session__in=sessions),
            StorageReservation.objects.filter(organization_id=tenant, idempotency_key__in=reservation_keys),
            files,
            ExternalAgentFileGrant.objects.filter(request__in=requests),
            notices,
            ConversationEvent.objects.filter(
                organization_id=tenant, conversation_id__in=conversation_ids, operation_id__in=[*handoffs, *replies],
                event_type__in=["QUEUE_ENTERED", "PUBLIC_REPLY"], actor_kind="AI",
            ),
            Notification.objects.filter(organization_id=tenant, dedup_key__in=[f"external-handoff:{pk}" for pk in handoffs]),
            OutboxEvent.objects.filter(organization_id=tenant, aggregate_type="ExternalAgentJob",
                                       payload__conversationId__in=conversation_ids),
        ):
            for row in rows.iterator(chunk_size=100):
                recorder.record_existing(row)


def purge_demo_template_versions(dataset):
    binding = dataset.shop_state.get("externalExecutor", {})
    template_ids = {*binding.get("templateIds", ()), *dataset.shop_state.get("historyTemplateIds", ())}
    versions = ExternalAgentTemplateVersion.objects.filter(
        organization_id=dataset.organization_id, template_id__in=template_ids, definition={},
    )
    for version in versions:
        if not Skill.objects.filter(organization_id=dataset.organization_id,
                                    templates__contains=[{"id": version.template_id}]).exists():
            version.delete()


def release_executor_upload(record):
    """Return whether the registry owns the file bytes as well as the row."""
    if not record.owned or record.released or not record.file:
        return False
    context = TenantContext.for_resource(record.organization)
    if record.complete:
        adjust_storage_usage(context=context, delta_bytes=-record.size)
    else:
        release_storage(context=context, idempotency_key=reservation_key(record))
    return True
