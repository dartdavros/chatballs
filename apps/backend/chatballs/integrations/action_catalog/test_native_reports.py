"""Report action grants never widen the product's historical report scope."""

from datetime import timedelta

from django.utils import timezone

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeReportTests(CommentTransactionTestBase):
    def filters(self):
        return {"from": (self.conversation.created_at - timedelta(seconds=1)).isoformat(),
            "to": (timezone.now() + timedelta(seconds=1)).isoformat(), "timezone": "UTC"}

    def test_employee_explicit_grant_only_reads_own_report_without_feedback(self):
        user = HumanUser.objects.create_user(email="native-report@tests.local")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        context = TenantContext.for_membership(member)
        with tenant_atomic(context):
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="reports.support.get", scope="organization")
        run, result = execute_action(context, "reports.support.get", {**self.filters(), "employee": user.pk})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["employee"] for row in result["employees"]], [user.pk])
        self.assertEqual(result["qualityAnalysis"]["state"], "forbidden")
        self.assertEqual(result["customerRatings"]["details"], [])
        run, _ = execute_action(context, "reports.support.get", {**self.filters(), "employee": self.author.pk})
        self.assertEqual(run.state, "failed")

    def test_foreign_dimension_is_rejected_and_missing_history_stays_unknown(self):
        run, result = execute_action(self.context, "reports.support.get", self.filters())
        self.assertEqual(run.state, "completed")
        self.assertFalse(result["coverage"]["complete"])
        self.assertIsNone(result["totals"]["values"]["waiting"]["seconds"])
        run, _ = execute_action(self.context, "reports.support.get", {**self.filters(), "employee": self.foreign_author.pk})
        self.assertEqual(run.state, "failed")
        run, result = execute_action(self.context, "reports.overview.get", {"period": "today"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(sum(row["dialogs"] for row in result["byChannel"]), 1)
