"""История диалога грузится окнами, а не целиком.

Карточка диалога не несёт сообщений вовсе; лента живёт своим endpoint'ом с
курсором в обе стороны: `before` — прокрутка вверх, `after` — то, что пришло
после последнего показанного сообщения.
"""

from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    Contact,
    ControlMode,
    Conversation,
    LifecycleState,
    Message,
    MessageAuthor,
)
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.testing import TenantAPIClient as APIClient

MESSAGE_WINDOW = 50


class ConversationHistoryWindowTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        self.connection = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="bot",
            channel=self.channel,
        )
        contact = Contact.objects.create(organization=self.organization, name="Иван")
        self.conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.connection,
            contact=contact,
        )
        self.messages = [
            Message.objects.create(
                conversation=self.conversation,
                author_type=MessageAuthor.CONTACT,
                text=f"Реплика {index}",
            )
            for index in range(120)
        ]
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _history(self, query: str = "") -> dict:
        response = self.client.get(
            f"/api/v1/conversations/{self.conversation.id}/messages/{query}"
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_detail_carries_no_messages(self) -> None:
        response = self.client.get(f"/api/v1/conversations/{self.conversation.id}/")
        self.assertEqual(response.status_code, 200)
        conversation = response.json()["conversation"]
        self.assertNotIn("messages", conversation)
        # Карточка контакта и цепочка прошлых обращений остаются на месте.
        self.assertIn("history", conversation)

    def test_open_returns_last_window_in_chronological_order(self) -> None:
        page = self._history()
        self.assertEqual(len(page["items"]), MESSAGE_WINDOW)
        self.assertTrue(page["hasMore"])
        ids = [item["id"] for item in page["items"]]
        self.assertEqual(ids, sorted(ids))
        # Хвост переписки: последние 50 из 120.
        self.assertEqual(ids, [m.id for m in self.messages[-MESSAGE_WINDOW:]])
        # Курсор указывает на самое раннее сообщение окна — с него прокрутка вверх.
        self.assertEqual(page["cursor"], ids[0])

    def test_scrolling_up_walks_whole_history_without_gaps(self) -> None:
        collected: list[int] = []
        page = self._history()
        collected = [item["id"] for item in page["items"]]
        while page["hasMore"]:
            page = self._history(f"?before={page['cursor']}")
            older = [item["id"] for item in page["items"]]
            self.assertEqual(older, sorted(older))
            collected = older + collected
        # Ни пропусков, ни дублей: собрали ровно всю переписку.
        self.assertEqual(collected, [m.id for m in self.messages])
        self.assertIsNone(page["cursor"])

    def test_delta_returns_only_newer_messages(self) -> None:
        last = self.messages[-1]
        page = self._history(f"?after={last.id}")
        self.assertEqual(page["items"], [])
        self.assertFalse(page["hasMore"])
        fresh = Message.objects.create(
            conversation=self.conversation,
            author_type=MessageAuthor.OPERATOR,
            text="Ответ оператора",
        )
        page = self._history(f"?after={last.id}")
        self.assertEqual([item["id"] for item in page["items"]], [fresh.id])

    def test_limit_is_honoured_and_capped(self) -> None:
        self.assertEqual(len(self._history("?limit=10")["items"]), 10)
        # Потолок окна не даёт запросить историю целиком через ?limit=100000.
        self.assertEqual(len(self._history("?limit=100000")["items"]), 120)

    def test_broken_cursor_falls_back_to_tail(self) -> None:
        # Сообщение, на которое указывал курсор, могло быть удалено — лента не
        # должна схлопываться в пустоту.
        page = self._history("?before=99999999")
        self.assertEqual(len(page["items"]), MESSAGE_WINDOW)

    def test_invalid_cursor_is_rejected(self) -> None:
        response = self.client.get(
            f"/api/v1/conversations/{self.conversation.id}/messages/?before=abc"
        )
        self.assertEqual(response.status_code, 400)


class ConversationListWindowTests(TestCase):
    """Инбокс — тоже окно: список диалогов не отдаётся целиком."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        self.connection = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="bot",
            channel=self.channel,
        )
        self.conversations = [self._conversation(f"Клиент {index}") for index in range(45)]
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _conversation(self, name: str) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name=name)
        conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.connection,
            contact=contact,
        )
        Message.objects.create(
            conversation=conversation, author_type=MessageAuthor.CONTACT, text=name
        )
        return conversation

    def _page(self, query: str = "") -> dict:
        response = self.client.get(f"/api/v1/conversations/{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_first_window_is_bounded(self) -> None:
        page = self._page()
        self.assertEqual(len(page["items"]), 30)
        self.assertTrue(page["hasMore"])

    def test_cursor_walks_list_without_gaps(self) -> None:
        seen: list[int] = []
        page = self._page()
        seen += [item["id"] for item in page["items"]]
        while page["hasMore"]:
            page = self._page(f"?cursor={page['cursor']}")
            seen += [item["id"] for item in page["items"]]
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {c.id for c in self.conversations})

    def test_waiting_sort_puts_longest_waiting_first(self) -> None:
        for conversation in self.conversations[:3]:
            conversation.lifecycle = LifecycleState.OPEN
            conversation.control_mode = ControlMode.PAUSED
            conversation.save(update_fields=["lifecycle", "control_mode"])
        page = self._page("?sort=waiting")
        head = [item["id"] for item in page["items"][:3]]
        # Ждут дольше всех — созданы раньше остальных, значит идут первыми.
        self.assertEqual(head, [c.id for c in self.conversations[:3]])

    def test_waiting_sort_cursor_walks_list_without_gaps(self) -> None:
        for conversation in self.conversations[:5]:
            conversation.lifecycle = LifecycleState.OPEN
            conversation.control_mode = ControlMode.PAUSED
            conversation.save(update_fields=["lifecycle", "control_mode"])
        seen: list[int] = []
        page = self._page("?sort=waiting")
        seen += [item["id"] for item in page["items"]]
        while page["hasMore"]:
            page = self._page(f"?sort=waiting&cursor={page['cursor']}")
            seen += [item["id"] for item in page["items"]]
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {c.id for c in self.conversations})
