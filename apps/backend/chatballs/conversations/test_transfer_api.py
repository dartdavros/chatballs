from uuid import uuid4

from django.db import connection, transaction
from django.utils import timezone

from chatballs.conversations.assignment import assign_operator
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.models import Message, SystemEvent
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.transfer_models import ConversationTransfer
from chatballs.conversations.transfer_operation_test_base import TransferOperationTestBase
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import EmployeeRole
from chatballs.notifications.models import Notification
from chatballs.notifications.serializers import notification_payload
from chatballs.tenancy.database import tenant_atomic


class TransferAPITests(TransferOperationTestBase):
    def test_transfer_is_one_operation_in_runtime_role_and_keeps_ai_mode(self):
        with tenant_atomic(self.context):
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            response = self.post()
            history = self.client.get(f"{self.root}{self.conversation.pk}/transfers/")
            self.assertEqual(history.status_code, 200)
            self.assertEqual(history.data["items"][0]["comment"], self.data["comment"])
            self.assertEqual(self.client.get(self.root + "directory/").status_code, 200)
            self.assertEqual(response.status_code, 200, response.data)
            row = ConversationTransfer.objects.get()
            self.conversation.refresh_from_db()
            self.assertEqual(row.assignment_version, self.conversation.assignment_version)
            self.assertEqual(self.conversation.assignment_version, 1)
            self.assertEqual(self.conversation.control_mode, "AI")
            self.assertEqual(self.conversation.assigned_operator_id, row.new_operator_id)
            fact = ConversationEvent.objects.get()
            self.assertEqual((fact.event_type, fact.operation_id, fact.responsible_id),
                             ("TRANSFERRED", row.operation_id, row.new_operator_id))
            notification = Notification.objects.get()
            self.assertEqual(notification.recipient_user_id, row.new_operator_id)
            self.assertEqual(notification.dedup_key, f"transfer:{row.operation_id}")
            payload = notification_payload(notification, unread=True)
            self.assertEqual(payload["transferId"], row.pk)
            self.assertEqual(notification.text_params, {"transferId": row.pk})
            self.assertNotIn(self.data["comment"], payload["title"] + payload["body"])
            detail = self.client.get(f"{self.root}{self.conversation.pk}/transfers/{row.pk}/")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.data["transfer"]["conversation"], {"contactName": "Customer", "provider": ""})
            self.assertIn("avatarUrl", detail.data["transfer"]["initiatedBy"])
            message = Message.objects.get(conversation=self.conversation, system_event=SystemEvent.ASSIGNED_TO)
            self.assertEqual(message_payload(message)["transferId"], row.pk)
            self.assertNotIn(self.data["comment"], str(message_payload(message)))
            self.assertNotIn(self.reason.name, str(message.system_params))
            event = self.outbox_since_setup().get()
            self.assertEqual(event.payload, {"notificationId": notification.pk})
            self.assertEqual(event.actor_kind, "SYSTEM")
            self.assertIsNone(event.membership_id)

    def test_outer_rollback_removes_assignment_journal_fact_notification_and_outbox(self):
        with self.assertRaises(RuntimeError), transaction.atomic():
            assign_operator(context=self.context, conversation_id=self.conversation.pk, transfer=self.data)
            raise RuntimeError("rollback")
        self.assert_no_transfer()

    def test_first_assignment_has_assigned_fact_and_same_operator_is_rejected(self):
        self.conversation.assigned_operator = None
        self.conversation.save(update_fields=["assigned_operator"])
        response = self.post(expectedVersion=1)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["transfer"]["previousOperatorId"])
        self.assertEqual(ConversationEvent.objects.get().event_type, "ASSIGNED")
        self.assertEqual(self.post(expectedVersion=2, operationId=str(uuid4())).status_code, 400)
        self.assertEqual(ConversationTransfer.objects.count(), 1)

    def test_closed_conversation_is_rejected_without_side_effects(self):
        self.conversation.lifecycle = "CLOSED"
        self.conversation.save(update_fields=["lifecycle"])
        self.assertEqual(self.post().status_code, 400)
        self.assert_no_transfer()

    def test_disabled_foreign_reason_and_invalid_input_do_not_mutate(self):
        self.reason.is_active = False
        self.reason.save(update_fields=["is_active"])
        for changes in ({}, {"reasonId": self.foreign_reason.pk}, {"operationId": "bad"},
                        {"comment": 10}, {"expectedVersion": True}, {"userId": "bad"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post(**changes).status_code, 400)
                self.assert_no_transfer()

    def test_blocked_inactive_foreign_and_policy_denied_recipient_do_not_mutate(self):
        employee = self.members[EmployeeRole.EMPLOYEE]
        for user_id in (self.foreign_user.pk, 99999999):
            self.assertEqual(self.post(userId=user_id).status_code, 400)
        employee.blocked_at = timezone.now()
        employee.save(update_fields=["blocked_at"])
        self.assertEqual(self.post().status_code, 400)
        employee.blocked_at = None
        employee.save(update_fields=["blocked_at"])
        employee.user.is_active = False
        employee.user.save(update_fields=["is_active"])
        self.assertEqual(self.post().status_code, 400)
        employee.user.is_active = True
        employee.user.save(update_fields=["is_active"])
        self.policy.unavailable = False
        self.policy.save(update_fields=["unavailable"])
        self.assertEqual(self.post().status_code, 400)
        self.assert_no_transfer()

    def test_stale_version_returns_conflict_and_current_assignment(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.post(operationId=str(uuid4()))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(int(response.data["assignmentVersion"]), 1)
        self.assertEqual(int(response.data["assignedOperatorId"]), self.data["userId"])
        self.assertEqual(ConversationTransfer.objects.count(), 1)

    def test_replay_returns_original_after_new_transfer_without_overwriting_it(self):
        original = self.post().json()
        later = self.post(userId=self.members[EmployeeRole.SUPERVISOR].user_id,
                          expectedVersion=1, operationId=str(uuid4()))
        self.assertEqual(later.status_code, 200)
        self.policy.unavailable = False
        self.policy.save(update_fields=["unavailable"])
        self.reason.is_active = False
        self.reason.save(update_fields=["is_active"])
        replay = self.post(userId=self.foreign_user.pk, comment="changed").json()
        self.assertEqual(original, replay)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.assigned_operator_id, self.members[EmployeeRole.SUPERVISOR].user_id)
        self.assertEqual(self.conversation.assignment_version, 2)
        self.assertEqual(ConversationTransfer.objects.count(), 2)
        self.assertEqual(ConversationEvent.objects.count(), 2)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(self.outbox_since_setup().count(), 2)

    def test_key_cannot_disclose_another_conversation_or_actor_result(self):
        self.assertEqual(self.post().status_code, 200)
        self.client.force_authenticate(self.members[EmployeeRole.ADMIN].user)
        response = self.post()
        self.assertEqual(response.status_code, 409)
        self.assertNotIn(self.data["comment"], str(response.data))

    def test_legacy_assignment_obeys_policy_and_invalidates_transfer_version(self):
        response = self.client.post(self.endpoint, {"userId": self.data["userId"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversation"]["assignmentVersion"], 1)
        self.assertEqual(self.post(operationId=str(uuid4())).status_code, 409)
        self.policy.unavailable = False
        self.policy.save(update_fields=["unavailable"])
        response = self.client.post(self.endpoint, {"userId": self.members[EmployeeRole.SUPERVISOR].user_id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ConversationTransfer.objects.exists())

    def test_unassignment_and_raw_updates_cannot_reset_assignment_version(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.client.post(self.endpoint, {"userId": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversation"]["assignmentVersion"], 2)
        self.conversation.__class__.objects.filter(pk=self.conversation.pk).update(assignment_version=0)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.assignment_version, 2)

    def test_legacy_key_replay_preserves_later_transfer_without_duplicate_facts(self):
        key = str(uuid4())
        body = {"userId": self.data["userId"]}
        response = self.client.post(self.endpoint, body, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConversationEvent.objects.count(), 1)
        # A fresh key for the current recipient is also a no-op.
        self.assertEqual(self.client.post(self.endpoint, body, format="json").status_code, 200)
        self.assertEqual(ConversationEvent.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        recipient = self.members[EmployeeRole.SUPERVISOR].user_id
        self.assertEqual(self.post(userId=recipient, expectedVersion=1).status_code, 200)
        counts = {model: model.objects.count() for model in
                  (ConversationTransfer, ConversationEvent, Message, Notification, OutboxEvent)}
        self.policy.unavailable = False
        self.policy.save(update_fields=["unavailable"])
        response = self.client.post(self.endpoint, body, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversation"]["assignedOperatorId"], recipient)
        self.assertEqual(response.data["conversation"]["assignmentVersion"], 2)
        self.assertEqual(counts, {model: model.objects.count() for model in counts})

    def test_transfer_rejects_key_used_by_legacy_assignment_without_mutation(self):
        body = {"userId": self.data["userId"]}
        response = self.client.post(self.endpoint, body, format="json",
                                    HTTP_IDEMPOTENCY_KEY=self.data["operationId"])
        self.assertEqual(response.status_code, 200)
        counts = {model: model.objects.count() for model in
                  (ConversationTransfer, ConversationEvent, Message, Notification, OutboxEvent)}
        response = self.post(userId=self.members[EmployeeRole.SUPERVISOR].user_id, expectedVersion=1)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn(self.data["comment"], str(response.data))
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.assigned_operator_id, body["userId"])
        self.assertEqual(self.conversation.assignment_version, 1)
        self.assertEqual(counts, {model: model.objects.count() for model in counts})
