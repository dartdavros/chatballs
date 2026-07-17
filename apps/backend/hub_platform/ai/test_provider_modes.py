from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from hub_platform.ai.credits import ManagedAiQuotaExceeded
from hub_platform.ai.invocation import invoke_chat
from hub_platform.ai.models import CredentialMode, LlmInvocation, LlmInvocationStatus
from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.ai.provider.custom import CustomProvider
from hub_platform.ai.provider.custoai import CustoAIProvider
from hub_platform.ai.provider.openrouter import OpenRouterProvider
from hub_platform.ai.provider.routing import (
    IntegrationNotConfigured,
    resolve_provider_and_model,
)
from hub_platform.ai.tests import make_channel_with_agent
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import HumanUser, Organization
from hub_platform.integrations.models import IntegrationProvider
from hub_platform.integrations.services import IntegrationInput, create_integration
from hub_platform.products.models import Product
from hub_platform.subscriptions.errors import EntitlementRequired
from hub_platform.subscriptions.keys import EntitlementKey, QuotaKey
from hub_platform.subscriptions.models import (
    EntitlementDefinition,
    OverrideOperation,
    OverrideTarget,
    QuotaDefinition,
    Subscription,
    SubscriptionOverride,
    UsageCounter,
    UsagePeriodStatus,
)
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.testing import TenantAPIClient, system_tenant_context


class ProviderModeTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.context = system_tenant_context(self.organization)
        self.channel, self.agent = make_channel_with_agent(
            self.organization,
            code="provider-mode-sales",
            name="Provider mode — продажи",
            product=Product.objects.get(code="firepage"),
        )

    def _set_mode(self, mode: str) -> None:
        self.agent.credential_mode = mode
        self.agent.save(update_fields=["credential_mode"])

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
        self.channel.provider_integration = integration
        self.channel.save(update_fields=["provider_integration"])
        return integration

    def _exhaust_managed_quota(self) -> None:
        policy = get_effective_policy(self.context)
        quota = policy.quota(QuotaKey.MANAGED_AI_CREDITS)
        self.assertIsNotNone(quota)
        self.assertIsNotNone(quota.limit)
        subscription = Subscription.objects.get(organization=self.organization)
        period = subscription.usage_periods.get(status=UsagePeriodStatus.OPEN)
        definition = QuotaDefinition.objects.get(key=QuotaKey.MANAGED_AI_CREDITS)
        UsageCounter.objects.update_or_create(
            organization=self.organization,
            period=period,
            quota_definition=definition,
            defaults={
                "used_value": quota.limit * definition.accounting_scale,
                "reserved_value": 0,
            },
        )

    def test_custom_and_openrouter_resolve_with_runtime_model(self) -> None:
        for provider_code, provider_type in (
            (IntegrationProvider.CUSTOM, CustomProvider),
            (IntegrationProvider.OPENROUTER, OpenRouterProvider),
        ):
            with self.subTest(provider=provider_code):
                self.channel.provider_integration = None
                self.channel.save(update_fields=["provider_integration"])
                self._link_integration(provider=provider_code, default_model="runtime-model")
                provider, model = resolve_provider_and_model(
                    self.channel, fallback_model="agent-model"
                )
                self.assertIsInstance(provider, provider_type)
                self.assertEqual(model, "runtime-model")

    @override_settings(HUB_AI_PROVIDER="")
    def test_byok_uses_channel_integration(self) -> None:
        self._set_mode(CredentialMode.BYOK)
        integration = self._link_integration()
        from hub_platform.ai.provider.factory import get_provider

        provider = get_provider(channel=self.channel)
        self.assertIsInstance(provider, CustomProvider)
        self.assertEqual(provider.api_key, integration.secret)

    @override_settings(
        HUB_AI_PROVIDER="",
        HUB_CUSTOAI_API_KEY="platform-key",
        HUB_CUSTOAI_BASE_URL="https://ai.api.cloud.yandex.net/v1",
        HUB_CUSTOAI_MODEL="gpt://folder/yandexgpt-5.1/latest",
    )
    def test_custoai_uses_platform_credential(self) -> None:
        from hub_platform.ai.provider.factory import get_provider

        provider = get_provider(channel=self.channel)
        self.assertIsInstance(provider, CustoAIProvider)
        self.assertEqual(provider.api_key, "platform-key")
        self.assertEqual(provider.base_url, "https://ai.api.cloud.yandex.net/v1")
        self.assertEqual(provider.model, "gpt://folder/yandexgpt-5.1/latest")

    @override_settings(HUB_AI_PROVIDER="", HUB_CUSTOAI_API_KEY="platform-key")
    def test_no_implicit_fallback(self) -> None:
        from hub_platform.ai.provider.factory import get_provider

        self._set_mode(CredentialMode.BYOK)
        with self.assertRaises(IntegrationNotConfigured):
            get_provider(channel=self.channel)

    def test_openrouter_from_integration_removed(self) -> None:
        from hub_platform.ai.provider import factory

        self.assertFalse(hasattr(factory, "_openrouter_from_integration"))

    def test_custoai_always_uses_platform_model(self) -> None:
        provider = CustoAIProvider(
            api_key="platform-key",
            base_url="https://ai.api.cloud.yandex.net/v1",
            model="gpt://folder/yandexgpt-5.1/latest",
        )
        with mock.patch(
            "hub_platform.ai.provider.openai_http.chat_completions",
            return_value=ChatResult("ok", "gpt://folder/yandexgpt-5.1/latest", 2, 1),
        ) as chat:
            provider.chat(
                messages=[ChatMessage(role="user", content="hello")],
                model="caller-controlled-model",
            )
        self.assertEqual(
            chat.call_args.kwargs["model"], "gpt://folder/yandexgpt-5.1/latest"
        )

    @override_settings(HUB_AI_PROVIDER="")
    def test_default_model_read_in_runtime(self) -> None:
        self._set_mode(CredentialMode.BYOK)
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

    def test_byok_entitlement_enforced(self) -> None:
        self._set_mode(CredentialMode.BYOK)
        self._link_integration()
        definition = EntitlementDefinition.objects.get(key=EntitlementKey.BYOK_AI)
        SubscriptionOverride.objects.create(
            organization=self.organization,
            target=OverrideTarget.ENTITLEMENT,
            entitlement_definition=definition,
            operation=OverrideOperation.DISABLE,
            reason="test",
            starts_at=timezone.now(),
            created_by=self.owner,
        )
        with self.assertRaises(EntitlementRequired):
            invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="hello")],
                purpose="agent_chat",
            )

    def test_managed_quota_exhausted_blocks_custoai_call(self) -> None:
        self._exhaust_managed_quota()
        with mock.patch("hub_platform.ai.provider.local.LocalProvider.chat") as chat:
            with self.assertRaises(ManagedAiQuotaExceeded):
                invoke_chat(
                    channel=self.channel,
                    messages=[ChatMessage(role="user", content="hello")],
                    purpose="agent_chat",
                )
        chat.assert_not_called()
        blocked = LlmInvocation.objects.get(status=LlmInvocationStatus.BLOCKED)
        self.assertIn("достижения лимита Managed AI credits", blocked.error)

    def test_byok_works_when_managed_exhausted(self) -> None:
        self._exhaust_managed_quota()
        self._set_mode(CredentialMode.BYOK)
        self._link_integration()
        result = invoke_chat(
            channel=self.channel,
            messages=[ChatMessage(role="user", content="hello")],
            purpose="agent_chat",
        )
        self.assertTrue(result.text)

    def test_credential_mode_round_trips_api(self) -> None:
        integration = self._link_integration()
        client = TenantAPIClient()
        client.login(username="owner@edevs.tech", password="temporary-password")
        response = client.patch(
            f"/api/v1/ai/agents/{self.agent.id}/update/",
            {
                "credentialMode": CredentialMode.BYOK,
                "providerIntegrationId": integration.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent"]["credentialMode"], CredentialMode.BYOK)
        self.assertEqual(
            response.json()["agent"]["channel"]["providerIntegrationId"], integration.id
        )
