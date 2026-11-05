"""Real domain files, export formats and tenant/step ownership through runner."""

import io
import json
import zipfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import connection
from django.utils import timezone

from chatballs.conversations.models import Conversation, Message, MessageKind
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.file_access import file_opener
from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.retention import cleanup, delete_operation_file
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import ServiceFile
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeFileTests(NativeFileCase):
    def test_report_exports_use_actual_formats_and_preserve_the_same_report_scope(self):
        run, data = execute_action(self.context, "reports.support_csv.get", self.filters())
        name, content_type, body = self.read_result(run, data)
        self.assertEqual((name, content_type), ("support-report.csv", "text/csv; charset=utf-8"))
        self.assertIn("\n", body.decode("utf-8-sig"))
        run, data = execute_action(self.context, "reports.support_xlsx.get", self.filters())
        name, _content_type, body = self.read_result(run, data)
        self.assertEqual(name, "support-report.xlsx")
        with zipfile.ZipFile(io.BytesIO(body)) as workbook:
            self.assertIn("xl/workbook.xml", workbook.namelist())
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="native-file-report@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="reports.support_csv.get", scope="organization")
        tenant = TenantContext.for_membership(member)
        run, _ = execute_action(tenant, "reports.support_csv.get", {**self.filters(), "employee": self.user.pk})
        self.assertEqual(run.state, "failed")
        run, data = execute_action(tenant, "reports.support_csv.get", {**self.filters(), "employee": user.pk})
        self.read_result(run, data)

    def test_domain_attachment_audio_avatar_and_redacted_diagnostic_use_original_selectors(self):
        with tenant_atomic(self.context):
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT", kind=MessageKind.FILE,
                attachment_name="receipt.pdf", attachment_content_type="application/pdf", attachment_size=8)
            message.attachment.save("receipt.pdf", ContentFile(b"%PDF-1.4"))
            voice = Message.objects.create(conversation=self.conversation, author_type="CONTACT", kind=MessageKind.VOICE,
                audio_content_type="audio/ogg")
            voice.audio.save("voice.ogg", ContentFile(b"OggS"))
            contact = self.conversation.contact
            contact.avatar_content_type = "image/png"
            contact.avatar.save("avatar.png", ContentFile(b"\x89PNG"))
        for key, arguments, expected in (
            ("messages.attachment_file.get", {"message_id": message.pk}, b"%PDF-1.4"),
            ("messages.audio_file.get", {"message_id": voice.pk}, b"OggS"),
            ("contacts.avatar.get", {"contact_id": contact.pk}, b"\x89PNG"),
        ):
            run, data = execute_action(self.context, key, arguments, conversation_id=self.conversation.pk)
            self.assertEqual(self.read_result(run, data)[2], expected)
        run, data = execute_action(self.context, "conversations.diagnostic.get", {}, conversation_id=self.conversation.pk)
        diagnostic = json.loads(self.read_result(run, data)[2])
        self.assertEqual(diagnostic["format"], "chatballs.conversation-diagnostic")
        self.assertFalse(diagnostic["coverage"]["secretsIncluded"])
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization, channel=self.conversation.channel,
                connection=self.connection, group=self.group, contact=self.conversation.contact)
        run, _ = execute_action(self.context, "messages.attachment_file.get", {"message_id": message.pk}, conversation_id=other.pk)
        self.assertEqual(run.state, "failed")
        foreign = TenantContext.for_membership(self.foreign_member)
        run, _ = execute_action(foreign, "messages.audio_file.get", {"message_id": voice.pk})
        self.assertEqual(run.state, "failed")

    def test_native_file_receipt_replays_and_retention_deletes_only_operational_copy(self):
        run, data = execute_action(self.context, "reports.support_csv.get", self.filters())
        self.read_result(run, data)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(ServiceFile.objects.count(), 1)
            self.assertEqual(run.steps.get().definition["files"], [data["file"]["fileId"]])
            displayed = run_payload(run, detail=True, tenant=self.context)
            self.assertEqual(displayed["steps"][0]["fileNames"][data["file"]["fileId"]], "support-report.csv")
            self.assertEqual(displayed["steps"][0]["result"], data)
            self.assertEqual(run.steps.get().definition["result"], data)
            ScenarioRun.objects.filter(pk=run.pk).update(finished_at=timezone.now() - timedelta(days=8))
        cleanup(self.context)
        with tenant_atomic(self.context):
            delete_operation_file({"fileId": data["file"]["fileId"]}, self.context)
            self.assertFalse(ServiceFile.objects.exists())

    def test_file_opener_is_limited_to_tenant_input_references_and_declared_size(self):
        self.assertFalse(connection.in_atomic_block)
        file = store_service_file(context=self.context, integration=None, name="data.txt", content_type="text/plain",
            stream=io.BytesIO(b"data"), size=4)
        for opener in (file_opener(self.foreign.pk), file_opener(self.organization.pk, allowed=set())):
            with self.assertRaises(ServiceFile.DoesNotExist):
                opener(file.file_id)
        with self.assertRaises(ValueError):
            store_service_file(context=self.context, integration=None, name="bad.txt", content_type="text/plain",
                stream=io.BytesIO(b"data"), size=1)
        with self.assertRaises(ValueError):
            file_opener(self.organization.pk, allowed={file.file_id}, max_bytes=3)(file.file_id)
