"""IPv4 для A-записи домена портала берётся из адреса установки.

Раньше это была переменная окружения с обязательной проверкой при старте, а у
коробки её задавать негде — значение по умолчанию схлопывалось в 127.0.0.1, и
продукт печатал владельцу инструкцию «направьте домен на loopback».
"""

from __future__ import annotations

from django.test import TestCase, override_settings

from chatballs.identity.instance_settings import InstanceSettings, invalidate_cache
from chatballs.support_portals import public_address


class HelpPublicIpv4Tests(TestCase):
    def setUp(self) -> None:
        public_address.invalidate_cache()
        invalidate_cache()
        self.addCleanup(public_address.invalidate_cache)
        self.addCleanup(invalidate_cache)

    def _set_host(self, host: str) -> None:
        row = InstanceSettings.load()
        row.public_host = host
        row.save(update_fields=["public_host", "updated_at"])
        invalidate_cache()
        public_address.invalidate_cache()

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="")
    def test_ip_installation_address_is_used_as_is(self) -> None:
        self._set_host("203.0.113.10")

        self.assertEqual(public_address.help_public_ipv4(), "203.0.113.10")

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="")
    def test_no_address_yet_means_nothing_to_show(self) -> None:
        self._set_host("")

        self.assertEqual(public_address.help_public_ipv4(), "")

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="")
    def test_domain_installation_address_is_resolved(self) -> None:
        self._set_host("crm.example.test")
        original = public_address._resolve_a_record
        public_address._resolve_a_record = lambda host: "198.51.100.7"
        self.addCleanup(setattr, public_address, "_resolve_a_record", original)

        self.assertEqual(public_address.help_public_ipv4(), "198.51.100.7")

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="192.0.2.5")
    def test_explicit_setting_wins(self) -> None:
        self._set_host("203.0.113.10")

        self.assertEqual(public_address.help_public_ipv4(), "192.0.2.5")
