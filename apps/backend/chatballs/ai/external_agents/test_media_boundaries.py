"""Authorization, native WEB publication, retention pins and transport boundaries."""

from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.utils import timezone

from chatballs.ai.external_agents.auth import issue_authorization
from chatballs.ai.external_agents.file_cleanup import cleanup
from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.public_messages import public_message
from chatballs.conversations.lifecycle_services import delete_conversation
from chatballs.conversations.models import Conversation, Message
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.models import OrganizationStorageUsage


class MediaBoundaryTests(MediaCase):
    def test_native_deletion_removes_staging_bytes_and_releases_storage_immediately(self):
        row = self.request()
        receipt = self.upload(row).json()
        record = ExternalAgentFile.objects.get(public_id=receipt["fileId"])
        with tenant_atomic(self.context):
            delete_conversation(context=self.context, conversation=self.conversation)
            self.assertFalse(record.file.storage.exists(record.file.name))
        record.refresh_from_db()
        self.assertTrue(record.released)
        self.assertEqual(OrganizationStorageUsage.objects.get(organization=self.organization).bytes_used, 0)
        self.assertEqual(self.download(row, record.public_id).status_code, 404)

    def test_known_file_is_unavailable_to_other_conversation_or_missing_authorization(self):
        row = self.request()
        receipt = self.upload(row).json()
        other = Conversation.objects.create(organization=self.organization, channel=self.channel,
                                            connection=self.messaging, contact=self.contact, external_chat_id="other")
        with tenant_atomic(self.context):
            session = issue_authorization(self.context, self.connection, self.agent.pk, other.pk)
        path = self.root.replace(f"/{self.conversation.pk}/", f"/{other.pk}/") + f"files/{receipt['fileId']}/"
        response = self.client.get(path, {"authorizationId": str(session.authorization_id)}, **self.header)
        self.assertEqual(response.status_code, 404)
        path = self.root + f"files/{receipt['fileId']}/"
        self.assertEqual(self.client.get(path, **self.header).status_code, 404)

    def test_current_stream_stops_after_revoke_and_expiry_never_extends(self):
        row = self.request()
        receipt = self.upload(row, b"x" * 150000).json()
        response = self.download(row, receipt["fileId"])
        chunks = iter(response.streaming_content)
        self.assertEqual(len(next(chunks)), 65536)
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.assertEqual(list(chunks), [])
        self.client.patch(self.url, {"enabled": True}, format="json")
        self.assertEqual(self.download(row, receipt["fileId"]).status_code, 403)

    def test_active_request_and_published_message_pin_bytes_then_orphan_is_released(self):
        row = self.request()
        receipt = self.upload(row).json()
        self.claim()
        record = ExternalAgentFile.objects.get(public_id=receipt["fileId"])
        future = timezone.now() + timedelta(days=2)
        with patch("chatballs.ai.external_agents.file_cleanup.timezone.now", return_value=future):
            self.assertEqual(self.download(row, record.public_id).status_code, 404)
            with tenant_atomic(self.context):
                self.assertEqual(cleanup(self.context), 0)
        body = self.result(row)
        body["outcome"]["messages"][0]["content"] = self.file_content(receipt)
        self.assertEqual(self.callback(row, body).status_code, 202)
        with patch("chatballs.conversations.transports.send_file", return_value=True):
            self.deliver(times=2)
        with patch("chatballs.ai.external_agents.file_cleanup.timezone.now", return_value=future):
            with tenant_atomic(self.context):
                self.assertEqual(cleanup(self.context), 0)
                self.assertTrue(record.file.storage.exists(record.file.name))
        Message.objects.filter(author_type="AI").delete()
        with patch("chatballs.ai.external_agents.file_cleanup.timezone.now", return_value=future):
            with tenant_atomic(self.context):
                self.assertEqual(cleanup(self.context), 1)

    def test_web_contact_uses_native_command_and_publication_snapshot_guard(self):
        self.organization.language = "en"
        self.organization.save(update_fields=["language"])
        self.messaging.provider = "WEB"
        self.messaging.save(update_fields=["provider"])
        with patch("chatballs.ai.external_agents.auth.consent_current", return_value=True), \
             patch("chatballs.ai.external_agents.readiness.consent_current", return_value=True):
            row = self.request()
            self.assertIsNotNone(self.claim())
            row.refresh_from_db()
            self.assertIn("contact_request", open_payload(row.snapshot_ciphertext)["deliveryConstraints"]["types"])
            body = self.result(row)
            body["outcome"]["messages"][0]["content"] = {"type": "contact_request"}
            response = self.callback(row, body)
        self.assertEqual(response.status_code, 200, response.content)
        message = Message.objects.get(author_type="AI")
        self.assertEqual(message.kind, "contact_request")
        self.assertEqual(message.text, t("conversations.contact_request_web", language="en"))
        self.assertEqual(public_message(message)["content"]["type"], "contact_request")
        self.conversation.refresh_from_db()
        self.assertIsNone(self.conversation.assigned_operator_id)
        self.assertFalse(self.sender.called)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Message.objects.filter(pk=message.pk).update(text="changed")
