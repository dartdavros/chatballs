"""Personal audience and preferences remain enforced through the runner."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.notifications.models import (
    MessengerBinding,
    NotificationPreference,
    NotificationRead,
)
from chatballs.notifications.services import notify
from chatballs.notifications.tests import _notifier
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeNotificationTests(CommentTransactionTestBase):
    def setUp(self):
        super().setUp()
        self.employee = HumanUser.objects.create_user(email="notifications@native.test")
        self.member = OrganizationMembership.objects.create(organization=self.organization,
            user=self.employee, role="EMPLOYEE")
        self.tenant = TenantContext.for_membership(self.member)

    def execute(self, key, arguments):
        with tenant_atomic(self.tenant):
            ActionGrant.objects.get_or_create(organization=self.organization, membership=self.member,
                native_key=key, operation_key="", defaults={"scope": "organization"})
        return execute_action(self.tenant, key, arguments)

    def test_read_and_mark_cannot_reach_another_persons_notification(self):
        with tenant_atomic(self.context):
            mine = notify(context=self.context, type="NEW_DIALOG", audience="USER",
                recipient_user=self.employee, title="Personal")
            other = notify(context=self.context, type="NEW_DIALOG", audience="USER",
                recipient_user=self.author, title="Private management")
        run, output = self.execute("notifications.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual([item["id"] for item in output["items"]], [mine.pk])
        run, output = self.execute("notifications.read.post", {"ids": [mine.pk, other.pk]})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["unreadCount"], 0)
        with tenant_atomic(self.tenant):
            self.assertEqual(list(NotificationRead.objects.filter(user=self.employee)
                .values_list("notification_id", flat=True)), [mine.pk])

    def test_preference_updates_only_the_actor_and_filters_unknown_types(self):
        with tenant_atomic(self.context):
            original = NotificationPreference.objects.create(organization=self.organization,
                user=self.author, transport="BROWSER", enabled=False, types=["NEW_DIALOG"])
        run, output = self.execute("notifications.preference.patch",
            {"transport": "BROWSER", "enabled": True, "types": ["NEW_DIALOG", "invented"]})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["enabled"])
        self.assertEqual(output["types"], ["NEW_DIALOG"])
        with tenant_atomic(self.context):
            original.refresh_from_db()
            self.assertFalse(original.enabled)
            self.assertTrue(NotificationPreference.objects.get(user=self.employee,
                organization=self.organization, transport="BROWSER").enabled)

    def test_binding_action_cannot_change_another_employees_binding(self):
        with tenant_atomic(self.context):
            integration = _notifier(self.organization)
            binding = MessengerBinding.objects.create(user=self.author, integration=integration,
                external_chat_id="private")
        run, _ = self.execute("notifications.binding.patch",
            {"integration_id": integration.pk, "pushTypes": ["NEW_DIALOG"]})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertTrue(MessengerBinding.objects.filter(pk=binding.pk, user=self.author).exists())
            self.assertFalse(NotificationPreference.objects.filter(user=self.employee,
                organization=self.organization, transport="MESSENGER").exists())
