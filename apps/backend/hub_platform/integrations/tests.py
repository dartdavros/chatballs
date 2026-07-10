import json
import urllib.request
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


def _patched_opener(captured: dict, body: dict):
    def fake_build_opener(proxy_url):
        captured["proxy_url"] = proxy_url
        opener = mock.MagicMock()
        ctx = mock.MagicMock()
        ctx.__enter__.return_value = _fake_response(200, body)
        opener.open.return_value = ctx
        return opener

    return fake_build_opener


class CheckProxyTransportTests(TestCase):
    """check_* должны прокидывать proxy_url в единый opener (build_opener)."""

    def test_check_openrouter_uses_proxy(self) -> None:
        captured = {}
        with mock.patch("hub_platform.integrations.checks.build_opener", side_effect=_patched_opener(captured, {"data": {"label": "ok"}})):
            ok, detail, meta = checks.check_openrouter(secret="sk-test", base_url="", proxy_url="http://proxy:8080")

        self.assertTrue(ok)
        self.assertEqual(captured["proxy_url"], "http://proxy:8080")

    def test_check_openrouter_without_proxy_passes_empty(self) -> None:
        captured = {}
        with mock.patch("hub_platform.integrations.checks.build_opener", side_effect=_patched_opener(captured, {"data": {"label": "ok"}})):
            checks.check_openrouter(secret="sk-test", base_url="", proxy_url="")

        self.assertEqual(captured["proxy_url"], "")

    def test_check_openrouter_supports_socks_url(self) -> None:
        captured = {}
        with mock.patch("hub_platform.integrations.checks.build_opener", side_effect=_patched_opener(captured, {"data": {"label": "ok"}})):
            ok, detail, meta = checks.check_openrouter(secret="sk-test", base_url="", proxy_url="socks5://proxy:1080")

        self.assertTrue(ok)
        self.assertEqual(captured["proxy_url"], "socks5://proxy:1080")


class OpenRouterProviderProxyTests(TestCase):
    def test_provider_routes_through_proxy_handler(self) -> None:
        from hub_platform.ai.provider.openrouter import OpenRouterProvider

        captured = {}
        provider = OpenRouterProvider(api_key="sk-test", base_url="https://openrouter.ai/api/v1", proxy_url="http://proxy:8080")
        with mock.patch("hub_platform.ai.provider.openrouter.build_opener", side_effect=_patched_opener(captured, {"choices": [{"message": {"content": "ok"}}]})):
            result = provider.chat(messages=[], model="x")

        self.assertEqual(result.text, "ok")
        self.assertEqual(captured["proxy_url"], "http://proxy:8080")


class BuildOpenerSocksTests(TestCase):
    def test_http_scheme_uses_proxy_handler(self) -> None:
        from hub_platform.integrations.proxy import build_opener

        opener = build_opener("http://proxy:8080")
        self.assertTrue(any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers))

    def test_socks5_scheme_builds_socks_handler(self) -> None:
        from hub_platform.integrations.proxy import build_opener

        opener = build_opener("socks5://user:pass@host:1080")
        # PySocks установлен → handler строится без ошибок и не является ProxyHandler.
        self.assertFalse(any(isinstance(h, urllib.request.ProxyHandler) for h in opener.handlers))

    def test_socks_without_pysocks_raises_value_error(self) -> None:
        from hub_platform.integrations import proxy
        from hub_platform.integrations.proxy import build_opener

        with mock.patch.object(proxy, "_import_socks", side_effect=ValueError("no PySocks")):
            with self.assertRaises(ValueError):
                build_opener("socks5://host:1080")
