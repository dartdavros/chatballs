"""Число запросов на страницу не зависит от размера набора.

Это и есть защита от возврата исходной беды: список или лента, которые
разрастаются вместе с базой, начинаются с одного лишнего запроса на строку.
Числа здесь не зафиксированы намеренно — сравниваются два прогона на разном
объёме данных, поэтому тест не ломается от посторонних изменений и ловит ровно
N+1.
"""

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    Contact,
    Conversation,
    LifecycleState,
    Message,
    MessageAuthor,
)
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.testing import TenantAPIClient as APIClient


class QueryBudgetTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        self.connection_row = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="bot",
            channel=self.channel,
        )
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _conversation(self, name: str, messages: int = 1) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name=name)
        conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.connection_row,
            contact=contact,
            lifecycle=LifecycleState.OPEN,
        )
        for index in range(messages):
            Message.objects.create(
                conversation=conversation,
                author_type=MessageAuthor.CONTACT,
                text=f"{name} — реплика {index}",
            )
        return conversation

    def _employee(self, index: int) -> None:
        user = HumanUser.objects.create_user(
            email=f"member{index:03d}@example.com",
            password="Password-123",
            full_name=f"Сотрудник {index:03d}",
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор",
        )

    def _queries(self, url: str) -> int:
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        return len(captured)

    def _assert_flat(self, url: str, grow) -> None:
        """Сколько бы строк ни добавилось, запросов должно остаться столько же."""
        # Первый запрос после входа тянет за собой сессию и контекст аренды —
        # прогреваем, иначе сравнивались бы разные вещи.
        self._queries(url)
        before = self._queries(url)
        grow()
        after = self._queries(url)
        self.assertEqual(after, before, f"{url}: запросов стало {after} вместо {before}")

    def test_inbox_window_does_not_grow_with_dialogs(self) -> None:
        for index in range(3):
            self._conversation(f"Клиент {index:02d}")
        self._assert_flat(
            "/api/v1/conversations/?limit=30",
            lambda: [self._conversation(f"Ещё клиент {index:02d}") for index in range(12)],
        )

    def test_history_window_does_not_grow_with_messages(self) -> None:
        conversation = self._conversation("Иван", messages=5)
        self._assert_flat(
            f"/api/v1/conversations/{conversation.id}/messages/?limit=50",
            lambda: [
                Message.objects.create(
                    conversation=conversation,
                    author_type=MessageAuthor.CONTACT,
                    text=f"Ещё реплика {index}",
                )
                for index in range(30)
            ],
        )

    def test_clients_page_does_not_grow_with_contacts(self) -> None:
        for index in range(3):
            self._conversation(f"Контакт {index:02d}")
        self._assert_flat(
            "/api/v1/conversations/clients/",
            lambda: [self._conversation(f"Новый контакт {index:02d}") for index in range(12)],
        )

    def test_employees_page_does_not_grow_with_staff(self) -> None:
        for index in range(3):
            self._employee(index)
        self._assert_flat(
            "/api/v1/employees/",
            lambda: [self._employee(index) for index in range(10, 22)],
        )
