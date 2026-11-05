"""Journal controls and retention preserve authorization and delayed cleanup."""

from uuid import uuid4

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.run_management import without_edit_tokens
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.launch import launch_direct
from chatballs.integrations.execution.retention import effective_days, policy_for
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeRunManagementTests(CommentTransactionTestBase):
    def execute(self, key, values, *, tenant=None, state="completed"):
        run, result = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return run, result

    def test_journal_reads_and_cancel_share_the_real_runner(self):
        pending, _ = launch_direct(tenant=self.context, connection_id="chatballs", operation_key="groups.get",
            arguments={}, trigger_key=str(uuid4()))
        _, listed = self.execute("runs.get", {"page": "1"})
        self.assertTrue(any(row["id"] == str(pending.public_id) for row in listed["items"]))
        _, read = self.execute("runs.detail.get", {"public_id": str(pending.public_id)})
        self.assertEqual(read["run"]["id"], str(pending.public_id))
        self.execute("runs.control.post", {"public_id": str(pending.public_id), "action": "cancel"})
        with tenant_atomic(self.context):
            pending.refresh_from_db()
            self.assertEqual(pending.state, "cancelled")
        _, catalog = self.execute("runs.actions.get", {})
        self.assertTrue(any(row["id"] == "chatballs:groups.get" for row in catalog["items"]))

    def test_retention_needs_explicit_shortening_and_current_manager(self):
        _, policy = self.execute("runs.retention.get", {})
        self.assertEqual((policy["stepDays"], policy["journalDays"]), (7, 30))
        data = {"stepDays": 3, "journalDays": 14, "version": policy["version"]}
        self.execute("runs.retention.put", data, state="failed")
        _, updated = self.execute("runs.retention.put", {**data, "confirmed": True})
        self.assertTrue(updated["effectiveAt"])
        with tenant_atomic(self.context):
            self.assertEqual(effective_days(policy_for(self.context)), (7, 30))
            user = HumanUser.objects.create_user(email="native-journal-employee@example.test")
            membership = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=membership,
                native_key="runs.retention.get", scope="organization")
        self.execute("runs.retention.get", {}, tenant=TenantContext.for_membership(membership), state="failed")
        self.execute("runs.retention.put", {**data, "confirmed": True}, state="failed")

    def test_foreign_run_and_protocol_tokens_are_not_available_as_action_data(self):
        foreign = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        row, _ = self.execute("groups.get", {}, tenant=foreign)
        self.execute("runs.detail.get", {"public_id": str(row.public_id)}, state="failed")
        self.execute("runs.control.post", {"public_id": str(row.public_id), "action": "cancel"}, state="failed")
        payload = {"run": {"steps": [{"editToken": "lease-secret", "editing": True, "result": {"count": 2}}]}}
        self.assertEqual(without_edit_tokens(payload), {"run": {"steps": [{"editing": True, "result": {"count": 2}}]}})
        self.assertEqual(payload["run"]["steps"][0]["editToken"], "lease-secret")
