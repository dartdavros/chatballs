"""Knowledge uploads use real service files, storage quotas and domain attachments."""

import io

from chatballs.ai.models import KnowledgeAttachment, KnowledgeFragment
from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeKnowledgeFileTests(NativeFileCase):
    def test_upload_and_delete_preserve_content_and_file_ownership(self):
        run, output = execute_action(self.context, "knowledge.post", {"title": "Attachments"})
        self.assertEqual(run.state, "completed")
        knowledge_id = output["knowledge"]["id"]
        content = b"Knowledge attachment content."
        reference = store_service_file(context=self.context, integration=None,
            name="guide.txt", content_type="text/plain", stream=io.BytesIO(content), size=len(content))
        run, output = execute_action(self.context, "knowledge.attachments.post", {
            "knowledge_id": knowledge_id, "file": {"fileId": reference.file_id}})
        self.assertEqual(run.state, "completed")
        attachment_id = output["attachment"]["id"]
        with tenant_atomic(self.context):
            attachment = KnowledgeAttachment.objects.get(pk=attachment_id, organization=self.organization)
            self.assertEqual(attachment.extracted_text, content.decode())
            self.assertTrue(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).exists())
            with attachment.file.open("rb") as stored:
                self.assertEqual(stored.read(), content)
            storage, name = attachment.file.storage, attachment.file.name
            public_id = str(attachment.public_id)
        run, output = execute_action(self.context, "knowledge.file.get", {"public_id": public_id})
        self.assertEqual(self.read_result(run, output)[2], content)
        run, _ = execute_action(TenantContext.for_membership(self.foreign_member),
            "knowledge.file.get", {"public_id": public_id})
        self.assertEqual(run.state, "failed")
        run, _ = execute_action(self.context, "knowledge.attachment.delete", {
            "knowledge_id": knowledge_id, "attachment_id": attachment_id})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertFalse(storage.exists(name))
            self.assertFalse(KnowledgeAttachment.objects.filter(pk=attachment_id).exists())
            self.assertFalse(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).exists())
