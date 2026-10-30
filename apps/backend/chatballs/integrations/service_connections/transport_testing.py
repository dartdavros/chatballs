"""Ответы внешнего сервиса в тестах API подключений.

Подменяется только последний шаг — отправка запроса защищённым транспортом:
API, реестр, проверка, шифрование и права работают как в установке. Сам
транспорт проверяют тесты adapters/test_http_adapter.py на живом сокете.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from unittest import mock

from chatballs.integrations.adapters.auth import OutboundRequest
from chatballs.integrations.adapters.transport import GuardedTransport, TransportResponse

Responder = Callable[[OutboundRequest], TransportResponse]


def json_response(payload, status: int = 200) -> TransportResponse:
    return TransportResponse(
        status=status, content_type="application/json", url="", body=json.dumps(payload).encode()
    )


class FakeService:
    """Отвечает по адресу запроса; запросы запоминает для проверок."""

    def __init__(self, test_case, routes: dict[str, Responder | TransportResponse] | None = None) -> None:
        self.routes: dict[str, Responder | TransportResponse] = dict(routes or {})
        self.requests: list[OutboundRequest] = []
        patcher = mock.patch.object(GuardedTransport, "send", self._send)
        patcher.start()
        test_case.addCleanup(patcher.stop)

    def _send(self, request: OutboundRequest, *, limits, store_file=None) -> TransportResponse:
        self.requests.append(request)
        path = request.url.split("?", 1)[0]
        answer = next((value for suffix, value in self.routes.items() if path.endswith(suffix)), None)
        if answer is None:
            return json_response({"error": "NOT_FOUND"}, status=404)
        return answer(request) if callable(answer) else answer
