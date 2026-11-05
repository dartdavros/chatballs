"""Call source permissions and credential lifecycle through the common runner."""

from uuid import uuid4

from django.test import override_settings

from chatballs.calls.models import CallSession
from chatballs.calls.tokens import issue_call_access_token
from chatballs.conversations.models import Conversation, Message, SystemEvent
from chatballs.integrations.action_catalog.native_call_test_base import NativeCallCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeCallTests(NativeCallCase):
    def test_staff_actions_share_lifecycle_and_replay_does_not_create_another_call(self):
        empty, result = execute_action(self.context, "calls.active.get", {}, conversation_id=self.conversation.pk)
        self.assertEqual((empty.state, result), ("completed", {"call": None}))
        run, call_id = self.create()
        run_one(self.context, run.public_id)
        for key, arguments in (("calls.active.get", {}), ("calls.session.get", {"call_session_id": call_id})):
            current, result = execute_action(self.context, key, arguments, conversation_id=self.conversation.pk)
            self.assertEqual((current.state, result["call"]["id"]), ("completed", call_id))
        cancelled, result = execute_action(self.context, "calls.cancel.post", {"call_session_id": call_id},
            conversation_id=self.conversation.pk)
        self.assertEqual((cancelled.state, result["call"]["status"]), ("completed", "CANCELLED"))
        with tenant_atomic(self.context):
            self.assertEqual(CallSession.objects.count(), 1)
            self.assertEqual(Message.objects.filter(system_event=SystemEvent.CALL_REQUESTED).count(), 1)

    def test_customer_accept_and_end_keep_token_secret_and_original_terminal_state(self):
        self.create()
        token = self.customer_token()
        for key, status in (("state", "RINGING"), ("accept", "ACCEPTED"), ("accept", "ACCEPTED"), ("end", "FAILED")):
            run, result = execute_action(self.context, f"calls.{key}.post", {"credential": token})
            self.assertEqual((run.state, result["call"]["status"]), ("completed", status))
        with tenant_atomic(self.context):
            self.assertEqual(Message.objects.filter(system_event=SystemEvent.CALL_ACCEPTED).count(), 1)
            payload = run_payload(run, detail=True, tenant=self.context)
            self.assertNotIn(token, str(payload))
            self.assertEqual(payload["steps"][0]["arguments"]["credential"], {"redacted": True})

    def test_foreign_expired_wrong_subject_and_staff_credentials_cannot_accept(self):
        _run, call_id = self.create()
        token = self.customer_token()
        foreign = TenantContext.for_membership(self.foreign_member)
        rejected, _ = execute_action(foreign, "calls.accept.post", {"credential": token})
        self.assertEqual(rejected.state, "failed")
        for side, subject in (("CUSTOMER", str(uuid4())), ("STAFF", str(self.user.pk))):
            candidate = issue_call_access_token(call_session_id=call_id, side=side, subject_id=subject)
            rejected, _ = execute_action(self.context, "calls.accept.post", {"credential": candidate})
            self.assertEqual(rejected.state, "failed")
        with override_settings(CHATBALLS_CALL_ACCESS_TTL_SECONDS=-1):
            expired = issue_call_access_token(call_session_id=call_id, side="CUSTOMER", subject_id="expired")
        rejected, _ = execute_action(self.context, "calls.state.post", {"credential": expired})
        self.assertEqual(rejected.state, "failed")
        declined, result = execute_action(self.context, "calls.decline.post", {"credential": token})
        self.assertEqual((declined.state, result["call"]["status"]), ("completed", "DECLINED"))

    def test_uuid_and_credential_cannot_escape_the_run_conversation(self):
        _run, call_id = self.create()
        token = self.customer_token()
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization, channel=self.conversation.channel,
                group=self.group, connection=self.connection, contact=self.conversation.contact)
        for key, arguments in (("calls.cancel.post", {"call_session_id": call_id}),
                ("calls.decline.post", {"credential": token})):
            rejected, _ = execute_action(self.context, key, arguments, conversation_id=other.pk)
            self.assertEqual(rejected.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(CallSession.objects.get(pk=call_id).status, "RINGING")

    def test_disabled_call_feature_and_missing_participation_remain_source_restrictions(self):
        _run, call_id = self.create()
        with tenant_atomic(self.context):
            CallSession.objects.get(pk=call_id).participants.filter(side="STAFF").delete()
        rejected, _ = execute_action(self.context, "calls.cancel.post", {"call_session_id": call_id})
        self.assertEqual(rejected.state, "failed")
        with tenant_atomic(self.context):
            self.connection.audio_calls_enabled = False
            self.connection.save(update_fields=["audio_calls_enabled"])
        rejected, _ = execute_action(self.context, "calls.invite.post", {"kind": "AUDIO"},
            conversation_id=self.conversation.pk)
        self.assertEqual(rejected.state, "failed")
