"""Демо-провайдер: живой AI без ключей — ответы по знаниям, передача оператору."""

from django.test import TestCase

from chatballs.ai.provider.base import ChatMessage
from chatballs.ai.provider.demo import DemoProvider
from chatballs.ai.provider.routing import _provider_from_integration
from chatballs.ai.runtime import HANDOFF_TOKEN
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider, IntegrationStatus
from chatballs.integrations.services import (
    IntegrationInput,
    create_integration,
    # Алиас обязателен: имя test_* на уровне модуля pytest собирает как тест
    # и падает на ненайденных фикстурах (как в integrations/tests.py).
    test_integration as run_integration_test,
)
from chatballs.testing import system_tenant_context

KNOWLEDGE = (
    "Отвечай только на основе этих знаний:\n"
    "Пошив занимает 5–7 рабочих дней после оплаты. Доставка по России — СДЭК, 3–5 рабочих дней. "
    "Курьер по Санкт-Петербургу звонит за час.\n"
    "Возврат готовых изделий возможен в течение 14 дней."
)


class DemoProviderTests(TestCase):
    def test_answers_from_knowledge_without_handoff(self) -> None:
        result = DemoProvider().chat(
            messages=[
                ChatMessage(role="system", content=KNOWLEDGE),
                ChatMessage(role="user", content="Сколько идёт доставка по России?"),
            ],
            model="demo",
        )
        self.assertIn("СДЭК", result.text)
        self.assertNotIn(HANDOFF_TOKEN, result.text)
        self.assertGreater(result.prompt_tokens, 0)

    def test_unknown_question_hands_off(self) -> None:
        result = DemoProvider().chat(
            messages=[
                ChatMessage(role="system", content=KNOWLEDGE),
                ChatMessage(role="user", content="Есть ли у вас парковка для велосипедов?"),
            ],
            model="demo",
        )
        self.assertIn(HANDOFF_TOKEN, result.text)

    def test_request_for_human_hands_off_even_with_knowledge(self) -> None:
        result = DemoProvider().chat(
            messages=[
                ChatMessage(role="system", content=KNOWLEDGE),
                ChatMessage(role="user", content="Хочу оформить возврат, позовите человека"),
            ],
            model="demo",
        )
        self.assertIn("14 дней", result.text)
        self.assertIn(HANDOFF_TOKEN, result.text)

    def test_embeddings_are_deterministic(self) -> None:
        first, second = DemoProvider().embed(texts=["шторы", "шторы"], model="demo")
        self.assertEqual(first.vector, second.vector)


class DemoIntegrationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.context = system_tenant_context(self.organization)

    def test_demo_integration_needs_no_key_and_checks_ok(self) -> None:
        integration = create_integration(
            context=self.context,
            data=IntegrationInput(provider=IntegrationProvider.DEMO, name="Демо", secret="", config={}),
        )
        self.assertEqual(integration.kind, IntegrationKind.LLM_PROVIDER)
        self.assertEqual(integration.config["default_model"], "demo")
        self.assertTrue(integration.secret)
        checked = run_integration_test(context=self.context, integration=integration)
        self.assertEqual(checked.status, IntegrationStatus.OK)
        self.assertIsInstance(_provider_from_integration(Integration.objects.get(pk=integration.pk)), DemoProvider)
