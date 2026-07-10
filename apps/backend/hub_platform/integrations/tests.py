import json
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.integrations import checks
from hub_platform.integrations.models import Integration, IntegrationProvider, IntegrationStatus
from hub_platform.integrations.serializers import integration_payload
from hub_platform.integrations.services import IntegrationInput, create_integration, update_integration


def _fake_response(status: int, body: dict):
    response = mock.MagicMock()
    response.status = status
    response.read.return_value = json.dumps(body).encode("utf-8")
    return response


class ProxyConfigTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")

    def test_proxy_url_is_persisted_in_config(self) -> None:
        integration = create_integration(
            organization=self.organization,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="OpenRouter",
                secret="sk-test",
                config={"baseUrl": "https://openrouter.ai/api/v1", "proxyUrl": "http://user:pass@host:8080"},
            ),
        )
        self.assertEqual(integration.config["proxy_url"], "http://user:pass@host:8080")

    def test_update_clears_proxy_when_empty(self) -> None:
        integration = create_integration(
            organization=self.organization,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="OpenRouter",
                secret="sk-test",
                config={"proxyUrl": "http://host:8080"},
            ),
        )
        updated = update_integration(
            integration=integration,
            data=IntegrationInput(provider=IntegrationProvider.OPENROUTER, name="OpenRouter", config={"proxyUrl": ""}),
        )
        self.assertNotIn("proxy_url", updated.config)

    def test_serializer_exposes_proxy_url(self) -> None:
        integration = create_integration(
            organization=self.organization,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="OpenRouter",
                secret="sk-test",
                config={"proxyUrl": "http://host:8080"},
            ),
        )
        self.assertEqual(integration_payload(integration)["config"]["proxyUrl"], "http://host:8080")


class CheckProxyTransportTests(TestCase):
    """check_* должны прокидывать proxy_url в HTTP-слой (ProxyHandler)."""

    def test_check_openrouter_uses_proxy(self) -> None:
        captured = {}

        def fake_build_opener(*handlers):
            captured["handlers"] = handlers
            opener = mock.MagicMock()
            ctx = mock.MagicMock()
            ctx.__enter__.return_value = _fake_response(200, {"data": {"label": "ok"}})
            opener.open.return_value = ctx
            return opener

        with mock.patch("hub_platform.integrations.checks.urllib.request.build_opener", side_effect=fake_build_opener):
            ok, detail, meta = checks.check_openrouter(secret="sk-test", base_url="", proxy_url="http://proxy:8080")

        self.assertTrue(ok)
        self.assertTrue(captured["handlers"], "ProxyHandler должен быть добавлен при заданном proxy_url")

    def test_check_openrouter_without_proxy_has_no_handler(self) -> None:
        captured = {}

        def fake_build_opener(*handlers):
            captured["handlers"] = handlers
            opener = mock.MagicMock()
            ctx = mock.MagicMock()
            ctx.__enter__.return_value = _fake_response(200, {"data": {"label": "ok"}})
            opener.open.return_value = ctx
            return opener

        with mock.patch("hub_platform.integrations.checks.urllib.request.build_opener", side_effect=fake_build_opener):
            checks.check_openrouter(secret="sk-test", base_url="", proxy_url="")

        self.assertEqual(captured["handlers"], (), "Без proxy_url ProxyHandler не добавляется")


class OpenRouterProviderProxyTests(TestCase):
    def test_provider_routes_through_proxy_handler(self) -> None:
        from hub_platform.ai.provider.openrouter import OpenRouterProvider

        captured = {}

        def fake_build_opener(*handlers):
            captured["handlers"] = handlers
            opener = mock.MagicMock()
            ctx = mock.MagicMock()
            ctx.__enter__.return_value = _fake_response(200, {"choices": [{"message": {"content": "ok"}}]})
            opener.open.return_value = ctx
            return opener

        provider = OpenRouterProvider(api_key="sk-test", base_url="https://openrouter.ai/api/v1", proxy_url="http://proxy:8080")
        with mock.patch("hub_platform.ai.provider.openrouter.urllib.request.build_opener", side_effect=fake_build_opener):
            result = provider.chat(messages=[], model="x")

        self.assertEqual(result.text, "ok")
        self.assertTrue(captured["handlers"], "ProxyHandler должен быть добавлен")
