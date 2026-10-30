"""HTTP-операции адаптера через защищённый транспорт (SPEC-0037 R-4, R-5, R-7, R-20).

Сервер теста слушает loopback; как в ``test_tool_client``, подменены DNS и
открытие сокета — клиент соединяется с проверенным «публичным» адресом.
"""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from django.test import TestCase, override_settings

from chatballs.identity import instance_settings
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations import tool_client
from chatballs.integrations.adapters import probe_testing
from chatballs.integrations.adapters.auth import ApiKeyAuth, BasicAuth, HmacSignatureAuth
from chatballs.integrations.adapters.contracts import Limits, OperationContext, ResultState
from chatballs.integrations.adapters.files import file_store
from chatballs.integrations.adapters.transport import GuardedTransport
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceFile,
)
from chatballs.integrations.tool_testing import PUBLIC_IP, fake_dns
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import system_tenant_context

DNS = {"api.probe.test": [PUBLIC_IP], "other.probe.test": ["93.184.216.40"], "intranet.probe.test": ["192.168.10.4"]}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    routes: dict[str, tuple[int, dict[str, str], bytes]] = {}
    seen: list[dict] = []

    def _serve(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        type(self).seen.append({"method": self.command, "path": self.path, "body": body, "headers": dict(self.headers.items())})
        status, headers, payload = type(self).routes.get(self.path.split("?")[0], (404, {"Content-Length": "0"}, b""))
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _serve  # noqa: N815

    def log_message(self, *args):
        return


def _json(payload, status: int = 200, extra: dict | None = None):
    body = json.dumps(payload).encode()
    return status, {"Content-Type": "application/json", "Content-Length": str(len(body)), **(extra or {})}, body


@override_settings(CHATBALLS_INSTANCE_SERVICE_HOSTS=[])
class HttpAdapterTests(TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        _Handler.routes, _Handler.seen = {}, []
        fake_dns(self, DNS)
        self.dialed: list[str] = []
        self._patch(tool_client, "_open_socket", self._dial)
        self._patch(instance_settings, "tools_private_network_allowed", lambda: False)
        bootstrap_owner(email="adapter-http@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.tenant = system_tenant_context(self.organization)
        with tenant_atomic(self.tenant):
            self.connection = Integration.objects.create(
                organization=self.organization, kind=IntegrationKind.SERVICE, provider=IntegrationProvider.ADAPTER, name="Probe"
            )

    def _patch(self, target, name, value) -> None:
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dial(self, address: str, port: int, timeout: float) -> socket.socket:
        self.dialed.append(address)
        return socket.create_connection(("127.0.0.1", self.port), timeout)

    def _context(self, auth=None, credentials=None, host="api.probe.test", **extra) -> OperationContext:
        return OperationContext(
            organization_id=self.organization.id,
            connection=self.connection,
            settings={"base_url": f"http://{host}:{self.port}/v1/"},
            credentials=credentials or {"key": "probe-secret"},
            auth=auth or ApiKeyAuth(),
            auth_options={"name": "X-Probe-Key"},
            transport=GuardedTransport(),
            **extra,
        )

    def _run(self, key: str, arguments: dict, context: OperationContext | None = None):
        operation = next(item for item in probe_testing.OPERATIONS if item.key == key)
        with tenant_atomic(self.tenant):
            return operation.handlers.execute(context or self._context(), operation, arguments)

    def test_write_methods_send_their_body_and_secret_only_to_the_service(self) -> None:
        _Handler.routes["/v1/orders/A-1"] = _json({"id": "A-1", "status": "paid"})

        result = self._run("order.replace", {"id": "A-1", "order": {"number": "A-1", "status": "paid"}})

        self.assertEqual(result.state, ResultState.COMPLETED)
        self.assertEqual(result.data, {"id": "A-1", "status": "paid"})
        seen = _Handler.seen[0]
        self.assertEqual((seen["method"], seen["path"]), ("PUT", "/v1/orders/A-1"))
        self.assertEqual(json.loads(seen["body"]), {"order": {"number": "A-1", "status": "paid"}})
        self.assertEqual(seen["headers"]["X-Probe-Key"], "probe-secret")
        self.assertEqual(self.dialed, [PUBLIC_IP])

    def test_delete_and_nested_form_bodies(self) -> None:
        _Handler.routes["/v1/orders/A-1"] = _json(None)
        _Handler.routes["/v1/orders/form"] = _json({"ok": True})

        deleted = self._run("order.delete", {"id": "A-1"})
        formed = self._run("order.form", {"fields": {"PHONE": [{"VALUE": "+7900"}], "OPENED": True}})

        self.assertEqual((deleted.state, formed.state), (ResultState.COMPLETED, ResultState.COMPLETED))
        self.assertEqual(_Handler.seen[0]["method"], "DELETE")
        self.assertEqual(_Handler.seen[1]["body"].decode(), "fields%5BPHONE%5D%5B0%5D%5BVALUE%5D=%2B7900&fields%5BOPENED%5D=Y")

    def test_idempotency_key_is_the_effect_key(self) -> None:
        _Handler.routes["/v1/orders"] = _json({"id": "A-2"}, status=201)

        self._run("order.create", {"number": "A-2"}, self._context(effect_key="run-1/step-2"))

        self.assertEqual(_Handler.seen[0]["headers"]["Idempotency-Key"], "run-1/step-2")

    def test_redirect_to_another_origin_drops_the_secret(self) -> None:
        _Handler.routes["/v1/account"] = (302, {"Location": f"http://other.probe.test:{self.port}/moved", "Content-Length": "0"}, b"")
        _Handler.routes["/moved"] = _json({"ok": True})

        result = self._run("account.get", {})

        self.assertEqual(result.state, ResultState.COMPLETED)
        self.assertNotIn("X-Probe-Key", _Handler.seen[1]["headers"])

    def test_private_network_address_is_refused_before_any_request(self) -> None:
        result = self._run("account.get", {}, self._context(host="intranet.probe.test"))

        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "address_internal"))
        self.assertEqual(_Handler.seen, [])

    def test_binary_response_goes_to_the_file_storage(self) -> None:
        pdf = b"%PDF-1.7 " + b"x" * 4096
        _Handler.routes["/v1/invoices/7"] = (200, {"Content-Type": "application/pdf", "Content-Length": str(len(pdf))}, pdf)
        context = self._context(store_file=file_store(context=self.tenant, integration=self.connection))

        result = self._run("invoice.download", {"id": "7"}, context)

        self.assertEqual(result.state, ResultState.COMPLETED)
        with tenant_atomic(self.tenant):
            stored = ServiceFile.objects.get(public_id=result.data["fileId"])
            with stored.file.open("rb") as stream:
                self.assertEqual(stream.read(), pdf)
        self.assertEqual((stored.content_type, stored.size), ("application/pdf", len(pdf)))

    def test_binary_response_without_storage_is_refused(self) -> None:
        _Handler.routes["/v1/invoices/7"] = (200, {"Content-Type": "application/pdf", "Content-Length": "3"}, b"pdf")

        result = self._run("invoice.download", {"id": "7"})

        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "too_large"))

    def test_lost_answer_of_a_write_is_unknown_and_of_a_read_is_a_failure(self) -> None:
        def drop(*args, **kwargs):
            raise TimeoutError

        with mock.patch.object(GuardedTransport, "send", drop):
            written = self._run("order.create", {"number": "A-3"})
            read = self._run("account.get", {})

        self.assertEqual((written.state, written.error_code), (ResultState.UNKNOWN, "no_response"))
        self.assertEqual((read.state, read.error_code), (ResultState.FAILED, "no_response"))

    def test_refused_connection_of_a_write_is_a_failure_not_unknown(self) -> None:
        def refuse(address: str, port: int, timeout: float) -> socket.socket:
            raise ConnectionRefusedError

        with mock.patch.object(tool_client, "_open_socket", refuse):
            result = self._run("order.create", {"number": "A-4"})

        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "unreachable"))

    def test_rate_limit_reports_retry_after(self) -> None:
        _Handler.routes["/v1/account"] = _json({"error": "slow down"}, status=429, extra={"Retry-After": "30"})

        result = self._run("account.get", {})

        self.assertEqual((result.state, result.error_code, result.retry_after_seconds), (ResultState.FAILED, "rate_limited", 30.0))

    def test_basic_and_signature_extensions_add_their_headers(self) -> None:
        _Handler.routes["/v1/account"] = _json({})

        self._run("account.get", {}, self._context(auth=BasicAuth(), credentials={"username": "u", "password": "p"}))
        self._run("account.get", {}, self._context(auth=HmacSignatureAuth(), credentials={"secret": "s"}))

        self.assertEqual(_Handler.seen[0]["headers"]["Authorization"], "Basic dTpw")
        self.assertRegex(_Handler.seen[1]["headers"]["X-Signature"], r"^[0-9a-f]{64}$")

    def test_limits_bound_the_inline_answer(self) -> None:
        big = b'{"a":"' + b"x" * 2048 + b'"}'
        _Handler.routes["/v1/account"] = (200, {"Content-Type": "application/json", "Content-Length": str(len(big))}, big)
        operation = next(item for item in probe_testing.OPERATIONS if item.key == "account.get")
        small = replace(operation, limits=Limits(max_response_bytes=512, max_file_bytes=1024))

        with tenant_atomic(self.tenant):
            result = small.handlers.execute(self._context(), small, {})

        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "too_large"))

    def test_unusable_answer_does_not_claim_that_a_write_failed(self) -> None:
        _Handler.routes["/v1/orders"] = _json({"id": "A-5", "details": "x" * 2048})
        operation = next(item for item in probe_testing.OPERATIONS if item.key == "order.create")
        small = replace(operation, limits=Limits(max_response_bytes=512, max_file_bytes=1024))
        with tenant_atomic(self.tenant):
            result = small.handlers.execute(self._context(), small, {"number": "A-5"})
        self.assertEqual((result.state, result.error_code), (ResultState.UNKNOWN, "too_large"))
