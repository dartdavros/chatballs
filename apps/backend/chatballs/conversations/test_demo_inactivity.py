from datetime import timedelta
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.inactivity_services import close_inactive_locked
from chatballs.conversations.maintenance import close_stale_conversations
from chatballs.conversations.models import Conversation, LifecycleState
from chatballs.conversations.services import close_conversation
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus, DemoRecord
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class DemoInactivityTests(DomainEventTestBase):
    def test_only_prepared_demo_conversations_are_protected(self):
        context = TenantContext.for_resource(self.organization)
        aged = timezone.now() - timedelta(days=30)
        with tenant_atomic(context):
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLED,
            )
            prepared = self.conversation
            ordinary = self.create_conversation()
            demo_autoclose = self.create_conversation()
            legacy = self.create_conversation()
            Conversation.objects.filter(
                pk__in=(prepared.pk, ordinary.pk, demo_autoclose.pk, legacy.pk),
            ).update(last_activity_at=aged)
            content_type = ContentType.objects.get_for_model(Conversation)
            for sequence, (conversation, protected) in enumerate(
                ((prepared, True), (demo_autoclose, False), (legacy, None)),
                start=1,
            ):
                DemoRecord.objects.create(
                    organization=self.organization, dataset=dataset, content_type=content_type,
                    object_id=str(conversation.pk), sequence=sequence,
                    protect_from_inactivity=protected,
                )
            prepared.refresh_from_db()
            self.assertFalse(close_inactive_locked(
                context=context, conversation=prepared, cutoff=timezone.now(),
            ))

        self.assertEqual(close_stale_conversations(context), 2)
        self.assertEqual(close_stale_conversations(context), 0)
        for conversation, expected in (
            (prepared, LifecycleState.OPEN),
            (legacy, LifecycleState.OPEN),
            (ordinary, LifecycleState.CLOSED),
            (demo_autoclose, LifecycleState.CLOSED),
        ):
            conversation.refresh_from_db()
            self.assertEqual(conversation.lifecycle, expected)

        close_conversation(context=self.context, conversation_id=prepared.pk)
        prepared.refresh_from_db()
        self.assertEqual(prepared.lifecycle, LifecycleState.CLOSED)

    def create_conversation(self):
        return Conversation.objects.create(
            organization=self.organization,
            channel=self.conversation.channel,
            connection=self.conversation.connection,
            contact=self.conversation.contact,
            external_chat_id=str(uuid4()),
            assigned_operator=self.user,
        )
