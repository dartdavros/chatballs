"""Оповещения о диалогах: кто их получает и что в них лежит.

Канал не решает, кому что показывать: событие несёт только повод обновиться, а
данные клиент забирает REST'ом, где и живёт проверка видимости. Поэтому здесь
проверяется ровно две вещи — что событие доходит до того, кто вправе его ждать,
и что подписаться на чужой диалог нельзя.
"""

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    Contact,
    Conversation,
    LifecycleState,
    Message,
    MessageAuthor,
)
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs_backend.asgi_app import application


class ConversationEventsTests(TransactionTestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.owner = result.owner
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        contact = Contact.objects.create(organization=self.organization, name="Иван")
        self.conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            contact=contact,
            lifecycle=LifecycleState.OPEN,
        )

    def _url(self) -> str:
        return f"/ws/organizations/{self.organization.public_id}/conversations/"

    def _communicator(self, user) -> WebsocketCommunicator:
        communicator = WebsocketCommunicator(application, self._url())
        communicator.scope["user"] = user
        return communicator

    async def _connect(self, user) -> WebsocketCommunicator:
        communicator = self._communicator(user)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_stranger_is_not_connected(self) -> None:
        outsider = await self._create_outsider()
        communicator = self._communicator(outsider)
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def test_new_message_reaches_the_open_dialog(self) -> None:
        communicator = await self._connect(self.owner)
        await communicator.send_json_to(
            {"type": "watch", "conversationId": self.conversation.id}
        )
        # Подписка подтверждается: до подтверждения события диалога могли бы
        # пройти мимо.
        self.assertEqual(
            await communicator.receive_json_from(timeout=5),
            {"type": "watching", "conversationId": self.conversation.id},
        )
        await self._post_message()
        # Подписчик получает и событие диалога, и общее событие инбокса; порядок
        # между группами не определён, поэтому проверяется состав.
        events = [await communicator.receive_json_from(timeout=5) for _ in range(2)]
        changed = next(event for event in events if event["type"] == "conversation.changed")
        self.assertEqual(changed["conversationId"], self.conversation.id)
        await communicator.disconnect()

    async def test_inbox_event_carries_no_identifiers(self) -> None:
        # Сотрудник видит не все диалоги организации, поэтому в событии инбокса
        # не должно быть ни идентификаторов, ни содержимого.
        communicator = await self._connect(self.owner)
        await self._post_message()
        # Без подписки на диалог доходит только событие инбокса — и в нём нет
        # ничего, кроме самого повода обновиться.
        event = await communicator.receive_json_from(timeout=5)
        self.assertEqual(event, {"type": "inbox.changed"})
        self.assertTrue(await communicator.receive_nothing(timeout=1))
        await communicator.disconnect()

    async def test_watch_is_refused_for_a_dialog_outside_visibility(self) -> None:
        employee, hidden = await self._create_employee_and_hidden_dialog()
        communicator = await self._connect(employee)
        await communicator.send_json_to({"type": "watch", "conversationId": hidden.id})
        await self._post_message(conversation=hidden)
        # На чужой диалог подписки нет: до клиента доходит только событие
        # инбокса, без идентификатора.
        event = await communicator.receive_json_from(timeout=5)
        self.assertEqual(event, {"type": "inbox.changed"})
        self.assertTrue(await communicator.receive_nothing(timeout=1))
        await communicator.disconnect()

    async def _post_message(self, conversation: Conversation | None = None) -> None:
        from channels.db import database_sync_to_async

        target = conversation or self.conversation

        @database_sync_to_async
        def create() -> None:
            Message.objects.create(
                conversation=target, author_type=MessageAuthor.CONTACT, text="Здравствуйте"
            )

        await create()

    async def _create_outsider(self):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def create():
            other = Organization.objects.create(name="Другая", slug="other-org")
            user = HumanUser.objects.create_user(
                email="stranger@example.com", password="Password-123"
            )
            OrganizationMembership.objects.create(
                user=user, organization=other, role=EmployeeRole.OWNER, position_title="Owner"
            )
            return user

        return await create()

    async def _create_employee_and_hidden_dialog(self):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def create():
            user = HumanUser.objects.create_user(
                email="operator@example.com", password="Password-123"
            )
            OrganizationMembership.objects.create(
                user=user,
                organization=self.organization,
                role=EmployeeRole.EMPLOYEE,
                position_title="Оператор",
            )
            # Диалог чужой группы: сотрудник в неё не входит и видеть его не должен.
            group = EmployeeGroup.objects.create(
                organization=self.organization, name="Закрытая группа"
            )
            contact = Contact.objects.create(organization=self.organization, name="Пётр")
            hidden = Conversation.objects.create(
                organization=self.organization,
                channel=self.channel,
                contact=contact,
                group=group,
                lifecycle=LifecycleState.OPEN,
            )
            return user, hidden

        return await create()
