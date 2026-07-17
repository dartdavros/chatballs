from unittest import mock

from django.test import TestCase

from hub_platform.ai.credits import MANAGED_AI_RULE_VERSION
from hub_platform.ai.invocation import invoke_chat
from hub_platform.ai.models import CredentialMode
from hub_platform.ai.provider.base import ChatMessage, ProviderError
from hub_platform.ai.tests import make_channel_with_agent
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.products.models import Product
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import UsageCounter, UsageLedgerEntry


class ManagedAiTokenAccountingTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel, self.agent = make_channel_with_agent(
            self.organization,
            code="managed-token-accounting",
            name="Managed token accounting",
            product=Product.objects.get(code="firepage"),
        )

    def test_actual_tokens_accumulate_without_per_call_rounding(self) -> None:
        for _ in range(2):
            result = invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="hello")],
                purpose="agent_chat",
            )
            self.assertEqual(result.total_tokens, 3)

        counter = UsageCounter.objects.get(
            organization=self.organization,
            quota_definition__key=QuotaKey.MANAGED_AI_CREDITS,
        )
        self.assertEqual(counter.used_value, 6)
        self.assertEqual(counter.reserved_value, 0)
        entries = UsageLedgerEntry.objects.filter(source="ai.managed_invocation")
        self.assertEqual(list(entries.values_list("quantity", flat=True)), [3, 3])
        self.assertTrue(all(entry.unit == "tokens" for entry in entries))
        self.assertTrue(all(entry.rule_version == MANAGED_AI_RULE_VERSION for entry in entries))
        self.assertTrue(all(entry.metadata["creditScaleTokens"] == 1000 for entry in entries))

    def test_provider_failure_releases_token_reservation(self) -> None:
        with mock.patch(
            "hub_platform.ai.provider.local.LocalProvider.chat",
            side_effect=ProviderError("provider unavailable"),
        ), self.assertRaises(ProviderError):
            invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="hello")],
                purpose="agent_chat",
            )
        counter = UsageCounter.objects.get(
            organization=self.organization,
            quota_definition__key=QuotaKey.MANAGED_AI_CREDITS,
        )
        self.assertEqual(counter.reserved_value, 0)
        self.assertFalse(UsageLedgerEntry.objects.filter(source="ai.managed_invocation").exists())

    def test_byok_does_not_use_managed_token_pool(self) -> None:
        self.agent.credential_mode = CredentialMode.BYOK
        self.agent.save(update_fields=["credential_mode"])
        with mock.patch(
            "hub_platform.ai.invocation.routing.resolve_model", return_value="byok-model"
        ):
            invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="hello")],
                purpose="agent_chat",
            )
        self.assertFalse(UsageLedgerEntry.objects.filter(source="ai.managed_invocation").exists())
