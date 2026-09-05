import json

from django.test import TestCase
from django.utils import timezone
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    Contact,
    Conversation,
    ConversationLabel,
    ConversationPriority,
    ControlMode,
    LifecycleState,
    ReplyTemplate,
)
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)


class ChatExtrasTestCase(TestCase):
    """Дизайн-базлайн v2: приоритет, метки, заметка, архив, шаблоны, счётчики."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Chat", slug="chat-extras")
        self.operators = EmployeeGroup.objects.create(
            organization=self.organization, name="Операторы"
        )
        self.owner = self._member("owner@chat.test", EmployeeRole.OWNER)
        self.employee = self._member("employee@chat.test", EmployeeRole.EMPLOYEE)
        EmployeeGroupMember.objects.create(
            organization=self.organization, group=self.operators, employee=self.employee
        )
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        self.conversation = self._conversation("Иван")
        self.client = APIClient()
        self.client.force_authenticate(self.employee.user)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.owner.user)

    def _member(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def _conversation(self, name: str, **extra) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name=name)
        return Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            contact=contact,
            **extra,
        )

    def _post(self, client, suffix: str, body: dict):
        return client.post(
            f"/api/v1/conversations/{self.conversation.id}/{suffix}/",
            data=json.dumps(body),
            content_type="application/json",
        )


class PriorityNoteTests(ChatExtrasTestCase):
    def test_operator_sets_priority_and_note(self) -> None:
        response = self._post(self.client, "priority", {"priority": "HIGH"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation"]["priority"], "HIGH")

        response = self._post(self.client, "note", {"note": "Просила писать на почту"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["conversation"]["note"], "Просила писать на почту"
        )

    def test_unknown_priority_is_rejected(self) -> None:
        response = self._post(self.client, "priority", {"priority": "URGENT"})
        self.assertEqual(response.status_code, 400)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.priority, ConversationPriority.NONE)


class LabelTests(ChatExtrasTestCase):
    def test_operator_creates_label_and_assigns_it(self) -> None:
        created = self.client.post(
            "/api/v1/conversations/labels/",
            data=json.dumps({"name": "доставка", "color": "#1677ff"}),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        label_id = created.json()["label"]["id"]

        # Повтор с тем же именем идемпотентен.
        repeat = self.client.post(
            "/api/v1/conversations/labels/",
            data=json.dumps({"name": "Доставка"}),
            content_type="application/json",
        )
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(repeat.json()["label"]["id"], label_id)

        assigned = self._post(self.client, "labels", {"labelIds": [label_id]})
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(
            [item["name"] for item in assigned.json()["conversation"]["labels"]],
            ["доставка"],
        )

        cleared = self._post(self.client, "labels", {"labelIds": []})
        self.assertEqual(cleared.json()["conversation"]["labels"], [])

    def test_foreign_label_is_rejected(self) -> None:
        other = Organization.objects.create(name="Other", slug="chat-extras-other")
        foreign = ConversationLabel.objects.create(organization=other, name="чужая")
        response = self._post(self.client, "labels", {"labelIds": [foreign.id]})
        self.assertEqual(response.status_code, 400)

    def test_label_management_requires_admin(self) -> None:
        label = ConversationLabel.objects.create(
            organization=self.organization, name="возврат"
        )
        renamed = self.client.patch(
            f"/api/v1/conversations/labels/{label.id}/",
            data=json.dumps({"name": "обмен"}),
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 403)
        renamed = self.admin_client.patch(
            f"/api/v1/conversations/labels/{label.id}/",
            data=json.dumps({"name": "обмен"}),
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200)
        deleted = self.admin_client.delete(f"/api/v1/conversations/labels/{label.id}/")
        self.assertEqual(deleted.status_code, 204)


class ArchiveTests(ChatExtrasTestCase):
    def test_archived_dialog_is_hidden_from_lists_and_admin_restores(self) -> None:
        response = self._post(self.client, "archive", {"archived": True})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["conversation"]["archivedAt"])

        listed = self.client.get("/api/v1/conversations/")
        self.assertEqual(listed.json()["items"], [])

        # Архив видит только администратор.
        denied = self.client.get("/api/v1/conversations/?archived=1")
        self.assertEqual(denied.status_code, 403)
        archive = self.admin_client.get("/api/v1/conversations/?archived=1")
        self.assertEqual(
            [item["id"] for item in archive.json()["items"]], [self.conversation.id]
        )

        # Восстановление — только администратор.
        rejected = self._post(self.client, "archive", {"archived": False})
        self.assertEqual(rejected.status_code, 403)
        restored = self._post(self.admin_client, "archive", {"archived": False})
        self.assertEqual(restored.status_code, 200)
        self.assertIsNone(restored.json()["conversation"]["archivedAt"])

    def test_spam_is_hidden_from_default_list(self) -> None:
        self.conversation.lifecycle = LifecycleState.SPAM
        self.conversation.save(update_fields=["lifecycle"])
        listed = self.client.get("/api/v1/conversations/")
        self.assertEqual(listed.json()["items"], [])
        spam = self.client.get("/api/v1/conversations/?lifecycle=SPAM")
        self.assertEqual(len(spam.json()["items"]), 1)


class ListFilterTests(ChatExtrasTestCase):
    def test_filters_by_agent_assigned_and_waiting(self) -> None:
        other_channel = Channel.objects.create(
            organization=self.organization, code="second", name="Вторая линия"
        )
        waiting = self._conversation("Ожидающий", control_mode=ControlMode.PAUSED)
        mine = self._conversation("Мой", assigned_operator=self.employee.user)
        Conversation.objects.filter(id=mine.id).update(channel=other_channel)

        by_agent = self.client.get(f"/api/v1/conversations/?agent={other_channel.id}")
        self.assertEqual([i["id"] for i in by_agent.json()["items"]], [mine.id])

        assigned = self.client.get("/api/v1/conversations/?assigned=me")
        self.assertEqual([i["id"] for i in assigned.json()["items"]], [mine.id])

        waits = self.client.get("/api/v1/conversations/?waiting=1")
        self.assertEqual([i["id"] for i in waits.json()["items"]], [waiting.id])

    def test_search_matches_contact_name(self) -> None:
        self._conversation("Мария Соколова")
        found = self.client.get("/api/v1/conversations/?q=соколова")
        self.assertEqual(len(found.json()["items"]), 1)
        empty = self.client.get("/api/v1/conversations/?q=нет-такого")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(empty.json()["items"], [])


class CountersTests(ChatExtrasTestCase):
    def test_contact_card_edit_from_dialog(self) -> None:
        response = self.client.post(
            f"/api/v1/conversations/{self.conversation.id}/contact/",
            {"description": "Постоянный клиент", "company": "ООО «Дом текстиля»", "city": "Казань", "phone": "+7 900 000-00-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        contact = response.json()["conversation"]["contact"]
        self.assertEqual(contact["description"], "Постоянный клиент")
        self.assertEqual(contact["company"], "ООО «Дом текстиля»")
        self.assertEqual(contact["city"], "Казань")
        self.assertEqual(contact["phone"], "+7 900 000-00-01")
        empty_name = self.client.post(
            f"/api/v1/conversations/{self.conversation.id}/contact/", {"name": ""}, format="json"
        )
        self.assertEqual(empty_name.status_code, 400)

    def test_directory_lists_all_groups_and_colleagues_for_employee(self) -> None:
        support = EmployeeGroup.objects.create(
            organization=self.organization, name="Поддержка"
        )
        blocked = self._member("blocked@chat.test", EmployeeRole.EMPLOYEE)
        blocked.blocked_at = timezone.now()
        blocked.save(update_fields=["blocked_at"])

        payload = self.client.get("/api/v1/conversations/directory/").json()
        # Сотрудник видит все группы — иначе не перенести диалог (кадр G).
        self.assertEqual(
            [group["name"] for group in payload["groups"]], ["Операторы", "Поддержка"]
        )
        self.assertEqual(payload["groups"][1]["id"], support.id)
        names = {employee["id"]: employee["name"] for employee in payload["employees"]}
        self.assertIn(self.owner.user_id, names)
        self.assertIn(self.employee.user_id, names)
        self.assertNotIn(blocked.user_id, names)

    def test_counters_reflect_visibility(self) -> None:
        support = EmployeeGroup.objects.create(
            organization=self.organization, name="Поддержка"
        )
        self._conversation("Групповой", group=self.operators)
        self._conversation("Чужой", group=support)
        self._conversation("Мой", assigned_operator=self.employee.user)
        self._conversation(
            "Ожидающий", group=self.operators, control_mode=ControlMode.PAUSED
        )

        response = self.client.get("/api/v1/conversations/counters/")
        payload = response.json()
        # EMPLOYEE не видит диалог чужой группы.
        self.assertEqual(payload["all"], 4)
        self.assertEqual(payload["waiting"], 1)
        self.assertEqual(payload["mine"], 1)
        self.assertEqual(
            payload["groups"],
            [{"id": self.operators.id, "name": "Операторы", "color": "", "count": 2}],
        )
        self.assertEqual(payload["ungrouped"], 2)

        admin = self.admin_client.get("/api/v1/conversations/counters/").json()
        self.assertEqual(admin["all"], 5)
        self.assertEqual(len(admin["groups"]), 2)
        self.assertEqual(
            admin["assignees"],
            [{"id": self.employee.user_id, "name": "employee@chat.test", "count": 1, "avatarUrl": None}],
        )
        by_assignee = self.admin_client.get(
            f"/api/v1/conversations/?assigned={self.employee.user_id}"
        ).json()
        self.assertEqual(len(by_assignee["items"]), 1)
        self.assertEqual(by_assignee["items"][0]["assignedOperator"]["id"], self.employee.user_id)


class ReplyTemplateTests(ChatExtrasTestCase):
    def test_admin_manages_templates_employee_reads(self) -> None:
        created = self.admin_client.post(
            "/api/v1/conversations/templates/",
            data=json.dumps({"title": "Приветствие", "text": "Здравствуйте!"}),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        template_id = created.json()["template"]["id"]

        duplicate = self.admin_client.post(
            "/api/v1/conversations/templates/",
            data=json.dumps({"title": "приветствие", "text": "Привет"}),
            content_type="application/json",
        )
        self.assertEqual(duplicate.status_code, 409)

        forbidden = self.client.post(
            "/api/v1/conversations/templates/",
            data=json.dumps({"title": "X", "text": "Y"}),
            content_type="application/json",
        )
        self.assertEqual(forbidden.status_code, 403)

        listed = self.client.get("/api/v1/conversations/templates/")
        self.assertEqual(
            [item["title"] for item in listed.json()["items"]], ["Приветствие"]
        )

        updated = self.admin_client.patch(
            f"/api/v1/conversations/templates/{template_id}/",
            data=json.dumps({"text": "Здравствуйте! Чем помочь?"}),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        deleted = self.admin_client.delete(
            f"/api/v1/conversations/templates/{template_id}/"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(ReplyTemplate.objects.exists())


class LaunchChecklistTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="New", slug="launch-org")
        owner = HumanUser.objects.create_user(
            email="owner@launch.test", password="Password-123"
        )
        OrganizationMembership.objects.create(
            user=owner,
            organization=self.organization,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )
        self.client = APIClient()
        self.client.force_authenticate(owner)

    def test_checklist_marks_steps_by_fact(self) -> None:
        initial = self.client.get("/api/v1/company/launch-checklist/").json()
        self.assertEqual(
            initial,
            {
                "agentCreated": False,
                "connectionBound": False,
                "employeeInvited": False,
                "done": False,
            },
        )

        channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        from chatballs.integrations.models import (
            Integration,
            IntegrationKind,
            IntegrationProvider,
        )

        Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Bot",
            channel=channel,
        )
        second = HumanUser.objects.create_user(
            email="second@launch.test", password="Password-123"
        )
        OrganizationMembership.objects.create(
            user=second,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Operator",
        )

        final = self.client.get("/api/v1/company/launch-checklist/").json()
        self.assertTrue(final["done"])
