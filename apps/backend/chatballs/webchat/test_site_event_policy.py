from django.db import transaction
from django.utils import timezone

from chatballs.ai.models import AIAgent
from chatballs.conversations.models import Conversation
from chatballs.identity.models import Organization, OrganizationMembership
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.automation_events.fanout import deliver_one
from chatballs.integrations.execution.ai_policy import needs_confirmation
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.models import WebSession
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_test_base import SiteEventCase


class SiteEventPolicyTests(SiteEventCase):
    def launch(self):
        self.session = self.issue()
        self.assertEqual(self.emit().status_code, 202)
        delivery = EventReceipt.objects.get(event_key="webchat.site_event").deliveries.get()
        deliver_one(self.tenant, delivery.pk)
        delivery.refresh_from_db()
        self.assertIsNotNone(delivery.run_id, delivery.error_code)
        return delivery.run

    def test_current_authority_is_rechecked_after_the_snapshot(self):
        run = self.launch()
        claim = SiteEventLaunch.objects.get()
        changes = (
            (Organization, self.organization.pk, {"operation_mode_version": claim.mode_version + 1}),
            (AIAgent, self.agent.pk, {"status": "DISABLED"}),
            (AIAgent, self.agent.pk, {"instructions": "Changed instructions"}),
            (Integration, self.widget.integration_id, {"config": {"siteEvent": {**self.rule, "active": False}}}),
            (WebSession, self.session.pk, {"consent_form_revision": "stale"}),
            (Conversation, claim.conversation_id, {"control_mode": "HUMAN"}),
            (Conversation, claim.conversation_id, {"lifecycle": "CLOSED"}),
            (Conversation, claim.conversation_id, {"ai_control_version": claim.control_version + 1}),
            (OrganizationMembership, self.tenant.membership_id, {"blocked_at": timezone.now()}),
        )
        for model, pk, values in changes:
            with self.subTest(model=model.__name__, changed=list(values)):
                with tenant_atomic(self.tenant), transaction.atomic():
                    if "ai_control_version" in values:
                        # The DB trigger owns this counter; change control and
                        # restore AI mode to check generation independently.
                        model.objects.filter(pk=pk).update(control_mode="HUMAN")
                        model.objects.filter(pk=pk).update(control_mode="AI")
                    else:
                        model.objects.filter(pk=pk).update(**values)
                    with self.assertRaises(ExecutionDenied, msg=f"{model.__name__}: {list(values)}"):
                        authorize_run(self.tenant, run)
                    transaction.set_rollback(True)
        with tenant_atomic(self.tenant):
            authorize_run(self.tenant, run)

    def test_an_event_does_not_confirm_another_write_or_expand_action_authority(self):
        run = self.launch()
        with tenant_atomic(self.tenant):
            self.assertFalse(needs_confirmation(run, native_action("webchat.first_reply").operation))
            self.assertFalse(needs_confirmation(run, native_action("contacts.card.get").operation))
            self.assertTrue(needs_confirmation(run, native_action("contacts.card.patch").operation))
