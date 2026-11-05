from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.conversations.models import Message
from chatballs.integrations.automation_events.fanout import deliver_one
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.proactive_guards import current
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.proactive_status import status
from chatballs.webchat.site_event_test_base import SiteEventCase


class SiteEventStatusTests(SiteEventCase):
    def launch(self):
        self.session = self.issue()
        self.assertEqual(self.emit().status_code, 202)
        return SiteEventLaunch.objects.get()

    def test_a_skipped_scenario_does_not_leave_the_visitor_waiting_for_an_answer(self):
        claim = self.launch()
        self.assertEqual(status(self.session), "pending")
        claim.receipt.deliveries.update(state="skipped", error_code="conditions_not_met")
        self.assertEqual(status(self.session), "suppressed")
        self.assertFalse(Message.objects.exists())

    def test_a_finished_scenario_without_the_reply_action_is_not_still_typing(self):
        claim = self.launch()
        delivery = claim.receipt.deliveries.get()
        deliver_one(self.tenant, delivery.pk)
        delivery.refresh_from_db()
        run = delivery.run
        self.assertIsNotNone(run)
        for state, expected in (("completed", "suppressed"), ("cancelled", "suppressed"), ("failed", "failed")):
            with self.subTest(state=state):
                run.state = state
                run.save(update_fields=["state"])
                self.assertEqual(status(self.session), expected)
        self.assertFalse(Message.objects.exists())

    def test_the_same_deadline_stops_waiting_and_denies_a_late_effect(self):
        claim = self.launch()
        claim.created_at = timezone.now() - timedelta(seconds=settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS + 1)
        claim.save(update_fields=["created_at"])
        self.assertEqual(status(self.session), "suppressed")
        with tenant_atomic(self.tenant), self.assertRaises(ExecutionDenied):
            current(self.tenant, claim)
        self.assertFalse(Message.objects.exists())
