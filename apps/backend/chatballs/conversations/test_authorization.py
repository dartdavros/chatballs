from django.test import TestCase
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)


class ConversationVisibilityTests(TestCase):
    """Видимость диалогов по группам (ADR-HUB-0043 §4): диалоги групп сотрудника
    + диалоги без группы + назначенные ему; OWNER/ADMIN видят всё."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="conversation-auth")
        self.operators = EmployeeGroup.objects.create(
            organization=self.organization, name="Операторы"
        )
        self.support = EmployeeGroup.objects.create(
            organization=self.organization, name="Поддержка"
        )
        self.owner = self._employee("owner@conversation.test", EmployeeRole.OWNER)
        self.employee = self._employee("employee@conversation.test", EmployeeRole.EMPLOYEE)
        self.outsider = self._employee("outsider@conversation.test", EmployeeRole.EMPLOYEE)
        EmployeeGroupMember.objects.create(
            organization=self.organization, group=self.operators, employee=self.employee
        )
        self.operators_conversation = self._conversation(self.operators, "operators-channel")
        self.support_conversation = self._conversation(self.support, "support-channel")
        self.shared_conversation = self._conversation(None, "shared-channel")
        self.client = APIClient()
        self.client.force_authenticate(self.employee.user)

    def _employee(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def _conversation(self, group: EmployeeGroup | None, code: str) -> Conversation:
        channel = Channel.objects.create(
            organization=self.organization,
            group=group,
            code=code,
            name=code,
        )
        contact = Contact.objects.create(organization=self.organization, name=code)
        return Conversation.objects.create(
            organization=self.organization, channel=channel, group=group, contact=contact
        )

    def test_employee_sees_own_group_and_ungrouped_dialogs(self) -> None:
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {self.operators_conversation.id, self.shared_conversation.id},
        )

        detail = self.client.get(
            f"/api/v1/conversations/{self.support_conversation.id}/"
        )
        self.assertEqual(detail.status_code, 404)
        action = self.client.post(
            f"/api/v1/conversations/{self.support_conversation.id}/claim/"
        )
        self.assertEqual(action.status_code, 404)

    def test_assignee_sees_foreign_group_dialog(self) -> None:
        self.support_conversation.assigned_operator = self.employee.user
        self.support_conversation.save(update_fields=["assigned_operator"])
        response = self.client.get("/api/v1/conversations/")
        self.assertIn(
            self.support_conversation.id,
            {item["id"] for item in response.json()["items"]},
        )
        detail = self.client.get(
            f"/api/v1/conversations/{self.support_conversation.id}/"
        )
        self.assertEqual(detail.status_code, 200)

    def test_employee_without_groups_sees_only_ungrouped(self) -> None:
        self.client.force_authenticate(self.outsider.user)
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {self.shared_conversation.id},
        )

    def test_owner_sees_everything(self) -> None:
        self.client.force_authenticate(self.owner.user)
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {
                self.operators_conversation.id,
                self.support_conversation.id,
                self.shared_conversation.id,
            },
        )

    def test_move_dialog_to_group_and_assign_responsible(self) -> None:
        self.client.force_authenticate(self.owner.user)
        moved = self.client.post(
            f"/api/v1/conversations/{self.shared_conversation.id}/group/",
            data={"groupId": self.support.id},
            format="json",
        )
        self.assertEqual(moved.status_code, 200)
        self.shared_conversation.refresh_from_db()
        self.assertEqual(self.shared_conversation.group_id, self.support.id)

        assigned = self.client.post(
            f"/api/v1/conversations/{self.shared_conversation.id}/assignee/",
            data={"userId": self.employee.user_id},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200)
        self.shared_conversation.refresh_from_db()
        self.assertEqual(
            self.shared_conversation.assigned_operator_id, self.employee.user_id
        )

        cleared = self.client.post(
            f"/api/v1/conversations/{self.shared_conversation.id}/group/",
            data={"groupId": None},
            format="json",
        )
        self.assertEqual(cleared.status_code, 200)
        self.shared_conversation.refresh_from_db()
        self.assertIsNone(self.shared_conversation.group_id)
