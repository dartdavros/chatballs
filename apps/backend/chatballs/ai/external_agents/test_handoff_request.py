"""Early handoff, lost ACK and revocations that must defeat the replay exception."""

from copy import deepcopy
from uuid import uuid4

from django.db import transaction
from django.test import TestCase

from chatballs.ai.external_agents.config_models import ExternalAgentBinding, ExternalAgentConnection
from chatballs.ai.external_agents.operation_models import ExternalAgentOperation
from chatballs.ai.external_agents.operation_testing import OperationData
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import Conversation, Message
from chatballs.identity.models import EmployeeGroup, Organization
from chatballs.notifications.models import Notification


class HandoffRequestTests(OperationData, RuntimeData, TestCase):
    def test_early_handoff_interrupts_work_and_replays_only_content_free_ack(self):
        group = EmployeeGroup.objects.create(organization=self.organization, name="Support")
        Conversation.objects.filter(pk=self.conversation.pk).update(group=group)
        row = self.prepare_session(complete=False)
        work = self.claim()
        body = self.operation_body("handoff")
        response = self.post_operation(body, "handoff")
        self.assertEqual(response.status_code, 200, response.content)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, "PAUSED")
        self.assertEqual(self.conversation.expected_responder, "OPERATOR")
        self.assertEqual(self.conversation.group, group)
        self.assertIsNone(self.conversation.assigned_operator_id)
        self.assertIsNotNone(self.conversation.waiting_since)
        notification = Notification.objects.get(type="OPERATOR_REQUESTED")
        self.assertEqual(notification.body, body["summary"])
        self.assertEqual(notification.audience_group, group)
        row.refresh_from_db()
        self.assertEqual(row.state, "cancelled")
        self.assertTrue(row.cancel_pending)
        self.settle(work, self.result(row))
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
        replay = self.post_operation(body, "handoff")
        self.assertEqual(replay.status_code, 200, replay.content)
        self.assertEqual(replay.json(), response.json())
        ack = replay.json()
        self.assertEqual((ack["state"], ack["items"], ack["deliveryId"], ack["requestId"]),
                         ("handed_off", [], None, None))
        self.assertNotIn(body["summary"], str(ack))
        self.assertEqual(Notification.objects.filter(type="OPERATOR_REQUESTED").count(), 1)
        changed = deepcopy(body)
        changed["summary"] += "!"
        self.assertEqual(self.post_operation(changed, "handoff").status_code, 409)
        self.assertEqual(self.post_operation(self.operation_body("handoff"), "handoff").status_code, 403)
        self.assertEqual(self.post_operation(self.operation_body()).status_code, 403)

    def test_replay_is_denied_after_another_control_revocation_even_if_state_returns(self):
        self.prepare_session()
        body = self.operation_body("handoff")
        self.assertEqual(self.post_operation(body, "handoff").status_code, 200)
        for mode in ("HUMAN", "PAUSED"):
            Conversation.objects.filter(pk=self.conversation.pk).update(control_mode=mode)
            self.assertEqual(self.post_operation(body, "handoff").status_code, 403)
        self.assertEqual(ExternalAgentOperation.objects.count(), 1)

    def test_feature_configuration_and_credential_changes_defeat_old_ack(self):
        self.prepare_session()
        body = self.operation_body("handoff")
        self.assertEqual(self.post_operation(body, "handoff").status_code, 200)
        Organization.objects.filter(pk=self.organization.pk).update(external_execution_enabled=False)
        self.assertEqual(self.post_operation(body, "handoff").status_code, 403)
        Organization.objects.filter(pk=self.organization.pk).update(external_execution_enabled=True)
        self.assertEqual(self.post_operation(body, "handoff").status_code, 403)

    def test_policy_generation_and_key_rotation_do_not_reauthorize_replay(self):
        from chatballs.ai.external_agents.auth import key_hash

        self.prepare_session()
        body = self.operation_body("handoff")
        self.assertEqual(self.post_operation(body, "handoff").status_code, 200)
        ExternalAgentBinding.objects.filter(agent=self.agent).update(proactive_enabled=False)
        self.assertEqual(self.post_operation(body, "handoff").status_code, 403)
        new_key = "rotated-test-only-credential-" + str(uuid4())
        ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(inbound_key_hash=key_hash(new_key))
        self.assertEqual(self.post_operation(body, "handoff").status_code, 401)
        self.assertEqual(self.post_operation(body, "handoff", HTTP_AUTHORIZATION="Bearer " + new_key).status_code, 403)

    def test_handoff_does_not_assign_or_return_control_and_rejects_changed_session(self):
        self.prepare_session(complete=False)
        body = self.operation_body("handoff")
        for field in ("employeeId", "groupId", "controlMode"):
            self.assertEqual(self.post_operation({**body, field: "1"}, "handoff").status_code, 400)
        self.assertEqual(self.post_operation({**body, "reasonCode": "arbitrary"}, "handoff").status_code, 400)
        self.assertEqual(self.post_operation({**body, "externalSessionId": "foreign"}, "handoff").status_code, 404)
        self.assertEqual(self.post_operation({**body, "authorizationId": str(uuid4())}, "handoff").status_code, 404)
        self.assertFalse(ExternalAgentOperation.objects.exists())
        response = self.post_operation(body, "handoff")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.post_operation(body, "handoff").json(), response.json())

    def test_independent_connection_and_key_changes_block_lost_ack(self):
        from chatballs.ai.external_agents.auth import key_hash

        self.prepare_session()
        body = self.operation_body("handoff")
        self.assertEqual(self.post_operation(body, "handoff").status_code, 200)
        with transaction.atomic():
            ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(enabled=False)
            self.assertEqual(self.post_operation(body, "handoff").status_code, 403)
            ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(enabled=True)
            self.assertEqual(self.post_operation(body, "handoff").status_code, 403)
            transaction.set_rollback(True)
        with transaction.atomic():
            new_key = "independent-rotation-test-only-" + str(uuid4())
            ExternalAgentConnection.objects.filter(pk=self.connection.pk).update(inbound_key_hash=key_hash(new_key))
            self.assertEqual(self.post_operation(body, "handoff").status_code, 401)
            self.assertEqual(self.post_operation(body, "handoff", HTTP_AUTHORIZATION="Bearer " + new_key).status_code, 403)
            transaction.set_rollback(True)
        self.assertEqual(self.post_operation(body, "handoff").status_code, 200)
