"""Политика исходящих запросов: куда хабу ходить можно, а куда нельзя."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.conversations.transports.base import download_bytes
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import IntegrationProvider
from chatballs.integrations.outbound import (
    HTTP_SCHEMES,
    PROXY_SCHEMES,
    OutboundUrlRejected,
    clean_config_url,
    ensure_downloadable,
)
from chatballs.integrations.proxy import build_opener
from chatballs.integrations.services import IntegrationInput, create_integration
from chatballs.testing import system_tenant_context


class ConfigUrlTests(TestCase):
    def test_scheme_outside_the_list_is_rejected(self) -> None:
        for value in ("file:///etc/passwd", "ftp://host/x", "javascript:1", "просто текст"):
            with self.subTest(value=value), self.assertRaises(OutboundUrlRejected):
                clean_config_url(value, schemes=HTTP_SCHEMES)

    def test_url_without_host_is_rejected(self) -> None:
        with self.assertRaises(OutboundUrlRejected):
            clean_config_url("http:///v1", schemes=HTTP_SCHEMES)

    def test_private_address_stays_allowed_in_configuration(self) -> None:
        # Self-hosted ставит рядом свой LLM-сервер или Bot API: запрет
        # приватных адресов в настройке сломал бы штатный сценарий.
        for value in ("http://localhost:11434/v1", "http://10.0.0.5:8080"):
            with self.subTest(value=value):
                self.assertEqual(clean_config_url(value, schemes=HTTP_SCHEMES), value)

    def test_proxy_accepts_socks_but_base_url_does_not(self) -> None:
        self.assertEqual(
            clean_config_url("socks5h://proxy:1080", schemes=PROXY_SCHEMES),
            "socks5h://proxy:1080",
        )
        with self.assertRaises(OutboundUrlRejected):
            clean_config_url("socks5h://proxy:1080", schemes=HTTP_SCHEMES)


class DownloadPolicyTests(TestCase):
    def test_only_http_schemes_are_downloadable(self) -> None:
        for url in (
            "file:///run/chatballs/secrets/secret_key",
            "ftp://host/x",
            "data:text/plain,x",
        ):
            with self.subTest(url=url), self.assertRaises(OutboundUrlRejected):
                ensure_downloadable(url)

    def test_internal_addresses_are_refused(self) -> None:
        for url in (
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8000/api/v1/health/",
            "http://10.0.0.5/x",
            "http://localhost/x",
        ):
            with self.subTest(url=url), self.assertRaises(OutboundUrlRejected):
                ensure_downloadable(url)

    def test_public_address_passes(self) -> None:
        ensure_downloadable("https://93.184.216.34/file.ogg")

    def test_configured_host_of_the_connection_is_allowed(self) -> None:
        # Владелец сам указал этот хост в base_url — значит, ходить туда велено.
        ensure_downloadable("http://10.0.0.5/file.ogg", allowed_host="10.0.0.5")
        with self.assertRaises(OutboundUrlRejected):
            ensure_downloadable("http://10.0.0.6/file.ogg", allowed_host="10.0.0.5")

    def test_proxy_takes_over_the_host_check(self) -> None:
        # До цели хаб идёт не сам, а через прокси владельца; при socks5h
        # локальный резолвер о ней вообще ничего не знает.
        ensure_downloadable("http://10.0.0.5/file.ogg", via_proxy=True)

    def test_download_bytes_refuses_local_files(self) -> None:
        with self.assertRaises(OutboundUrlRejected):
            download_bytes("file:///run/chatballs/secrets/secret_key")


class OpenerSchemeTests(TestCase):
    """Второй рубеж: даже в обход проверки схемы opener не откроет файл."""

    def test_opener_refuses_non_http_schemes(self) -> None:
        opener = build_opener("")
        for url in ("file:///etc/hostname", "ftp://example.com/x", "data:text/plain,x"):
            with self.subTest(url=url), self.assertRaises(OutboundUrlRejected):
                opener.open(url)


class IntegrationConfigTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="outbound-owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.context = system_tenant_context(self.organization)

    def test_base_url_with_file_scheme_is_refused_on_save(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            create_integration(
                context=self.context,
                data=IntegrationInput(
                    provider=IntegrationProvider.CUSTOM,
                    name="Свой LLM",
                    secret="key",
                    config={"baseUrl": "file:///etc/passwd", "defaultModel": "m"},
                ),
            )
        self.assertIn("Base URL", str(raised.exception))

    def test_proxy_url_scheme_is_validated(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            create_integration(
                context=self.context,
                data=IntegrationInput(
                    provider=IntegrationProvider.CUSTOM,
                    name="Свой LLM",
                    secret="key",
                    config={
                        "baseUrl": "https://llm.example.com/v1",
                        "defaultModel": "m",
                        "proxyUrl": "file:///etc/passwd",
                    },
                ),
            )
        self.assertIn("Proxy URL", str(raised.exception))
