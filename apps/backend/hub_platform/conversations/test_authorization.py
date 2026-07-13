from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.channels.models import Channel
from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeAccessAssignment,
    EmployeeProfile,
    EmployeeRole,
    HumanUser,
    Organization,
)


class ConversationAuthorizationTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="conversation-auth")
        self.sales = Department.objects.create(
            organization=self.organization, code="sales", name="Sales"
        )
        self.support = Department.objects.create(
            organization=self.organization, code="support", name="Support"
        )
        self.owner = self._employee("owner@conversation.test", EmployeeRole.OWNER)
        self.employee = self._employee(
            "employee@conversation.test", EmployeeRole.EMPLOYEE, self.sales
        )
        self.unassigned = self._employee(
            "unassigned@conversation.test", EmployeeRole.EMPLOYEE, self.support
        )
        self.sales_conversation = self._conversation(self.sales, "sales-channel")
        self.support_conversation = self._conversation(self.support, "support-channel")

        profile = AccessProfile.objects.create(
            organization=self.organization, name="Sales conversations"
        )
        for code in ("conversations.view", "conversations.operate"):
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code=code
            )
        EmployeeAccessAssignment.objects.create(
            employee=self.employee,
            access_profile=profile,
            scope_type="DEPARTMENT",
            department=self.sales,
            assigned_by=self.owner,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.employee.user)

    def _employee(
        self, email: str, role: str, department: Department | None = None
    ) -> EmployeeProfile:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return EmployeeProfile.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
            primary_department=department,
        )

    def _conversation(self, department: Department, code: str) -> Conversation:
        channel = Channel.objects.create(
            organization=self.organization,
            department=department,
            code=code,
            name=code,
        )
        contact = Contact.objects.create(organization=self.organization, name=code)
        return Conversation.objects.create(
            organization=self.organization, channel=channel, contact=contact
        )

    def test_list_and_direct_id_use_same_department_scope(self) -> None:
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["items"]],
            [self.sales_conversation.id],
        )

        detail = self.client.get(
            f"/api/v1/conversations/{self.support_conversation.id}/"
        )
        self.assertEqual(detail.status_code, 404)
        action = self.client.post(
            f"/api/v1/conversations/{self.support_conversation.id}/claim/"
        )
        self.assertEqual(action.status_code, 404)

    def test_primary_department_alone_does_not_open_list(self) -> None:
        self.client.force_authenticate(self.unassigned.user)
        response = self.client.get("/api/v1/conversations/")
        self.assertEqual(response.status_code, 403)

