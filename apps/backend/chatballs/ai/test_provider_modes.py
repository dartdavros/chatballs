from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from chatballs.ai.invocation import invoke_chat
from chatballs.ai.provider.base import ChatMessage, ChatResult, ProviderError
from chatballs.ai.provider.custom import CustomProvider
from chatballs.ai.provider.factory import get_provider
from chatballs.ai.provider.local import LocalProvider
from chatballs.ai.provider.openrouter import OpenRouterProvider
from chatballs.ai.provider.routing import (
    IntegrationNotConfigured,
    resolve_model,
    resolve_provider_and_model,
)
from chatballs.ai.provider_selection import configure_agent_provider
from chatballs.ai.tests import make_channel_with_agent
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.services import IntegrationInput, create_integration
from chatballs.products.models import Product
from chatballs.testing import system_tenant_context


class ProviderModeTests(TestCase):
    """BYOK — единственный режим работы AI (ADR-HUB-0042 §3)."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.context = system_tenant_context(self.organization)
        self.channel, self.agent = make_channel_with_agent(
            self.organization,
            code="provider-mode-sales",
            name="Provider mode — продажи",
            product=Product.objects.get(code="site"),
        )

    def _link_integration(
        self,
        *,
        provider: str = IntegrationProvider.CUSTOM,
        default_model: str = "byok-model",
    ):
        base_url = (
            "https://api.example.com/v1"
            if provider == IntegrationProvider.CUSTOM
            else "https://openrouter.ai/api/v1"
        )
        integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=provider,
                name=f"BYOK {provider}",
                secret="sk-byok",
                config={"baseUrl": base_url, "defaultModel": default_model},
            ),
        )
        agent = self.channel.ai_agent
        agent.provider_integration = integration
        agent.save(update_fields=["provider_integration"])
        self.channel.refresh_from_db()
        return integration

    def test_custom_and_openrouter_resolve_with_runtime_model(self) -> None:
        for provider_code, provider_type in (
            (IntegrationProvider.CUSTOM, CustomProvider),
            (IntegrationProvider.OPENROUTER, OpenRouterProvider),
        ):
            with self.subTest(provider=provider_code):
                agent = self.channel.ai_agent
                agent.provider_integration = None
                agent.save(update_fields=["provider_integration"])
                self._link_integration(provider=provider_code, default_model="runtime-model")
                provider, model = resolve_provider_and_model(
                    self.channel, fallback_model="agent-model"
                )
                self.assertIsInstance(provider, provider_type)
                self.assertEqual(model, "runtime-model")

    @override_settings(CHATBALLS_AI_PROVIDER="")
    def test_byok_uses_agent_integration(self) -> None:
        integration = self._link_integration()

        provider = get_provider(channel=self.channel)
        self.assertIsInstance(provider, CustomProvider)
        self.assertEqual(provider.api_key, integration.secret)

    @override_settings(CHATBALLS_AI_PROVIDER="")
    def test_missing_integration_raises_integration_not_configured(self) -> None:
        with self.assertRaises(IntegrationNotConfigured):
            get_provider(channel=self.channel)

    def test_integration_not_configured_is_a_provider_error(self) -> None:
        # Отсутствие провайдера — штатное состояние, а не 500: вызывающий код
        # ловит ProviderError (индексация без эмбеддингов, handoff в диалогах).
        self.assertTrue(issubclass(IntegrationNotConfigured, ProviderError))

    @override_settings(CHATBALLS_AI_PROVIDER="test")
    def test_test_provider_setting_gives_local_provider(self) -> None:
        self.assertIsInstance(get_provider(channel=self.channel), LocalProvider)

    def test_openrouter_from_integration_removed(self) -> None:
        from chatballs.ai.provider import factory

        self.assertFalse(hasattr(factory, "_openrouter_from_integration"))

    @override_settings(CHATBALLS_AI_PROVIDER="")
    def test_default_model_read_in_runtime(self) -> None:
        self._link_integration(default_model="integration-model")
        with mock.patch.object(
            CustomProvider,
            "chat",
            return_value=ChatResult(
                text="ok",
                model="integration-model",
                prompt_tokens=1,
                completion_tokens=1,
            ),
        ) as chat:
            invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="hello")],
                purpose="agent_chat",
            )
        self.assertEqual(chat.call_args.kwargs["model"], "integration-model")


class AgentProviderOwnershipTests(TestCase):
    """SPEC-HUB-0027 §9 — провайдер живёт на агенте, канал не изменяется."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.context = system_tenant_context(self.organization)
        self.channel, self.agent = make_channel_with_agent(
            self.organization, code="byok", name="BYOK"
        )

    def _integration(self, *, default_model: str = "byok-model") -> Integration:
        return create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="BYOK",
                secret="sk-byok",
                config={"baseUrl": "https://openrouter.ai/api/v1", "defaultModel": default_model},
            ),
        )

    def test_no_integration_is_a_valid_draft_selection(self) -> None:
        # Агент без интеграции — валидный черновик; активация без провайдера
        # запрещена отдельно в set_agent_active.
        selection = configure_agent_provider(context=self.context, integration_id=None)
        self.assertIsNone(selection.integration)
        self.assertEqual(selection.model, "")

    def test_unknown_integration_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            configure_agent_provider(context=self.context, integration_id=999999)

    def test_selection_never_writes_to_the_channel(self) -> None:
        integration = self._integration()
        selection = configure_agent_provider(
            context=self.context,
            integration_id=integration.id,
        )

        self.assertEqual(selection.integration, integration)
        self.assertEqual(selection.model, "byok-model")
        self.channel.refresh_from_db()
        self.assertIsNone(self.channel.provider_integration_id)

    def test_runtime_falls_back_to_the_channel_for_unmigrated_rows(self) -> None:
        # Переходный fallback §9 шаг 3: агент пуст, провайдер ещё на канале.
        integration = self._integration(default_model="legacy-model")
        self.channel.provider_integration = integration
        self.channel.save(update_fields=["provider_integration"])
        self.agent.provider_integration = None
        self.agent.save(update_fields=["provider_integration"])
        self.channel.refresh_from_db()

        self.assertEqual(
            resolve_model(self.channel, fallback_model="agent-model"), "legacy-model"
        )

    def test_agent_integration_wins_over_the_channel(self) -> None:
        stale = self._integration(default_model="legacy-model")
        self.channel.provider_integration = stale
        self.channel.save(update_fields=["provider_integration"])
        current = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.CUSTOM,
                name="Current",
                secret="sk-current",
                config={"baseUrl": "https://api.example.com/v1", "defaultModel": "current-model"},
            ),
        )
        self.agent.provider_integration = current
        self.agent.save(update_fields=["provider_integration"])
        self.channel.refresh_from_db()

        self.assertEqual(
            resolve_model(self.channel, fallback_model="agent-model"), "current-model"
        )
