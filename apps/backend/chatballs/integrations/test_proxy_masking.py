"""Пароль прокси не уходит наружу и не теряется при редактировании.

Секрет интеграции в ответе маскируется, а адрес прокси отдавался целиком —
вместе с ``user:pass@``. Его видит каждый, у кого есть право смотреть
интеграции, и он же оседает в логах и истории браузера.

Маскировать мало: форма отправляет конфигурацию целиком, поэтому замаскированное
значение сохранилось бы вместо настоящего пароля при правке соседнего поля.
"""

from __future__ import annotations

from django.test import TestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.integrations.models import IntegrationKind, IntegrationProvider
from chatballs.integrations.serializers import (
    PROXY_PASSWORD_MASK,
    integration_payload,
    mask_proxy_url,
    restore_proxy_password,
)
from chatballs.integrations.services import IntegrationInput, create_integration, update_integration
from chatballs.testing import system_tenant_context

PROXY = "socks5://proxy-user:s3cr3t-pass@proxy.example:1080"


class ProxyMaskTests(TestCase):
    def test_password_is_replaced_and_the_rest_is_kept(self) -> None:
        masked = mask_proxy_url(PROXY)

        self.assertNotIn("s3cr3t-pass", masked)
        self.assertIn("proxy-user", masked)
        self.assertIn("proxy.example:1080", masked)
        self.assertIn(PROXY_PASSWORD_MASK, masked)

    def test_proxy_without_password_is_untouched(self) -> None:
        self.assertEqual(
            mask_proxy_url("http://proxy.example:3128"), "http://proxy.example:3128"
        )

    def test_empty_stays_empty(self) -> None:
        self.assertEqual(mask_proxy_url(""), "")

    def test_mask_of_the_same_proxy_restores_the_stored_password(self) -> None:
        self.assertEqual(restore_proxy_password(mask_proxy_url(PROXY), PROXY), PROXY)

    def test_mask_of_another_host_is_not_restored(self) -> None:
        submitted = mask_proxy_url("socks5://proxy-user:other@elsewhere.example:1080")

        self.assertEqual(restore_proxy_password(submitted, PROXY), submitted)

    def test_new_password_replaces_the_stored_one(self) -> None:
        submitted = "socks5://proxy-user:brand-new@proxy.example:1080"

        self.assertEqual(restore_proxy_password(submitted, PROXY), submitted)


class ProxyPayloadTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(email="proxy-owner@example.com", password="Owner-Password-2026!")
        self.context = system_tenant_context(result.organization)
        self.integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="LLM",
                secret="sk-or-v1-secret-value",
                config={"baseUrl": "https://openrouter.ai/api/v1", "proxyUrl": PROXY},
            ),
        )

    def test_payload_never_carries_the_proxy_password(self) -> None:
        payload = integration_payload(self.integration)

        self.assertNotIn("s3cr3t-pass", str(payload))
        self.assertIn(PROXY_PASSWORD_MASK, payload["config"]["proxyUrl"])

    def test_stored_value_keeps_the_real_password(self) -> None:
        self.integration.refresh_from_db()

        self.assertEqual(self.integration.config["proxy_url"], PROXY)

    def test_editing_another_field_keeps_the_proxy_password(self) -> None:
        """Форма возвращает то, что ей отдали, — включая маску."""
        from chatballs.integrations.views import _keep_proxy_password

        submitted = {
            "baseUrl": "https://openrouter.ai/api/v1",
            "proxyUrl": integration_payload(self.integration)["config"]["proxyUrl"],
            "defaultModel": "openai/gpt-4o-mini",
        }
        restored = _keep_proxy_password(submitted, self.integration)

        updated = update_integration(
            context=self.context,
            integration=self.integration,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="LLM",
                secret=None,
                config=restored,
            ),
        )

        self.assertEqual(updated.config["proxy_url"], PROXY)
        self.assertEqual(updated.kind, IntegrationKind.LLM_PROVIDER)
