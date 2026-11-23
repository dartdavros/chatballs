from django.test import TestCase
from django.utils import timezone

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, ControlMode, Conversation
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.identity.employee_dismissal import dismiss_employee
from chatballs.identity.employee_queries import list_employees
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.models import AuditEvent, HumanUser, Organization, OrganizationMembership
from chatballs.tenancy.context import TenantContext
from chatballs.testing import TenantAPIClient


class EmployeeDismissalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Work", slug="dismissal")
        cls.owner = cls.member("owner@dismissal.test", "OWNER")
        cls.admin = cls.member("admin@dismissal.test", "ADMIN")
        cls.employee = cls.member("employee@dismissal.test", "EMPLOYEE")
        cls.context = TenantContext.for_membership(cls.admin)
        cls.channel = Channel.objects.create(organization=cls.organization, code="test", name="Test")
        cls.contact = Contact.objects.create(organization=cls.organization, name="Customer")

    @classmethod
    def member(cls, email, role, **values):
        user = HumanUser.objects.create_user(email=email)
        return OrganizationMembership.objects.create(
            organization=cls.organization, user=user, role=role, **values,
        )

    def dismiss(self, target=None, confirmed=True):
        return dismiss_employee(self.context, (target or self.employee).user_id, {"confirmed": confirmed})

    def test_dismissal_closes_only_organization_access_and_releases_work(self):
        other = Organization.objects.create(name="Other", slug="dismissal-other")
        other_membership = OrganizationMembership.objects.create(
            organization=other, user=self.employee.user, role="EMPLOYEE",
        )
        conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel, contact=self.contact,
            control_mode=ControlMode.HUMAN, assigned_operator=self.employee.user,
        )
        participation = ConversationParticipant.objects.create(
            organization=self.organization, conversation=conversation, membership=self.employee,
            joined_by=self.admin, join_reason="Consultation",
        )
        original_password = self.employee.user.password
        self.assertFalse(self.dismiss().problem)
        self.employee.refresh_from_db()
        conversation.refresh_from_db()
        participation.refresh_from_db()
        other_membership.refresh_from_db()
        self.employee.user.refresh_from_db()
        self.assertIsNotNone(self.employee.dismissed_at)
        self.assertTrue(self.employee.is_blocked)
        self.assertIsNone(conversation.assigned_operator_id)
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        self.assertIsNotNone(conversation.waiting_since)
        self.assertIsNotNone(participation.left_at)
        self.assertFalse(other_membership.is_blocked)
        self.assertTrue(self.employee.user.is_active)
        self.assertEqual(self.employee.user.password, original_password)
        api = TenantAPIClient()
        api.force_authenticate(self.employee.user)
        response = api.get(f"/api/v1/organizations/{self.organization.public_id}/employees/")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(can_manage_employee(self.admin, self.employee, EmployeeAction.UNBLOCK))

    def test_confirmation_and_idempotent_audit(self):
        self.assertEqual(self.dismiss(confirmed=False).problem, "invalid")
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.dismissed_at)
        self.dismiss()
        self.dismiss()
        self.assertEqual(AuditEvent.objects.filter(action="identity.employee_dismissed").count(), 1)

    def test_http_dismissal_requires_confirmation_and_returns_updated_card(self):
        client = TenantAPIClient()
        client.force_authenticate(self.admin.user)
        path = f"/api/v1/organizations/{self.organization.public_id}/employees/{self.employee.user_id}/dismiss/"
        self.assertEqual(client.post(path, {}, format="json").status_code, 400)
        response = client.post(path, {"confirmed": True}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        card = response.json()["employee"]
        self.assertIsNotNone(card["dismissedAt"])
        self.assertFalse(card["permissions"]["canDismiss"])
        self.assertFalse(card["permissions"]["canUnblock"])

    def test_owner_is_read_only_for_administrator(self):
        for action in (EmployeeAction.BLOCK, EmployeeAction.UNBLOCK, EmployeeAction.UPDATE_PROFILE,
                       EmployeeAction.CHANGE_GROUPS, EmployeeAction.RESET_PASSWORD,
                       EmployeeAction.TERMINATE_SESSIONS, EmployeeAction.DISMISS, EmployeeAction.DELETE):
            with self.subTest(action=action):
                self.assertFalse(can_manage_employee(self.admin, self.owner, action))
        self.assertEqual(self.dismiss(self.owner).problem, "forbidden")
        self.owner.refresh_from_db()
        self.assertIsNone(self.owner.blocked_at)
        self.assertIsNone(self.owner.dismissed_at)

    def test_status_and_role_filters_exclude_dismissed_before_pagination(self):
        invited = self.member("invited@dismissal.test", "SUPERVISOR")
        invited.user.must_change_password = True
        invited.user.save(update_fields=["must_change_password"])
        blocked = self.member("blocked@dismissal.test", "EMPLOYEE", blocked_at=timezone.now())
        self.dismiss()
        all_rows = list_employees(self.context, {})
        self.assertNotIn(self.employee.user_id, [row["id"] for row in all_rows["items"]])
        for status, expected in (("invited", invited), ("blocked", blocked), ("dismissed", self.employee)):
            with self.subTest(status=status):
                rows = list_employees(self.context, {"status": status, "role": expected.role, "pageSize": "1"})
                self.assertEqual(rows["total"], 1)
                self.assertEqual([row["id"] for row in rows["items"]], [expected.user_id])
        active = list_employees(self.context, {"status": "active"})
        self.assertEqual({row["id"] for row in active["items"]}, {self.owner.user_id, self.admin.user_id})
