import json
import urllib.request
from unittest import mock

from django.test import TestCase

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.integrations import checks
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider, IntegrationStatus
from hub_platform.integrations.serializers import integration_payload
from hub_platform.integrations.services import (
    IntegrationInput,
    create_integration,
    test_integration as run_integration_test,
    update_integration,
)
from hub_platform.testing import system_tenant_context


def _fake_response(status: int, body: dict):
    response = mock.MagicMock()
    response.status = status
    response.read.return_value = json.dumps(body).encode("utf-8")
    return response


class WebIntegrationCheckTests(TestCase):
    """«Проверить» для Web-виджета: внешнего API нет — валидируем привязку к
    каналу и что виджет канала обслуживается именно этим подключением."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.context = system_tenant_context(self.organization)
        from hub_platform.channels.models import Channel

        self.channel = Channel.objects.create(organization=self.organization, code="edevs", name="Edevs — главный сайт")

    def _web(self, name: str, channel=None) -> Integration:
        return create_integration(
            context=self.context,
            data=IntegrationInput(provider=IntegrationProvider.WEB, name=name, channel_id=channel.id if channel else None),
        )

    def test_web_without_channel_fails(self) -> None:
        integration = run_integration_test(
            context=self.context, integration=self._web("Виджет", channel=None)
        )
        self.assertEqual(integration.status, IntegrationStatus.ERROR)
        self.assertIn("не привязано к каналу", integration.last_error)

    def test_web_bound_to_channel_is_ok(self) -> None:
        integration = run_integration_test(
            context=self.context, integration=self._web("Виджет", channel=self.channel)
        )
        self.assertEqual(integration.status, IntegrationStatus.OK)
        self.assertEqual(integration.last_error, "")

    def test_web_shadowed_by_another_connection_fails(self) -> None:
        # Два WEB-подключения на один канал: виджет обслуживает первое по сортировке.
        self._web("A-виджет", channel=self.channel)
        shadowed = run_integration_test(
            context=self.context, integration=self._web("B-виджет", channel=self.channel)
        )
        self.assertEqual(shadowed.status, IntegrationStatus.ERROR)
        self.assertIn("другое WEB-подключение", shadowed.last_error)


class ProxyConfigTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.context = system_tenant_context(self.organization)

    def test_proxy_url_is_persisted_in_config(self) -> None:
        integration = create_integration(
            context=self.context,
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
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="OpenRouter",
                secret="sk-test",
                config={"proxyUrl": "http://host:8080"},
            ),
        )
        updated = update_integration(
            context=self.context,
            integration=integration,
            data=IntegrationInput(provider=IntegrationProvider.OPENROUTER, name="OpenRouter", config={"proxyUrl": ""}),
        )
        self.assertNotIn("proxy_url", updated.config)

    def test_serializer_exposes_proxy_url(self) -> None:
        integration = create_integration(
            context=self.context,
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
        # После рефакторинга общий HTTP-слой живёт в openai_http (ADR-HUB-0033 §7):
        # мокаем именно его build_opener.
        with mock.patch("hub_platform.ai.provider.openai_http.build_opener", side_effect=_patched_opener(captured, {"choices": [{"message": {"content": "ok"}}], "model": "x"})):
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


class CustomIntegrationTests(TestCase):
    """Generic OpenAI-compatible BYOK provider (ADR-HUB-0034, SPEC-HUB-0024 §5).

    Covers the three required fields (endpoint, API key, model), runtime
    reading of the model field (SPEC #2, #5 — closing the as-built gap where
    «Модель по умолчанию» was decorative), and the connectivity check against
    an arbitrary OpenAI-compatible endpoint.
    """

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.context = system_tenant_context(self.organization)

    def test_custom_persists_endpoint_and_model(self) -> None:
        integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.CUSTOM,
                name="Мой провайдер",
                secret="sk-custom",
                config={
                    "baseUrl": "https://api.example.com/v1",
                    "defaultModel": "local-llama-3",
                },
            ),
        )
        # Модель — отдельное рабочее поле (ADR-HUB-0034 §4), читается в рантайме.
        self.assertEqual(integration.config["base_url"], "https://api.example.com/v1")
        self.assertEqual(integration.config["default_model"], "local-llama-3")
        self.assertEqual(integration.kind, IntegrationKind.LLM_PROVIDER)

    def test_custom_requires_model_free_text(self) -> None:
        # Каталога нет — модель обязательна к заполнению владельцем, но на уровне
        # нормализации конфига мы её сохраняем; пустое значение просто не сохраняется.
        integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.CUSTOM,
                name="Мой провайдер",
                secret="sk-custom",
                config={"baseUrl": "https://api.example.com/v1"},
            ),
        )
        self.assertNotIn("default_model", integration.config)

    def test_check_custom_lists_models_on_openai_shape(self) -> None:
        captured = {}
        with mock.patch("hub_platform.integrations.checks.build_opener", side_effect=_patched_opener(captured, {"data": [{"id": "local-llama-3"}]})):
            ok, detail, meta = checks.check_custom(secret="sk-custom", base_url="https://api.example.com/v1")

        self.assertTrue(ok)
        self.assertIn("1 моделей", detail)

    def test_check_custom_without_secret_fails(self) -> None:
        ok, detail, meta = checks.check_custom(secret="", base_url="https://api.example.com/v1")
        self.assertFalse(ok)
        self.assertEqual(detail, "Не указан API-ключ")

    def test_check_custom_without_base_url_fails(self) -> None:
        ok, detail, meta = checks.check_custom(secret="sk-custom", base_url="")
        self.assertFalse(ok)
        self.assertEqual(detail, "Не указан Base URL")

    def test_check_custom_non_200_is_error(self) -> None:
        response = mock.MagicMock()
        response.status = 401
        response.read.return_value = b"{}"
        opener = mock.MagicMock()
        ctx = mock.MagicMock()
        ctx.__enter__.return_value = response
        opener.open.return_value = ctx
        with mock.patch("hub_platform.integrations.checks.build_opener", return_value=opener):
            ok, detail, meta = checks.check_custom(secret="sk-custom", base_url="https://api.example.com/v1")

        self.assertFalse(ok)
        self.assertIn("401", detail)
