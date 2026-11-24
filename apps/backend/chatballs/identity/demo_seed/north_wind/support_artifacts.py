"""Track staff changes made in a provisioned North Wind support dialog."""

from functools import wraps

from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.models import Conversation, Message
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.conversations.rules.models import RuleExecution
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.operation_modes import lock_organization
from chatballs.notifications.models import Notification
from chatballs.tenancy.database import tenant_atomic


def register_thread_history(dataset):
    """Collect native history written to registered demo threads since installation."""
    from chatballs.identity.demo_seed.registry import recording

    conversation_type = ContentType.objects.get_for_model(Conversation)
    registered = dataset.records.filter(content_type=conversation_type).values_list("object_id", flat=True)
    dialogs = Conversation.objects.filter(
        organization_id=dataset.organization_id, pk__in=list(map(int, registered)),
        external_chat_id__startswith=f"north-wind:{dataset.generation}:",
    ).values("pk")
    with recording(dataset) as recorder:
        for model in (Message, ConversationEvent, RuleExecution, ConversationComment, ConversationParticipant):
            content_type = ContentType.objects.get_for_model(model)
            existing = dataset.records.filter(content_type=content_type).values_list("object_id", flat=True)
            records = model._base_manager.filter(conversation_id__in=dialogs, organization_id=dataset.organization_id)
            for record in records.exclude(pk__in=list(map(int, existing))).iterator():
                recorder.record(record)
        for notice in Notification.objects.filter(
            organization_id=dataset.organization_id, source_type="Conversation", target_route="chat",
            source_id__in=list(map(str, dialogs.values_list("pk", flat=True))), target_id=F("source_id"),
        ).iterator():
            recorder.record_existing(notice)


def record_demo_support_operation(operation):
    @wraps(operation)
    def execute(*, context, conversation_id, **arguments):
        with tenant_atomic(context):
            datasets = DemoDataset.objects.filter(
                organization_id=context.organization_id,
                status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
                generation__isnull=False,
            )
            dataset = datasets.first()
            if dataset is not None and _is_demo_support_dialog(dataset, conversation_id):
                lock_organization(context.organization_id)
                dataset = datasets.select_for_update().filter(generation=dataset.generation).first()
                if dataset is not None:
                    from chatballs.identity.demo_seed.registry import runtime_recording

                    with runtime_recording(dataset):
                        return operation(context=context, conversation_id=conversation_id, **arguments)
        return operation(context=context, conversation_id=conversation_id, **arguments)
    return execute


def _is_demo_support_dialog(dataset, conversation_id):
    if not dataset.records.filter(
        content_type=ContentType.objects.get_for_model(Conversation), object_id=str(conversation_id),
    ).exists():
        return False
    return Conversation.objects.filter(
        organization_id=dataset.organization_id, pk=conversation_id,
        external_chat_id__startswith=f"north-wind:{dataset.generation}:",
    ).exists()
