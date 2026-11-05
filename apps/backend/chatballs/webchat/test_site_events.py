from django.core.cache import cache
from django.db import connection
from rest_framework.throttling import SimpleRateThrottle

from chatballs.conversations.models import Conversation, Message
from chatballs.events.models import OutboxEvent
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_test_base import SiteEventCase


class SiteEventIngressTests(SiteEventCase):
    def test_no_consent_no_receipt_or_conversation_and_form_revision_is_current(self):
        session = self.issue(consent=False)
        self.assertEqual(self.emit().status_code, 400)
        self.assertFalse(EventReceipt.objects.exists())
        self.assertFalse(SiteEventLaunch.objects.exists())
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(Message.objects.exists())
        self.client.post("/api/v1/webchat/consent/", {"hostOrigin": "https://site.example", "consentVersion": "v1"}, format="json")
        self.widget.consent_config = {"consent_version": "v2"}
        self.widget.save(update_fields=["consent_config"])
        self.assertEqual(self.emit().status_code, 400)
        self.assertFalse(EventReceipt.objects.exists())
        session.refresh_from_db()
        self.assertEqual(session.consent_version, "v1")

    def test_commit_contains_one_encrypted_receipt_target_and_outbox_before_ack(self):
        other = self.make_scenario("Unselected subscriber")
        session = self.issue()
        response = self.emit()
        self.assertEqual(response.status_code, 202, response.content)
        receipt = EventReceipt.objects.get(event_key="webchat.site_event")
        self.assertEqual(list(receipt.deliveries.values_list("scenario_id", flat=True)), [self.scenario.pk])
        self.assertNotEqual(other.pk, self.scenario.pk)
        self.assertTrue(OutboxEvent.objects.filter(event_type="integrations.receipt", payload__receiptId=receipt.pk).exists())
        self.assertTrue(OutboxEvent.objects.filter(event_type="integrations.fanout", payload__receiptId=receipt.pk).exists())
        self.assertEqual(SiteEventLaunch.objects.get(session=session).receipt, receipt)
        self.assertFalse(Conversation.objects.exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT content FROM integrations_eventreceipt WHERE id=%s", [receipt.pk])
            self.assertNotIn("private-category", str(cursor.fetchone()[0]))
        self.assertNotIn("launchId", str(response.json()))

    def test_same_or_new_id_cannot_launch_rule_twice_for_the_session(self):
        self.issue()
        self.assertEqual(self.emit().status_code, 202)
        self.assertEqual(self.emit().status_code, 200)
        self.assertEqual(self.emit({**self.event, "eventId": "new-id"}).status_code, 200)
        self.assertEqual(EventReceipt.objects.filter(event_key="webchat.site_event").count(), 1)
        self.assertEqual(SiteEventLaunch.objects.count(), 1)

    def test_schema_origin_and_authority_selectors_are_rejected_before_receipt(self):
        self.issue()
        for data in ({"category": "x", "unknown": "secret"}, {"category": None}, {"category": "x" * 121}):
            response = self.emit({**self.event, "data": data})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("secret", str(response.json()))
        self.assertEqual(self.emit(origin="https://foreign.example").status_code, 401)
        self.assertEqual(self.emit({**self.event, "scenario_id": str(self.scenario.public_id)}).status_code, 400)
        self.assertFalse(EventReceipt.objects.exists())

    def test_history_and_operator_mode_suppress_a_first_reply(self):
        session = self.issue()
        Conversation.objects.create(organization=self.organization, channel=self.channel,
            connection=session.connection, contact=session.identity.contact, lifecycle="CLOSED")
        self.assertEqual(self.emit().json(), {"state": "suppressed"})
        self.assertFalse(SiteEventLaunch.objects.exists())

    def test_cancel_before_ingress_fences_the_later_request(self):
        self.issue()
        response = self.client.post("/api/v1/webchat/site-events/cancel/", {"hostOrigin": "https://site.example"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.emit().status_code, 200)
        self.assertFalse(EventReceipt.objects.exists())

    def test_new_required_form_cannot_be_bypassed_by_an_existing_token(self):
        self.issue()
        self.widget.integration.config = {"siteEvent": self.rule, "preChat": {
            "enabled": True, "fields": [{"key": "name", "required": True}]}}
        self.widget.integration.save(update_fields=["config"])
        self.assertEqual(self.emit().status_code, 400)
        response = self.client.post("/api/v1/webchat/consent/", {
            "hostOrigin": "https://site.example", "consentVersion": "v1"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EventReceipt.objects.exists())
        response = self.client.post("/api/v1/webchat/consent/", {
            "hostOrigin": "https://site.example", "consentVersion": "v1",
            "preChatFields": {"name": "Visitor"}}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.emit().status_code, 202)
        self.assertFalse(Message.objects.exists())

    def test_raw_size_and_shared_session_rate_limit_are_enforced(self):
        self.issue()
        self.assertEqual(self.emit({**self.event, "data": {"category": "x" * 21000}}).status_code, 400)
        original = SimpleRateThrottle.THROTTLE_RATES
        SimpleRateThrottle.THROTTLE_RATES = {**original, "webchat_session_write": "1/min"}
        cache.clear()
        try:
            self.assertEqual(self.emit().status_code, 202)
            self.assertEqual(self.emit().status_code, 429)
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original
            cache.clear()
        self.assertEqual(EventReceipt.objects.filter(event_key="webchat.site_event").count(), 1)
