"""Live credential scope, immutable votes and management rights through runner."""

from datetime import timedelta

from django.test import TransactionTestCase
from django.utils import timezone

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.models import Conversation
from chatballs.events.models import OutboxEvent
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.ratings.credentials import credential_for, hash_credential
from chatballs.ratings.models import CustomerRating, RatingRequest
from chatballs.ratings.test_support import RatingTestBase, prepare_rating_transport
from chatballs.ratings.web_delivery import deliver_due_requests
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeRatingTests(TransactionTestCase):
    row = DomainEventTestBase.row
    completion = RatingTestBase.completion
    scheduled = RatingTestBase.scheduled

    def setUp(self):
        DomainEventTestBase.setUpTestData.__func__(type(self))
        prepare_rating_transport(self)
        with tenant_atomic(self.context):
            self.target = self.scheduled()
            deliver_due_requests(self.context)
            self.target.refresh_from_db()
            self.credential = credential_for(self.target)

    def test_live_credential_votes_once_and_never_appears_in_journal(self):
        values = {"credential": self.credential, "value": 5, "comment": "Customer feedback"}
        run, result = execute_action(self.context, "ratings.customer.post", values)
        self.assertEqual((run.state, result["value"]), ("completed", 5))
        run_one(self.context, run.public_id)
        _, repeated = execute_action(self.context, "ratings.customer.post", values)
        self.assertEqual(repeated, result)
        changed, _ = execute_action(self.context, "ratings.customer.post", {**values, "value": 4})
        self.assertEqual(changed.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(CustomerRating.objects.count(), 1)
            self.assertEqual(OutboxEvent.objects.filter(event_type="ratings.received").count(), 1)
            payload = run_payload(run, detail=True, tenant=self.context)
            self.assertEqual(payload["steps"][0]["arguments"]["credential"], {"redacted": True})
            self.assertNotIn(self.credential, str(payload))

    def test_foreign_expired_and_cancelled_credentials_cannot_be_used_by_a_grant(self):
        foreign = TenantContext.for_membership(self.foreign_member)
        run, _ = execute_action(foreign, "ratings.customer.get", {"credential": self.credential})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            event = self.row(event_type="CLOSED")
            event.save()
            expired = RatingRequest.objects.get(completion=event)
            expired.sent_at = timezone.now() - timedelta(days=8)
            expired.expires_at = expired.sent_at + timedelta(days=7)
            expired.credential_hash = hash_credential(credential_for(expired))
            expired.save(update_fields=["sent_at", "expires_at", "credential_hash"])
        run, _ = execute_action(self.context, "ratings.customer.post", {"credential": credential_for(expired), "value": 5})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            RatingRequest.objects.filter(pk=self.target.pk).update(cancelled_at=timezone.now())
        run, _ = execute_action(self.context, "ratings.customer.get", {"credential": self.credential})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(CustomerRating.objects.exists())

    def test_protected_results_share_scale_counts_and_conversation_card(self):
        execute_action(self.context, "ratings.customer.post", {"credential": self.credential, "value": 4})
        run, result = execute_action(self.context, "ratings.results.get", {})
        self.assertEqual((run.state, result["count"]), ("completed", 1))
        self.assertEqual(result["scaleGroups"][0]["values"], [{"value": 4, "count": 1}])
        run, card = execute_action(self.context, "ratings.conversation.get", {}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(card["results"][0]["value"], 4)
        run, question = execute_action(self.context, "ratings.customer.get", {"credential": self.credential})
        self.assertEqual(run.state, "completed")
        self.assertEqual(question["result"]["value"], 4)

    def test_disabling_settings_cancels_the_existing_customer_request(self):
        run, settings = execute_action(self.context, "ratings.settings.get", {})
        self.assertEqual((run.state, settings["enabled"]), ("completed", True))
        run, settings = execute_action(self.context, "ratings.settings.patch", {"enabled": False})
        self.assertEqual((run.state, settings["enabled"]), ("completed", False))
        with tenant_atomic(self.context):
            self.target.refresh_from_db()
            self.assertIsNotNone(self.target.cancelled_at)
        run, _ = execute_action(self.context, "ratings.customer.get", {"credential": self.credential})
        self.assertEqual(run.state, "failed")

    def test_live_credential_cannot_escape_the_run_conversation(self):
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization, channel=self.conversation.channel,
                group=self.group, connection=self.connection, contact=self.conversation.contact)
        run, _ = execute_action(self.context, "ratings.customer.post", {"credential": self.credential, "value": 5},
            conversation_id=other.pk)
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(CustomerRating.objects.exists())

    def test_support_feedback_preserves_rating_distribution_and_sent_request_cohort(self):
        vote, _ = execute_action(self.context, "ratings.customer.post", {"credential": self.credential,
            "value": 4, "comment": "Customer feedback"})
        self.assertEqual(vote.state, "completed")
        run, result = execute_action(self.context, "reports.support.get", {
            "from": (self.conversation.created_at - timedelta(seconds=1)).isoformat(),
            "to": (timezone.now() + timedelta(seconds=1)).isoformat(), "timezone": "UTC"})
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        feedback = result["customerRatings"]
        self.assertEqual(feedback["groups"][0]["values"], [{"value": 4, "count": 1}])
        self.assertEqual(feedback["details"][0]["comment"], "Customer feedback")
        summary = feedback["scaleSummaries"][0]
        self.assertEqual((summary["ratingCount"], summary["meanValue"], summary["commentCount"]), (1, 4, 1))
        self.assertEqual((summary["delivery"]["sentCount"], summary["delivery"]["answeredCount"]), (1, 1))
        self.assertEqual(summary["delivery"]["responseRate"], 1)
