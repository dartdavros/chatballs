"""SVG-логотип организации: принимается чистый, отклоняется опасный.

Логотип отдаётся с адреса приложения, поэтому SVG проверяется при загрузке
(скрипты, обработчики, внешние ссылки), а при отдаче получает защитные
заголовки как второй рубеж.
"""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.logo_svg import svg_is_safe
from chatballs.testing import TenantAPIClient

CLEAN_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 64 64">
  <defs><linearGradient id="g"><stop offset="0" stop-color="#1677ff"/><stop offset="1" stop-color="#003eb3"/></linearGradient></defs>
  <style>.mark { fill: url(#g); }</style>
  <circle class="mark" cx="32" cy="32" r="30"/>
  <use xlink:href="#mark"/>
</svg>
"""


class SvgSafetyTests(TestCase):
    def test_clean_svg_is_accepted(self) -> None:
        self.assertTrue(svg_is_safe(CLEAN_SVG))

    def test_dangerous_svg_is_rejected(self) -> None:
        samples = {
            "script": b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            "handler": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect/></svg>',
            "javascript href": b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="javascript:alert(1)"><rect/></a></svg>',
            "external image": b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/t.png"/></svg>',
            "foreignObject": b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div>x</div></foreignObject></svg>',
            "external css": b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://evil.example/a.css);</style></svg>',
            "style url": b'<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(http://evil.example/x)"/></svg>',
            "doctype entity": b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg"/>',
            "not svg": b'<html><body>hi</body></html>',
            "broken xml": b'<svg xmlns="http://www.w3.org/2000/svg"><rect></svg>',
        }
        for name, sample in samples.items():
            with self.subTest(name):
                self.assertFalse(svg_is_safe(sample))


class SvgLogoApiTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(email="svg-owner@example.com", password="temporary-password")
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def _upload(self, data: bytes):
        return self.client.post(
            "/api/v1/company/administration/logo/",
            {"file": SimpleUploadedFile("logo.svg", data, content_type="image/svg+xml")},
            format="multipart",
        )

    def test_svg_logo_round_trip_with_protective_headers(self) -> None:
        uploaded = self._upload(CLEAN_SVG)

        self.assertEqual(uploaded.status_code, 200, uploaded.content)
        downloaded = self.client.get("/api/v1/company/administration/logo/")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "image/svg+xml")
        self.assertIn("sandbox", downloaded["Content-Security-Policy"])
        self.assertEqual(downloaded["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(downloaded.streaming_content), CLEAN_SVG)

    def test_svg_with_script_is_refused_with_a_field_error(self) -> None:
        response = self._upload(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json()["errors"])
