"""Existing WebSession authentication never expands the run's canonical scope."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.calls.models import CallSession
from chatballs.conversations.models import Conversation
from chatballs.integrations.action_catalog.native_call_test_base import NativeCallCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.models import WebSession
from chatballs.webchat.services import hash_session_token
from chatballs.webchat.testing import create_web_widget


class NativeWidgetCallTests(NativeCallCase):
    def setUp(self):
        super().setUp()
        self.credential = "native-widget-customer-secret"
        with tenant_atomic(self.context):
            widget = create_web_widget(self.conversation.channel, integration=self.connection)
            self.session = WebSession.objects.create(organization=self.organization,
                widget=widget, connection=self.connection, identity=self.identity,
                token_hash=hash_session_token(self.credential))

    def execute(self, *, tenant=None, conversation=None, credential=None):
        return execute_action(tenant or self.context, "calls.widget_decline.post",
            {"credential": credential or self.credential},
            conversation_id=(conversation or self.conversation).pk)

    def test_decline_uses_source_identity_once_and_never_exposes_credential(self):
        self.create()
        run, result = self.execute()
        self.assertEqual((run.state, result["ok"], result["call"]["status"]), ("completed", True, "DECLINED"))
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(CallSession.objects.count(), 1)
            self.assertEqual(CallSession.objects.get().ended_by, "CUSTOMER")
            payload = run_payload(run, detail=True, tenant=self.context)
            self.assertEqual(payload["steps"][0]["arguments"]["credential"], {"redacted": True})
            self.assertNotIn(self.credential, str(payload))
            # No call-access exchange is performed by this command.
            self.assertIsNone(CallSession.objects.get().invite.opened_at)

    def test_scope_and_foreign_tenant_fail_before_declining_the_live_call(self):
        self.create()
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization,
                channel=self.conversation.channel, group=self.group,
                connection=self.connection, contact=self.conversation.contact)
        denied, _ = self.execute(conversation=other)
        self.assertEqual(denied.state, "failed")
        foreign = TenantContext.for_membership(self.foreign_member)
        denied, _ = self.execute(tenant=foreign, conversation=self.foreign_conversation)
        self.assertEqual(denied.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(CallSession.objects.get().status, "RINGING")

    def test_invalid_and_idle_expired_sessions_cannot_decline(self):
        self.create()
        denied, _ = self.execute(credential="unknown-widget-credential")
        self.assertEqual(denied.state, "failed")
        with tenant_atomic(self.context):
            WebSession.objects.filter(pk=self.session.pk).update(last_seen_at=timezone.now()
                - timedelta(seconds=settings.CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS + 1))
        denied, _ = self.execute()
        self.assertEqual(denied.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(CallSession.objects.get().status, "RINGING")
