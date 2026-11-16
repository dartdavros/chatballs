"""Private panel files use real storage and revoke with the owning test scope."""

from chatballs.ai.external_agents import dispatch, test_chat
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.test_models import ExternalAgentTestSession
from chatballs.conversations.models import Message
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.tenancy.database import tenant_atomic


class PrivatePanelFileTests(MediaCase):
    def test_only_initiator_reads_accepted_file_until_scope_closes(self):
        identifier = test_chat.start(self.context, self.channel.pk, {})["id"]
        test_chat.send(self.context, self.channel.pk, identifier, {"message": "Private file"})
        scope = ExternalAgentTestSession.objects.get(public_id=identifier)
        with tenant_atomic(self.context):
            dispatch.claim(self.context, scope.conversation_id)
        row = ExternalAgentRequest.objects.get(conversation_id=scope.conversation_id)
        self.root = (f"/api/v1/external-agent/connections/{self.connection.pk}"
                     f"/conversations/{scope.conversation_id}/")
        uploaded = self.upload(row, b"private test bytes")
        self.assertEqual(uploaded.status_code, 201, uploaded.content)
        body = self.result(row)
        body["outcome"]["messages"][0]["content"] = self.file_content(uploaded.json())
        response = self.callback(row, body)
        self.assertEqual(response.status_code, 200, response.content)
        message = Message.including_tests.get(conversation=scope.conversation, author_type="AI")
        url = (f"/api/v1/organizations/{self.organization.public_id}/agents/{self.channel.pk}"
               f"/external-test/{identifier}/files/{message.pk}/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"private test bytes")
        other = HumanUser.objects.create_user(email="other-file-admin@example.invalid")
        OrganizationMembership.objects.create(organization=self.organization, user=other, role="ADMIN")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.user)
        test_chat.close(self.context, self.channel.pk, identifier)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.sender.assert_not_called()
