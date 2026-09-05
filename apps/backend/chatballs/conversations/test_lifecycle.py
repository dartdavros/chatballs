import json

from unittest import mock



from django.test import TestCase



from chatballs.channels.models import Channel

from chatballs.conversations.ingest import ingest_inbound

from chatballs.conversations.models import (

    ConnectionIdentity,

    Contact,

    ControlMode,

    Conversation,

    ExpectedResponder,

    LifecycleState,

    MessageAuthor,

)

from chatballs.conversations.transports.base import InboundMessage

from chatballs.identity.bootstrap import bootstrap_owner

from chatballs.identity.models import HumanUser, Organization

from chatballs.integrations.models import (

    Integration,

    IntegrationKind,

    IntegrationProvider,

)

from chatballs.testing import TenantAPIClient as APIClient





def _connection(channel: Channel) -> Integration:

    return Integration.objects.create(

        organization=channel.organization,

        kind=IntegrationKind.MESSENGER,

        provider=IntegrationProvider.TELEGRAM,

        name="test-bot",

        channel=channel,

    )





class OperatorOnlyIngestTests(TestCase):

    def setUp(self) -> None:

        bootstrap_owner(

            email="owner@example.com", password="temporary-password"

        )

        self.organization = Organization.objects.get(slug="demo")

        self.channel = Channel.objects.create(

            organization=self.organization,

            code="operator-only",

            name="Операторский канал",

        )

        self.integration = _connection(self.channel)



    def _ingest_without_ai(self, inbound: InboundMessage) -> tuple[mock.Mock, mock.Mock]:

        with (

            mock.patch(

                "chatballs.conversations.ingest.run_channel_turn"

            ) as ai_turn,

            mock.patch(

                "chatballs.conversations.ingest.transports.send_reply"

            ) as send,

        ):

            ingest_inbound(self.integration, inbound)

        return ai_turn, send



    def test_new_dialog_starts_in_queue_without_ai_fallback(self) -> None:

        ai_turn, send = self._ingest_without_ai(

            InboundMessage(

                external_id="operator-1",

                user_id="user-1",

                chat_id="chat-1",

                text="Нужна помощь",

                display_name="Гость",

            )

        )



        conversation = self.channel.conversations.get()

        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)

        self.assertEqual(

            conversation.expected_responder, ExpectedResponder.OPERATOR

        )

        self.assertEqual(

            list(conversation.messages.values_list("author_type", flat=True)),

            [MessageAuthor.CONTACT],

        )

        ai_turn.assert_not_called()

        send.assert_not_called()



    def test_existing_ai_dialog_moves_to_queue_when_agent_is_unavailable(self) -> None:

        contact = Contact.objects.create(

            organization=self.organization, name="Клиент"

        )

        ConnectionIdentity.objects.create(

            contact=contact,

            connection=self.integration,

            external_user_id="user-existing",

        )

        conversation = Conversation.objects.create(

            organization=self.organization,

            channel=self.channel,

            connection=self.integration,

            contact=contact,

            external_chat_id="chat-existing",

            control_mode=ControlMode.AI,

            expected_responder=ExpectedResponder.AI,

        )



        ai_turn, send = self._ingest_without_ai(

            InboundMessage(

                external_id="operator-2",

                user_id="user-existing",

                chat_id="chat-existing",

                text="Вы здесь?",

                display_name="Клиент",

            )

        )



        conversation.refresh_from_db()

        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)

        self.assertEqual(

            conversation.expected_responder, ExpectedResponder.OPERATOR

        )

        self.assertEqual(conversation.messages.count(), 1)

        ai_turn.assert_not_called()

        send.assert_not_called()





class ClosedConversationActionTests(TestCase):

    def setUp(self) -> None:

        bootstrap_owner(

            email="owner@example.com", password="temporary-password"

        )

        organization = Organization.objects.get(slug="demo")

        channel = Channel.objects.create(

            organization=organization,

            code="closed-actions",

            name="Закрытые диалоги",

        )

        integration = _connection(channel)

        contact = Contact.objects.create(organization=organization, name="Иван")

        owner = HumanUser.objects.get(email="owner@example.com")

        self.conversation = Conversation.objects.create(

            organization=organization,

            channel=channel,

            connection=integration,

            contact=contact,

            lifecycle=LifecycleState.CLOSED,

            control_mode=ControlMode.HUMAN,

            assigned_operator=owner,

            expected_responder=ExpectedResponder.NOBODY,

        )

        self.client = APIClient()

        self.client.login(

            username="owner@example.com", password="temporary-password"

        )



    def test_closed_dialog_rejects_operational_actions(self) -> None:

        base = f"/api/v1/conversations/{self.conversation.id}"

        self.assertEqual(self.client.post(f"{base}/claim/").status_code, 409)

        self.assertEqual(self.client.post(f"{base}/release/").status_code, 409)

        self.assertEqual(

            self.client.post(f"{base}/return-queue/").status_code, 409

        )

        self.assertEqual(

            self.client.post(

                f"{base}/messages/",

                data=json.dumps({"text": "Поздний ответ"}),

                content_type="application/json",

            ).status_code,

            409,

        )

        self.assertEqual(self.client.post(f"{base}/close/").status_code, 409)

        self.assertEqual(self.client.post(f"{base}/spam/").status_code, 409)



    def test_open_dialog_can_be_marked_as_spam(self) -> None:

        self.conversation.lifecycle = LifecycleState.OPEN

        self.conversation.expected_responder = ExpectedResponder.OPERATOR

        self.conversation.save(

            update_fields=["lifecycle", "expected_responder"]

        )



        response = self.client.post(

            f"/api/v1/conversations/{self.conversation.id}/spam/"

        )



        self.assertEqual(response.status_code, 200)

        payload = response.json()["conversation"]

        self.assertEqual(payload["lifecycle"], LifecycleState.SPAM)

        self.assertEqual(payload["controlMode"], ControlMode.PAUSED)

        self.assertIsNone(payload["assignedOperator"])

        self.assertEqual(

            payload["expectedResponder"], ExpectedResponder.NOBODY

        )

