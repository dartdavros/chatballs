"""Независимо написанный адаптер для тестов расширяемости (SPEC-0037 R-30).

Сервис «Probe» не существует: модуль подключается только настройкой
``CHATBALLS_SERVICE_ADAPTERS`` в тестах. Он объявляет то, чего нет у
Битрикс24, — вход через OAuth, ключ API, долгую операцию с продолжением,
сверкой и отменой, события webhook и опроса, вложенные типы и файлы, — и
регистрируется без правок ядра и общих экранов.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    CheckDescriptor,
    Delivery,
    Effect,
    EventDescriptor,
    LookupDescriptor,
    LookupItem,
    Mode,
    OperationContext,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    Presentation,
    ResultState,
    RetryStrategy,
    ScenarioTemplate,
    TemplateStep,
)
from chatballs.integrations.adapters.http import HttpSpec, http_operation
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

ORDER = TypeSpec(
    "object",
    properties=(
        ("number", TypeSpec("string", required=True)),
        ("placed_on", TypeSpec("date")),
        ("status", TypeSpec("enum", options=(EnumOption("new", ""), EnumOption("paid", "")))),
        ("manager", TypeSpec("lookup", lookup="managers", nullable=True)),
        ("lines", TypeSpec("array", items=TypeSpec("object", properties=(("sku", TypeSpec("string", required=True)), ("qty", TypeSpec("integer")))))),
        ("invoice", TypeSpec("file", nullable=True)),
    ),
)


def _resume(context: OperationContext, operation: OperationDescriptor, continuation: dict[str, Any]) -> OperationResult:
    return OperationResult(ResultState.COMPLETED, data={"job": continuation.get("job")})


def _start_export(context: OperationContext, operation: OperationDescriptor, arguments: dict[str, Any]) -> OperationResult:
    return OperationResult(ResultState.PENDING, continuation={"job": "export-1"}, external_reference="export-1",
                           deadline=datetime.now(UTC) + timedelta(hours=1))


def _managers(data: Any) -> list[LookupItem]:
    return [LookupItem(value=row["id"], label=row["name"]) for row in data or []]


OPERATIONS: tuple[OperationDescriptor, ...] = (
    http_operation(
        "account.get", title_key="", effect=Effect.READ, input=TypeSpec("object"),
        output=TypeSpec("object", open=True), spec=HttpSpec(method="GET", path="account", body="none"),
    ),
    http_operation(
        "manager.list", title_key="", effect=Effect.READ, input=TypeSpec("object"),
        output=TypeSpec("array", items=TypeSpec("object", open=True)), spec=HttpSpec(method="GET", path="managers", body="none"),
    ),
    http_operation(
        "order.create", title_key="", effect=Effect.CREATE, input=ORDER, output=TypeSpec("object", open=True),
        spec=HttpSpec(method="POST", path="orders", idempotency_header="Idempotency-Key"),
    ),
    http_operation(
        "order.replace", title_key="", effect=Effect.UPDATE,
        input=TypeSpec("object", properties=(("id", TypeSpec("string", required=True)), ("order", ORDER))),
        output=TypeSpec("object", open=True), spec=HttpSpec(method="PUT", path="orders/{id}"),
    ),
    http_operation(
        "order.delete", title_key="", effect=Effect.DELETE,
        input=TypeSpec("object", properties=(("id", TypeSpec("string", required=True)),)),
        output=TypeSpec("object", open=True, nullable=True), spec=HttpSpec(method="DELETE", path="orders/{id}", body="none"),
    ),
    http_operation(
        "order.form", title_key="", effect=Effect.UPDATE, input=TypeSpec("object", open=True),
        output=TypeSpec("object", open=True), spec=HttpSpec(method="PATCH", path="orders/form", body="form"),
    ),
    http_operation(
        "invoice.download", title_key="", effect=Effect.READ,
        input=TypeSpec("object", properties=(("id", TypeSpec("string", required=True)),)),
        output=TypeSpec("file"), spec=HttpSpec(method="GET", path="invoices/{id}", body="none"),
    ),
    OperationDescriptor(
        key="export.run", title_key="", effect=Effect.OTHER, input=TypeSpec("object"), output=TypeSpec("object", open=True),
        mode=Mode.LONG, retry=RetryStrategy.RECONCILE, cancellable=True,
        handlers=OperationHandlers(execute=_start_export, resume=_resume, reconcile=_resume, cancel=_resume),
    ),
)

OAUTH = AuthMethod(
    key="oauth",
    extension="oauth2@1",
    title_key="",
    fields=TypeSpec("object", properties=(("base_url", TypeSpec("string", required=True, control="url@1")),)),
    check=CheckDescriptor(operation="account.get", note_key=""),
    options={
        "authorize_url": "https://login.probe.example.test/authorize",
        "token_url": "https://login.probe.example.test/token",
        "scopes": ["orders"],
    },
)

API_KEY = AuthMethod(
    key="api_key",
    extension="api_key@1",
    title_key="",
    fields=TypeSpec(
        "object",
        properties=(
            ("base_url", TypeSpec("string", required=True, control="url@1")),
            ("key", TypeSpec("string", required=True, secret=True, control="secret@1")),
        ),
    ),
    check=CheckDescriptor(operation="account.get", note_key=""),
    options={"name": "X-Probe-Key"},
)

# Без проверки: сохраняется «Не проверено».
UNCHECKED = AuthMethod(
    key="token",
    extension="bearer@1",
    title_key="",
    fields=TypeSpec(
        "object",
        properties=(
            ("base_url", TypeSpec("string", required=True)),
            ("token", TypeSpec("string", required=True, secret=True)),
        ),
    ),
)

ADAPTER = AdapterDescriptor(
    key="probe",
    contract_version=1,
    presentation=Presentation(
        title_key="", about_key="", connect_lead_key="", logo_light="", logo_dark="", host_label_key=""
    ),
    auth_methods=(OAUTH, API_KEY, UNCHECKED),
    operations=OPERATIONS,
    events=(
        EventDescriptor(key="order.paid", title_key="", payload=ORDER, delivery=Delivery.WEBHOOK, ingress=lambda *args: None),
        EventDescriptor(key="order.changed", title_key="", payload=ORDER, delivery=Delivery.POLL, poll=lambda *args: None),
    ),
    lookups=(LookupDescriptor(key="managers", title_key="", operation="manager.list", items=_managers),),
    templates=(
        ScenarioTemplate(
            key="register_order",
            version=1,
            title_key="",
            purpose_key="",
            parameters=TypeSpec("object", properties=(("manager", TypeSpec("lookup", lookup="managers", required=True)),)),
            steps=(TemplateStep(id="create", title_key="", target="service:order.create"),),
        ),
    ),
)
