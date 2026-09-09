"""Редирект не должен уводить скачивание туда, куда исходный адрес не пустили.

Политика исходящих проверяет адрес до запроса, но urllib сам ходит по
редиректам: ответ подставного провайдера возвращал 302 на внутренний адрес, и
хаб шёл туда своими руками. Проверка теперь висит на каждом Location.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from django.test import SimpleTestCase

from chatballs.conversations.transports.base import download_bytes
from chatballs.integrations.outbound import OutboundUrlRejected

PAYLOAD = b"file-content"


class _Handler(BaseHTTPRequestHandler):
    redirect_to = ""

    def do_GET(self):  # noqa: N802
        if self.path == "/file":
            self.send_response(200)
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            self.wfile.write(PAYLOAD)
            return
        self.send_response(302)
        self.send_header("Location", type(self).redirect_to)
        self.end_headers()

    def log_message(self, *args):  # тишина в выводе тестов
        return


class OutboundRedirectTests(SimpleTestCase):
    def setUp(self) -> None:
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.host, self.port = self.server.server_address
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        # Хост из base_url подключения владелец назвал сам — он разрешён даже
        # будучи внутренним. Именно так провайдер и живёт у self-hosted.
        self.allowed_host = "127.0.0.1"
        self.base = f"http://127.0.0.1:{self.port}"

    def test_direct_download_from_the_configured_host_works(self) -> None:
        data = download_bytes(f"{self.base}/file", allowed_host=self.allowed_host)

        self.assertEqual(data, PAYLOAD)

    def test_redirect_inside_the_configured_host_is_followed(self) -> None:
        _Handler.redirect_to = f"{self.base}/file"

        data = download_bytes(f"{self.base}/start", allowed_host=self.allowed_host)

        self.assertEqual(data, PAYLOAD)

    def test_redirect_to_a_foreign_internal_address_is_rejected(self) -> None:
        # Классическая цель SSRF: метаданные облачной машины.
        _Handler.redirect_to = "http://169.254.169.254/latest/meta-data/"

        with self.assertRaises(OutboundUrlRejected):
            download_bytes(f"{self.base}/start", allowed_host=self.allowed_host)

    def test_redirect_to_a_forbidden_scheme_is_rejected(self) -> None:
        _Handler.redirect_to = "file:///run/chatballs/secrets/secret_key"

        with self.assertRaises(OutboundUrlRejected):
            download_bytes(f"{self.base}/start", allowed_host=self.allowed_host)
