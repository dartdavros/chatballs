from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.ai.assistance_behavior_base import AssistanceBehaviorData
from chatballs.ai.execution_version import configuration_version
from chatballs.ai.external_agents.readiness import require_builtin
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.conversations.ai_turn_state import request_ai_turn
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.events.models import OutboxEvent


class ExternalAssistanceTests(AssistanceBehaviorData, TestCase):
    def test_explicit_assistance_keeps_its_own_builtin_provider(self):
        self.agent.execution_mode = "external"
        self.agent.save(update_fields=["execution_mode"])
        suggestion = self.generate(self.request())
        self.assertEqual(suggestion.status, "READY")
        with self.assertRaises(ValidationError):
            require_builtin(self.agent)
        self.agent.assistance_enabled = False
        with self.assertRaises(ValidationError):
            require_builtin(self.agent, assistance=True)


class ExecutionBoundaryTests(ConfigurationCase):
    def test_external_selection_never_schedules_builtin_turn(self):
        from chatballs.ai.external_agents.config_bindings import select_execution
        identifier = self.connect()["connection"]["id"]
        self.bind(identifier)
        select_execution(self.context, self.agent.pk, "external")
        contact = Contact.objects.create(organization=self.organization, name="Contact")
        conversation = Conversation.objects.create(organization=self.organization, channel=self.channel, contact=contact)
        message = Message.objects.create(conversation=conversation, author_type="CONTACT", text="Question")
        request_ai_turn(message=message, user_id="contact", context=self.context)
        self.assertFalse(OutboxEvent.objects.filter(event_type="conversation.ai_turn_requested").exists())

    def test_execution_mode_aba_changes_builtin_fingerprint(self):
        before = configuration_version(self.agent)
        for mode in ("external", "builtin"):
            self.agent.execution_mode = mode
            self.agent.save(update_fields=["execution_mode"])
        self.agent.refresh_from_db()
        self.assertNotEqual(configuration_version(self.agent), before)
