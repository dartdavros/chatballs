"""Разбор устройства и адреса для карточки «Активные сессии» (кадр P1)."""

from django.test import SimpleTestCase

from chatballs.identity.sessions import describe_agent, device_kind, mask_ip


class SessionMetaTests(SimpleTestCase):
    def test_describes_browser_and_platform(self) -> None:
        chrome_mac = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )
        safari_iphone = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
        )
        self.assertEqual(describe_agent(chrome_mac), "Chrome · macOS")
        self.assertEqual(describe_agent(safari_iphone), "Safari · iPhone")
        self.assertEqual(describe_agent(""), "Браузер")

    def test_picks_device_icon(self) -> None:
        self.assertEqual(device_kind("iPhone"), "phone")
        self.assertEqual(device_kind("Macintosh"), "laptop")
        self.assertEqual(device_kind("Windows NT 10.0"), "monitor")

    def test_masks_address(self) -> None:
        self.assertEqual(mask_ip("91.108.4.17"), "91.108.•.•")
        self.assertEqual(mask_ip("2a00:1450:4010:c07::8a"), "2a00:•")
        self.assertEqual(mask_ip(""), "")
