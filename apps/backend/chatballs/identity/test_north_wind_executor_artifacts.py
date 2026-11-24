from uuid import uuid4

from django.contrib.contenttypes.models import ContentType

from chatballs.ai.external_agents.file_models import ExternalAgentFile, ExternalAgentFileGrant
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.conversations.models import Message
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.executor_artifacts import register_executor_artifacts
from chatballs.identity.demo_seed.registry import recording
from chatballs.tenancy.database import tenant_atomic


class NorthWindExecutorArtifactTests(MediaCase):
    def test_reset_claims_file_aliases_only_for_registered_messages(self):
        row = self.request()
        with tenant_atomic(self.context):
            dataset = DemoDataset.objects.create(
                organization=self.organization, generation=uuid4(), status=DemoDatasetStatus.INSTALLED,
                shop_state={"externalExecutor": {
                    "connectionId": self.connection.pk, "conversationId": self.conversation.pk,
                    "agentId": self.agent.pk,
                }},
            )
            with recording(dataset):
                demo_message = self.attachment_message()
            working_message = self.attachment_message()
            demo_file, demo_grant = self.file_alias(demo_message, row)
            working_file, working_grant = self.file_alias(working_message, row)

            register_executor_artifacts(dataset)

            self.assertEqual(self.registered_ids(dataset, ExternalAgentFile), {str(demo_file.pk)})
            self.assertEqual(self.registered_ids(dataset, ExternalAgentFileGrant), {str(demo_grant.pk), str(working_grant.pk)})
            self.assertTrue(ExternalAgentFile.objects.filter(pk=working_file.pk).exists())

    def attachment_message(self):
        return Message.objects.create(conversation=self.conversation, author_type="CONTACT", kind="file")

    def file_alias(self, message, request):
        file = ExternalAgentFile.objects.create(
            organization=self.organization, authorization_id=request.authorization_id,
            source_message=message, filename="document.txt", mime_type="text/plain", size=8,
            sha256="0" * 64, owned=False, complete=True,
        )
        grant = ExternalAgentFileGrant.objects.create(
            organization=self.organization, authorization_id=request.authorization_id, file=file, request=request,
        )
        return file, grant

    def registered_ids(self, dataset, model):
        content_type = ContentType.objects.get_for_model(model)
        return set(dataset.records.filter(content_type=content_type).values_list("object_id", flat=True))
