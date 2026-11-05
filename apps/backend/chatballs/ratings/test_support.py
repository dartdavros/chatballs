"""Shared setup for focused tests on the real PostgreSQL test database."""

from uuid import uuid4

from django.core.cache import cache

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.models import ConnectionIdentity
from chatballs.ratings.models import RatingRequest, RatingSettings
from chatballs.webchat.models import WebChatWidget, WebSession


def prepare_rating_transport(case):
    cache.clear()
    case.connection.channel = case.conversation.channel
    case.connection.status = "OK"
    case.connection.save()
    case.widget = WebChatWidget.objects.create(
        organization=case.organization, integration=case.connection,
        code="ratings", name="Ratings", status="PUBLISHED",
    )
    case.identity = ConnectionIdentity.objects.create(
        organization=case.organization, connection=case.connection,
        contact=case.conversation.contact, external_user_id="rating-client",
    )
    case.session = WebSession.objects.create(
        organization=case.organization, connection=case.connection, widget=case.widget,
        identity=case.identity, token_hash="a" * 64,
    )
    case.conversation.transport_meta = {"webChatWidgetId": case.widget.pk}
    case.conversation.save()
    case.scale = [{"value": value, "label": str(value)} for value in range(1, 6)]
    case.policy = RatingSettings.objects.create(
        organization=case.organization, enabled=True, scale=case.scale,
        text="Test customer question", delay_seconds=0,
    )


class RatingTestBase(DomainEventTestBase):
    def setUp(self):
        prepare_rating_transport(self)

    def completion(self, conversation=None):
        conversation = conversation or self.conversation
        conversation.lifecycle = "CLOSED"
        conversation.save(update_fields=["lifecycle"])
        event = self.row(
            conversation_id=conversation.pk, event_type="CLOSED", operation_id=uuid4(),
        )
        event.save()
        return event

    def scheduled(self):
        event = self.completion()
        return RatingRequest.objects.get(completion=event)
