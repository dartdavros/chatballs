"""Ручная расшифровка проверяет capability внутри tenant-транзакции."""

from django.db import connection
from django.test import TransactionTestCase

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.testing import TenantAPIClient


class TranscribeRuntimePermissionsTests(TransactionTestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Voice", slug="voice-permissions")
        self.admin = HumanUser.objects.create_user(email="voice-admin@example.test")
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.admin, role="ADMIN", position_title="ADMIN",
        )
        self.own = self.ready_message(self.organization)
        other = Organization.objects.create(name="Other", slug="voice-permissions-other")
        self.foreign = self.ready_message(other)

    def ready_message(self, organization):
        channel = Channel.objects.create(organization=organization, name="Voice", code="voice")
        contact = Contact.objects.create(organization=organization, name="Voice")
        conversation = Conversation.objects.create(organization=organization, channel=channel, contact=contact)
        # Готовая стенограмма не читает файл и не вызывает внешнее распознавание.
        return Message.objects.create(
            conversation=conversation, author_type="CONTACT", kind="voice",
            audio="existing.webm", transcript="Ready", transcript_status="READY",
        )

    def test_admin_can_read_ready_transcript_under_runtime_rls_but_not_foreign_message(self):
        client = TenantAPIClient()
        client.force_authenticate(self.admin)
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            base = f"/api/v1/organizations/{self.organization.public_id}/conversations/messages/"
            own = client.post(f"{base}{self.own.id}/transcribe/")
            self.assertEqual(own.status_code, 200, own.content)
            self.assertEqual(own.json()["message"]["transcript"], "Ready")
            foreign = client.post(f"{base}{self.foreign.id}/transcribe/")
            self.assertEqual(foreign.status_code, 404, foreign.content)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")
