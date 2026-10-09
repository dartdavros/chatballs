import json

from django.core.exceptions import ValidationError

from chatballs.ai.diagnostic_models import TurnDiagnostic
from chatballs.conversations.diagnostic_testing import DiagnosticTestCase
from chatballs.conversations.models import AiTurnState, LifecycleState, Message, MessageAuthor
from chatballs.identity.models import AuditEvent, EmployeeRole, Organization


class DiagnosticExportTests(DiagnosticTestCase):
    def test_employee_cannot_download_even_if_the_dialog_is_visible(self):
        self.assertEqual(self.export(self.client).status_code, 403)

    def test_admin_and_owner_can_export_closed_dialog_and_download_is_audited(self):
        self.conversation.lifecycle = LifecycleState.CLOSED
        self.conversation.save(update_fields=["lifecycle"])
        for role in (EmployeeRole.ADMIN, EmployeeRole.OWNER):
            self.owner.role = role
            self.owner.save(update_fields=["role"])
            response = self.export()
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertIn("attachment;", response["Content-Disposition"])
            self.assertEqual(response.json()["format"], "chatballs.conversation-diagnostic")
        self.assertEqual(AuditEvent.objects.filter(action="conversations.diagnostic_exported").count(), 2)

    def test_cross_organization_export_is_not_available(self):
        other = Organization.objects.create(name="Other", slug="other-diagnostics")
        self.owner.organization = other
        self.owner.save(update_fields=["organization"])
        self.assertEqual(self.export().status_code, 404)

    def test_old_turn_is_reported_as_missing_without_fabricating_history(self):
        message = Message.objects.create(conversation=self.conversation, author_type=MessageAuthor.CONTACT,
                                         text="Где заказ?", ai_turn_state=AiTurnState.DONE)
        response = self.export().json()
        self.assertEqual(response["turns"], [])
        self.assertEqual(response["coverage"]["messagesWithoutTrace"], [message.id])
        self.assertFalse(response["coverage"]["currentConfigurationIsHistorical"])
        availability = response["currentConfiguration"]["toolAvailability"]
        self.assertEqual(availability[0]["reason"], "required_client_data_unavailable")

    def test_trace_tenant_must_match_the_message(self):
        other = Organization.objects.create(name="Other", slug="trace-other")
        message = Message.objects.create(conversation=self.conversation, author_type=MessageAuthor.CONTACT)
        with self.assertRaises(ValidationError):
            TurnDiagnostic.objects.create(message=message, organization=other)

    def test_export_masks_personal_values_and_secrets_and_cascade_removes_traces(self):
        message = Message.objects.create(conversation=self.conversation, author_type=MessageAuthor.CONTACT,
                                         text="Иван ivan@example.test session_token=customer-secret")
        TurnDiagnostic.objects.create(message=message, payload={"state": "completed", "agent": {"name": "Old name"}})
        payload = self.export().content.decode()
        for value in ("Иван", "ivan@example.test", "customer-secret"):
            self.assertNotIn(value, payload)
        self.assertEqual(json.loads(payload)["turns"][0]["agent"]["name"], "Old name")
        self.conversation.delete()
        self.assertFalse(TurnDiagnostic.objects.filter(message_id=message.id).exists())
