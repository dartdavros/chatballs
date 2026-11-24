"""Reports against real Django/PostgreSQL services in the isolated test DB."""

import csv
from datetime import timedelta
from io import BytesIO, StringIO
from uuid import uuid4

from django.db import connection, transaction
from django.utils import timezone
from openpyxl import load_workbook

from chatballs.conversations.domain_events import record_fact
from chatballs.conversations.models import (
    Conversation,
    ConversationComment,
    ConversationParticipant,
    Message,
)
from chatballs.conversations.services import (
    assign_operator,
    claim_conversation,
    close_conversation,
    release_to_ai,
)
from chatballs.conversations.support_export import export_csv, export_xlsx, safe_csv_value
from chatballs.conversations.support_export_rows import report_tables
from chatballs.conversations.support_filters import ReportFilters
from chatballs.conversations.support_report import calculate_support_report
from chatballs.conversations.support_report_test_base import SupportReportTestBase
from chatballs.identity.group_models import EmployeeGroupMember
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.integrations.models import Integration
from chatballs.testing import TenantAPIClient


class SupportReportTests(SupportReportTestBase):
    def setUp(self):
        self.start = self.conversation.created_at
        self.end = timezone.now() + timedelta(hours=1)
        self.filters = ReportFilters(self.start, self.end, "Europe/Moscow")
        self.url = f"/api/v1/organizations/{self.organization.public_id}/conversations/support-report/"
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.user)
        self.params = self.filters.payload()
        self.params = {key: value for key, value in self.params.items() if value is not None}

    def report(self, **changes):
        return calculate_support_report(context=self.context, filters=ReportFilters(
            self.start, self.end, "Europe/Moscow", **changes,
        ))

    def test_real_facts_current_assignment_comments_and_foreign_dimensions(self):
        record_fact(self.conversation, "QUEUE_ENTERED")
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        # A system entry and an ordinary internal note cannot become replies.
        Message.objects.create(conversation=self.conversation, author_type="SYSTEM")
        ConversationComment.objects.create(organization=self.organization, conversation=self.conversation,
                                           author=self.user, audience="INTERNAL", text="Internal", operation_id=uuid4())
        colleague_user = HumanUser.objects.create(email="participant@reports.test")
        colleague = OrganizationMembership.objects.create(organization=self.organization, user=colleague_user, role="EMPLOYEE")
        ConversationParticipant.objects.create(organization=self.organization, conversation=self.conversation,
                                               membership=colleague, joined_by=self.member, join_reason="Help")
        report = self.report()
        self.assertTrue(report["coverage"]["complete"])
        self.assertEqual(report["totals"]["values"]["accepted"], 1)
        self.assertEqual(report["totals"]["values"]["humanReplies"], 0)
        self.assertEqual(report["currentLoad"], 1)
        self.assertEqual(report["employees"][0]["currentLoad"], 1)
        self.assertEqual(report["employees"][1]["currentLoad"], 0)
        self.assertNotIn(self.foreign_user.pk, [row["employee"] for row in report["employees"]])
        for key, value in (("employee", self.foreign_user.pk), ("connection", self.foreign_connection.pk),
                           ("group", self.foreign_group.pk)):
            response = self.client.get(self.url, {**self.params, key: value})
            self.assertEqual(response.status_code, 404, response.data)

    def test_legacy_history_shows_observed_values_and_physical_deletion_excludes_facts(self):
        Conversation.objects.filter(pk=self.conversation.pk).update(created_at=self.start - timedelta(days=365))
        record_fact(self.conversation, "ACCEPTED", actor_kind="HUMAN", responsible_id=self.user.pk)
        report = self.report()
        self.assertFalse(report["coverage"]["complete"])
        self.assertEqual(report["totals"]["values"]["accepted"], 1)
        self.assertEqual(report["totals"]["observedCounts"]["accepted"], 1)
        self.assertGreater(report["totals"]["values"]["handling"]["seconds"], 0)
        self.assertFalse(report["totals"]["completeByMetric"]["handling"])
        self.assertTrue(report["totals"]["completeByMetric"]["accepted"])
        self.conversation.delete()
        report = self.report()
        self.assertEqual(report["totals"]["observedCounts"]["accepted"], 0)
        self.assertEqual(report["currentLoad"], 0)

    def test_historical_filters_survive_current_dimension_change(self):
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        close_conversation(context=self.context, conversation_id=self.conversation.pk)
        Conversation.objects.filter(pk=self.conversation.pk).update(group=None, connection=None)
        report = self.report(group=self.group.pk, connection=self.connection.pk, transport="WEB")
        self.assertEqual(report["totals"]["values"]["accepted"], 1)
        self.assertEqual(report["totals"]["values"]["completed"], 1)
        self.assertEqual(report["currentLoad"], 0)
        self.assertTrue(all(row["group"] == self.group.pk for row in report["details"]))

    def test_supervisor_team_is_current_controlled_members_and_revocation_is_immediate(self):
        supervisor_user = HumanUser.objects.create(email="supervisor@reports.test")
        supervisor = OrganizationMembership.objects.create(organization=self.organization, user=supervisor_user,
                                                           role="SUPERVISOR")
        link = EmployeeGroupSupervision.objects.create(organization=self.organization, employee=supervisor, group=self.group)
        EmployeeGroupMember.objects.create(organization=self.organization, employee=self.member, group=self.group)
        self.client.force_authenticate(supervisor_user)
        response = self.client.get(self.url, self.params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["employee"] for row in response.data["employees"]], [self.user.pk])
        self.assertEqual(response.data["currentLoad"], 1)
        link.delete()
        for suffix in ("/", ".csv", ".xlsx"):
            url = self.url.rstrip("/") + suffix
            response = self.client.get(url, {**self.params, "group": self.group.pk})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(self.url, self.params).data["currentLoad"], 0)

    def test_shared_exports_match_api_and_all_xlsx_strings_are_nonformula(self):
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        close_conversation(context=self.context, conversation_id=self.conversation.pk)
        HumanUser.objects.filter(pk=self.user.pk).update(full_name=" =HYPERLINK(\"https://invalid.test\")")
        report = self.client.get(self.url, self.params).json()
        tables = report_tables(report)
        workbook = load_workbook(BytesIO(export_xlsx(report)), data_only=False)
        for sheet, (_, rows) in zip(workbook, tables, strict=True):
            actual = list(sheet.values)
            for expected, rendered in zip(rows, actual, strict=True):
                self.assertEqual(["Нет данных" if value is None else None if value == "" else value
                                  for value in expected], list(rendered))
            self.assertTrue(all(cell.data_type != "f" for row in sheet for cell in row))
        csv_rows = list(csv.reader(StringIO(export_csv(report).decode("utf-8-sig"))))
        malicious = [row[2] for row in csv_rows if len(row) > 2 and "HYPERLINK" in row[2]]
        self.assertTrue(malicious)
        self.assertTrue(all(value.startswith("'") for value in malicious))
        for suffix, content_type in ((".csv", "text/csv"), (".xlsx", "application/vnd.openxmlformats")):
            response = self.client.get(self.url.rstrip("/") + suffix, self.params)
            self.assertEqual(response.status_code, 200)
            self.assertIn(content_type, response["Content-Type"])

    def test_stale_context_block_and_employee_report_cannot_expose_team(self):
        OrganizationMembership.objects.filter(pk=self.member.pk).update(role="EMPLOYEE")
        report = self.report(employee=self.user.pk)
        self.assertEqual([row["employee"] for row in report["employees"]], [self.user.pk])
        self.assertEqual(self.client.get(self.url, self.params).status_code, 403)
        OrganizationMembership.objects.filter(pk=self.member.pk).update(blocked_at=timezone.now())
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.report(employee=self.user.pk)

    def test_assignment_without_claim_does_not_add_acceptance_or_handling(self):
        self.conversation.assigned_operator = None
        self.conversation.save(update_fields=["assigned_operator"])
        assign_operator(context=self.context, conversation_id=self.conversation.pk, assignee=self.user)
        report = self.report()
        self.assertEqual(report["totals"]["values"]["accepted"], 0)
        self.assertEqual(report["totals"]["values"]["handling"]["seconds"], 0)
        self.assertEqual(report["currentLoad"], 1)

    def test_runtime_role_reads_only_current_tenant_with_new_boundary(self):
        record_fact(self.conversation, "ACCEPTED", actor_kind="HUMAN", responsible_id=self.user.pk)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            try:
                report = self.report()
                self.assertEqual(report["totals"]["values"]["accepted"], 1)
                self.assertNotIn(self.foreign_user.pk, [row["employee"] for row in report["employees"]])
                self.assertTrue(report["coverage"]["complete"])
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE NONE")

    def test_human_return_to_ai_records_end_without_queue_and_replays_once(self):
        from chatballs.ai.models import AIAgent

        channel = self.conversation.channel
        provider = Integration.objects.create(organization=self.organization, kind="LLM_PROVIDER",
                                              provider="DEMO", name="Demo", secret="test-provider")
        self.connection.channel = channel
        self.connection.save(update_fields=["channel"])
        AIAgent.objects.create(organization=self.organization, channel=channel, provider_integration=provider,
                               name="Agent", status="ACTIVE")
        claim_conversation(context=self.context, conversation_id=self.conversation.pk)
        operation = uuid4()
        for _ in range(2):
            release_to_ai(context=self.context, conversation_id=self.conversation.pk, operation_id=operation)
        events = self.conversation.domain_events.filter(event_type="QUEUE_EXITED")
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.get().responsible_id, self.user.pk)
        report = self.report()
        self.assertEqual(report["totals"]["values"]["handling"]["currentIntervals"], 0)
        self.assertEqual(report["currentLoad"], 0)

    def test_csv_formula_prefixes_include_whitespace_and_control_characters(self):
        for value in ("=1+1", "+SUM(A1)", "-SUM(A1)", "@SUM(A1)", "\t=1", "\r=1", "\n=1", "\x00=1", "   =1", " \x00 \x00=1"):
            self.assertEqual(safe_csv_value(value), "'" + value)
        self.assertEqual(safe_csv_value(12), 12)
