"""HTTP-инструмент: сборка запроса и защита адреса (SPEC-0023 R-3, R-4, R-16)."""

from __future__ import annotations

import json
from unittest import mock

from chatballs.integrations import tool_client
from chatballs.integrations.external_server_testing import (
    DNS,
    TOKEN,
    ExternalServerTestCase,
    order_status,
)
from chatballs.integrations.http_tool import (
    ClientData,
    ToolArgumentsRejected,
    bound_arguments,
    build_request,
    call_http_tool,
    input_schema,
)
from chatballs.integrations.models import Integration
from chatballs.integrations.tool_network import ToolAddressRejected
from chatballs.integrations.tool_testing import PUBLIC_IP, fake_dns

ORDERS = "https://shop.example.test/api/orders/"
EMAIL = {"name": "email", "type": "string", "required": True, "source": {"type": "contact", "field": "email"}}
ORDER_NUMBER = {"name": "order_number", "type": "string", "location": "path"}


class HttpToolTestCase(ExternalServerTestCase):
    def _tool(self, **settings: object) -> Integration:
        response = self._create("HTTP", order_status(**settings))
        self.assertEqual(response.status_code, 201, response.content)
        return Integration.objects.get(id=response.json()["integration"]["id"])


class BuildRequestTests(HttpToolTestCase):
    def test_write_methods_preserve_method_and_encode_json(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                response = self._create("HTTP", order_status(
                    method=method, url="https://shop.example.test/api/orders",
                    parameters=[{"name": "state", "type": "string", "required": True, "location": "body"}],
                ), name=f"Change {method}")
                self.assertEqual(response.status_code, 201, response.content)
                tool = Integration.objects.get(id=response.json()["integration"]["id"])
                request = build_request(tool, {"state": "cancelled"}, {})
                self.assertEqual(request.method, method)
                self.assertEqual(json.loads(request.body), {"state": "cancelled"})

    def test_arguments_go_to_the_path_and_the_query(self) -> None:
        request = build_request(
            self._tool(), {"order_number": "A 10/482?x=1#y", "include_items": True}, {}
        )

        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url, f"{ORDERS}A%2010%2F482%3Fx%3D1%23y?include_items=true")
        self.assertIsNone(request.body)
        self.assertEqual(
            request.headers,
            {"Authorization": TOKEN, "X-Shop-Id": "obed-main", "Accept": "application/json, text/*"},
        )

    def test_optional_parameter_without_value_is_left_out(self) -> None:
        request = build_request(self._tool(), {"order_number": 10482, "include_items": ""}, {})

        self.assertEqual(request.url, f"{ORDERS}10482")

    def test_post_sends_body_parameters_as_json(self) -> None:
        tool = self._tool(
            method="POST",
            readOnly=True,
            url="https://shop.example.test/api/search?lang=ru",
            parameters=[
                {"name": "text", "type": "string", "required": True, "location": "body"},
                {"name": "max_price", "type": "number", "location": "body"},
                {"name": "in_stock", "type": "boolean", "location": "body"},
                {"name": "page", "type": "number", "location": "query"},
            ],
        )

        request = build_request(
            tool, {"text": "ноутбук & монтаж", "max_price": 80000, "in_stock": True, "page": 2.0}, {}
        )

        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url, "https://shop.example.test/api/search?lang=ru&page=2")
        self.assertEqual(
            json.loads(request.body),
            {"text": "ноутбук & монтаж", "max_price": 80000, "in_stock": True},
        )
        self.assertEqual(request.headers["Content-Type"], "application/json")

    def test_bound_parameter_is_hidden_from_the_model_and_set_by_the_server(self) -> None:
        tool = self._tool(parameters=[ORDER_NUMBER, EMAIL])
        client = ClientData(email="anna@example.test")

        self.assertEqual(
            input_schema(tool.config),
            {
                "type": "object",
                "properties": {"order_number": {"type": "string"}},
                "required": ["order_number"],
            },
        )
        bound = bound_arguments(tool.config, client)
        self.assertEqual(bound, {"email": "anna@example.test"})
        # Модель привязанный параметр не переопределит.
        request = build_request(tool, {"order_number": "7", "email": "other@example.test"}, bound)
        self.assertEqual(request.url, f"{ORDERS}7?email=anna%40example.test")

    def test_tool_without_a_required_bound_value_is_not_offered(self) -> None:
        tool = self._tool(parameters=[ORDER_NUMBER, EMAIL])
        client = ClientData(name="Анна")

        self.assertIsNone(bound_arguments(tool.config, client))
        # Необязательный параметр без значения просто не уходит в запрос.
        tool.config["parameters"][1]["required"] = False
        self.assertEqual(bound_arguments(tool.config, client), {})
        self.assertEqual(build_request(tool, {"order_number": "7"}, {}).url, f"{ORDERS}7")

    def test_arguments_that_do_not_fit_are_rejected(self) -> None:
        tool = self._tool()

        for arguments in (
            {},
            {"order_number": ""},
            {"order_number": ".."},
            {"order_number": ["7"]},
            {"order_number": "7", "include_items": "yes"},
            {"order_number": "7" * 2001},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ToolArgumentsRejected):
                build_request(tool, arguments, {})


class AddressInjectionTests(HttpToolTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.dialed: list[str] = []
        patcher = mock.patch.object(tool_client, "_open_socket", self._dial)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dial(self, address: str, port: int, timeout: float):
        self.dialed.append(address)
        raise ConnectionRefusedError

    def test_value_with_an_address_stays_inside_the_path(self) -> None:
        tool = self._tool()

        for value in ("@postgres:5432/", "//postgres/", "http://169.254.169.254/", "x/../../admin"):
            with self.subTest(value=value):
                self.dialed.clear()
                request = build_request(tool, {"order_number": value}, {})
                self.assertTrue(request.url.startswith(ORDERS), request.url)
                self.assertNotIn("/", request.url.removeprefix(ORDERS))
                self.assertNotIn("@", request.url)

                with self.assertRaises(ConnectionRefusedError):
                    call_http_tool(tool, {"order_number": value}, {}, timeout=5)
                self.assertEqual(self.dialed, [PUBLIC_IP])

    def test_parameter_cannot_choose_the_server(self) -> None:
        tool = self._tool()
        # Такой шаблон сохранение не пропустит; здесь он записан в обход проверки.
        tool.config["url"] = "http://{order_number}/latest/meta-data"
        tool.save(update_fields=["config"])

        for value in ("postgres", "169.254.169.254", "127.0.0.1", "192.168.1.20"):
            with self.subTest(value=value), self.assertRaises(ToolAddressRejected):
                call_http_tool(tool, {"order_number": value}, {}, timeout=5)
        self.assertEqual(self.dialed, [])

    def test_final_address_is_checked_by_the_client_policy(self) -> None:
        tool = self._tool()
        # Имя сервера после сохранения стало разрешаться во внутренний адрес.
        fake_dns(self, {**DNS, "shop.example.test": ["192.168.1.20"]})

        with self.assertRaises(ToolAddressRejected) as raised:
            call_http_tool(tool, {"order_number": "10482"}, {}, timeout=5)

        self.assertEqual(raised.exception.code, "internal")
        self.assertEqual(self.dialed, [])
