from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase
from django.utils import timezone

from chatballs.ai.provider.base import ChatResult
from chatballs.ai.turn import TurnAnswer
from chatballs.conversations.models import Conversation, Message
from chatballs.integrations.automation_events.fanout import deliver_one
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat import services
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_test_base import SiteEventSetup


class ProactiveTurnTests(SiteEventSetup, TransactionTestCase):
    def launch(self):
        self.session = self.issue()
        response = self.emit()
        self.assertEqual(response.status_code, 202, response.content)
        receipt = EventReceipt.objects.get(event_key="webchat.site_event")
        delivery = receipt.deliveries.get()
        deliver_one(self.tenant, delivery.pk)
        delivery.refresh_from_db()
        self.assertEqual(delivery.state, "delivered", delivery.error_code)
        self.assertIsNotNone(delivery.run_id)
        return delivery.run

    def pump(self, run):
        from chatballs.webchat.proactive import execute
        errors = []
        def observed(*args):
            try:
                return execute(*args)
            except Exception as error:
                errors.append(error)
                raise
        for _ in range(8):
            with patch("chatballs.webchat.proactive.execute", side_effect=observed):
                run_one(self.tenant, run.public_id)
            unexpected = [error for error in errors if not isinstance(error, ValueError)]
            if unexpected:
                raise unexpected[0]
            run.refresh_from_db()
            if run.state in {"completed", "failed"}:
                return run.state
        self.fail(f"Run did not finish: {run.state}")

    def answer(self, plan, **kwargs):
        self.plans = [*getattr(self, "plans", []), plan]
        return TurnAnswer(result=ChatResult(text="How can I help?", model="test", prompt_tokens=1, completion_tokens=1))

    def test_one_real_domain_message_without_a_fictional_customer_or_second_model_cycle(self):
        self.event["data"]["category"] = "person@example.test"
        run = self.launch()
        with patch("chatballs.webchat.proactive.run_turn_chat", side_effect=self.answer) as model:
            self.assertEqual(self.pump(run), "completed")
        self.assertEqual(model.call_count, 1)
        plan = self.plans[0]
        self.assertFalse(any(message.role == "user" for message in plan.job.messages))
        self.assertTrue(any("Trusted scenario task" in message.content for message in plan.job.messages))
        self.assertTrue(any("недоверенные" in message.content for message in plan.job.messages))
        self.assertTrue(any("Отвечай всегда на языке" in message.content for message in plan.job.messages))
        self.assertFalse(any("person@example.test" in message.content for message in plan.job.messages))
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.filter(author_type="AI").count(), 1)
        self.assertFalse(Message.objects.filter(author_type="CONTACT").exists())
        claim = SiteEventLaunch.objects.get()
        self.assertEqual(claim.state, "sent")
        self.assertEqual(claim.response.text, "How can I help?")
        self.assertIsNone(claim.response.ai_reply_to_id)
        self.assertEqual(services.messages_payload(self.session, 0)["messages"][0]["id"], claim.response_id)
        self.assertEqual(NativeEffectReceipt.objects.count(), 1)

    def test_first_customer_input_suppresses_the_late_response_and_keeps_one_conversation(self):
        run = self.launch()
        def first_input(plan, **kwargs):
            with tenant_atomic(self.tenant):
                services.post_message(self.session, "I wrote first")
            return self.answer(plan, **kwargs)
        with patch("chatballs.webchat.proactive.run_turn_chat", side_effect=first_input):
            self.pump(run)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.filter(author_type="CONTACT").count(), 1)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
        self.assertEqual(SiteEventLaunch.objects.get().state, "suppressed")

    def test_recovery_after_domain_commit_before_checkpoint_does_not_call_model_again(self):
        run = self.launch()
        with patch("chatballs.webchat.proactive.run_turn_chat", side_effect=self.answer) as model:
            with patch("chatballs.integrations.execution.runner._commit", side_effect=RuntimeError("checkpoint failed")):
                with self.assertRaises(RuntimeError):
                    for _ in range(8):
                        run_one(self.tenant, run.public_id)
            self.assertEqual(Message.objects.filter(author_type="AI").count(), 1)
            self.assertEqual(NativeEffectReceipt.objects.count(), 1)
            with tenant_atomic(self.tenant):
                run.steps.update(lease_until=timezone.now() - timedelta(seconds=1), due_at=timezone.now())
            self.assertEqual(self.pump(run), "completed")
            self.assertEqual(model.call_count, 1)
        self.assertEqual(Message.objects.filter(author_type="AI").count(), 1)

    def test_revoked_rule_before_effect_cannot_call_model(self):
        run = self.launch()
        self.widget.integration.config = {"siteEvent": {**self.rule, "active": False}}
        self.widget.integration.save(update_fields=["config"])
        with patch("chatballs.webchat.proactive.run_turn_chat") as model:
            self.pump(run)
        model.assert_not_called()
        self.assertFalse(Message.objects.exists())
