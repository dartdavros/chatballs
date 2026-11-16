"""Native OpenAI configuration, routing and connectivity registration."""

from types import SimpleNamespace
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from chatballs.ai.provider.openai import OpenAIProvider
from chatballs.ai.provider.routing import provider_for_integration
from chatballs.ai.provider_selection import configure_agent_provider, configure_agent_transcription
from chatballs.integrations import checking, checks
from chatballs.integrations.models import (
    PROVIDER_KIND,
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.integrations.openai_urls import DEFAULT_OPENAI_BASE_URL, DEFAULT_OPENAI_MODEL
from chatballs.integrations.services import _normalized_config, _validate_provider
from chatballs.speech.contracts import capabilities


class OpenAIPresetTests(SimpleTestCase):
    def test_provider_is_registered_as_llm_with_default_settings(self):
        self.assertEqual(_validate_provider("OPENAI"), IntegrationProvider.OPENAI)
        self.assertEqual(PROVIDER_KIND[IntegrationProvider.OPENAI], IntegrationKind.LLM_PROVIDER)
        config = _normalized_config(IntegrationProvider.OPENAI, {})
        self.assertEqual(config, {"base_url": DEFAULT_OPENAI_BASE_URL, "default_model": DEFAULT_OPENAI_MODEL})

    def test_explicit_model_proxy_and_audio_settings_are_retained(self):
        config = _normalized_config(IntegrationProvider.OPENAI, {
            "baseUrl": DEFAULT_OPENAI_BASE_URL + "/responses/", "defaultModel": "gpt-4.1",
            "proxyUrl": "http://proxy.test:8080", "transcriptionModel": "whisper-1",
        })
        self.assertEqual(config, {"base_url": DEFAULT_OPENAI_BASE_URL, "default_model": "gpt-4.1",
                                  "proxy_url": "http://proxy.test:8080", "transcription_model": "whisper-1"})

    def test_invalid_base_url_is_still_rejected(self):
        with self.assertRaises(ValidationError):
            _normalized_config(IntegrationProvider.OPENAI, {"baseUrl": "file:///private/responses"})

    def test_runtime_uses_native_adapter_with_configured_credentials_and_timeout(self):
        integration = SimpleNamespace(provider=IntegrationProvider.OPENAI, secret="unit-test", config={"proxy_url": "http://proxy.test:8080"})
        provider = provider_for_integration(integration, timeout=13)
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual((provider.base_url, provider.api_key, provider.timeout, provider.proxy_url),
                         (DEFAULT_OPENAI_BASE_URL, "unit-test", 13, "http://proxy.test:8080"))

    def test_check_uses_models_endpoint_and_proxy_even_when_full_endpoint_was_saved(self):
        checker = checking._CHECKS[IntegrationProvider.OPENAI]
        for base in ("", DEFAULT_OPENAI_BASE_URL, DEFAULT_OPENAI_BASE_URL + "/responses"):
            with self.subTest(base=base), mock.patch.object(checks, "_get", return_value=(200, {"data": [{"id": DEFAULT_OPENAI_MODEL}]})) as get:
                ok, _, _ = checker(secret="unit-test", base_url=base, proxy_url="http://proxy.test:8080")
                self.assertTrue(ok)
                get.assert_called_once_with(DEFAULT_OPENAI_BASE_URL + "/models", headers={"Authorization": "Bearer unit-test"}, proxy_url="http://proxy.test:8080")

    def test_missing_key_does_not_make_a_network_request(self):
        with mock.patch.object(checks, "_get") as get:
            ok, _, _ = checking._CHECKS[IntegrationProvider.OPENAI](secret="", base_url="")
        self.assertFalse(ok)
        get.assert_not_called()

    def test_agent_and_transcription_selection_allow_openai_but_keep_tenant_filter(self):
        integration = SimpleNamespace(config={"default_model": DEFAULT_OPENAI_MODEL})
        context = SimpleNamespace(organization_id=42)
        with mock.patch.object(Integration.objects, "get", return_value=integration) as get:
            selection = configure_agent_provider(context=context, integration_id=7)
            self.assertEqual(selection.model, DEFAULT_OPENAI_MODEL)
            self.assertIn(IntegrationProvider.OPENAI, get.call_args.kwargs["provider__in"])
            self.assertEqual(get.call_args.kwargs["organization_id"], 42)
            self.assertIs(configure_agent_transcription(context=context, integration_id=7), integration)
            self.assertIn(IntegrationProvider.OPENAI, get.call_args.kwargs["provider__in"])
            self.assertEqual(get.call_args.kwargs["organization_id"], 42)
        self.assertTrue(capabilities("OPENAI").stt)
        self.assertEqual(capabilities("OPENAI").default_model, "whisper-1")
