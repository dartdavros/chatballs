"""Shared real call fixture; creates no source or demo environment data."""

from django.test import TransactionTestCase

from chatballs.calls.services import open_call_for_identity
from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.models import ConnectionIdentity
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.tenancy.database import tenant_atomic


class NativeCallCase(TransactionTestCase):
    def setUp(self):
        DomainEventTestBase.setUpTestData.__func__(type(self))
        with tenant_atomic(self.context):
            self.connection.channel = self.conversation.channel
            self.connection.audio_calls_enabled = True
            self.connection.save(update_fields=["channel", "audio_calls_enabled"])
            self.identity = ConnectionIdentity.objects.create(
                organization=self.organization, connection=self.connection,
                contact=self.conversation.contact, external_user_id="native-call-customer",
            )

    def create(self):
        run, result = execute_action(self.context, "calls.invite.post", {"kind": "AUDIO"},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertEqual(result["call"]["status"], "RINGING")
        self.assertNotIn("staffAccessToken", result)
        return run, result["call"]["id"]

    def customer_token(self):
        with tenant_atomic(self.context):
            return open_call_for_identity(identity=self.identity).customer_access_token
