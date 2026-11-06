"""Операции REST API Битрикс24 через входящий вебхук.

Метод вызывается POST ``<адрес вебхука>/<метод>.json`` с JSON-телом; ответ —
``{"result": ...}``, ошибка — ``{"error": "...", "error_description": "..."}``.
Записи CRM описаны так, как их принимает Битрикс24 (поля в верхнем регистре),
без общей CRM-модели: неописанные поля портала передаются как есть.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial
from typing import Any

from chatballs.integrations.adapters.contracts import Effect, OperationDescriptor
from chatballs.integrations.adapters.http import HttpSpec, http_operation
from chatballs.integrations.adapters.initial_values import InitialValue
from chatballs.integrations.adapters.schema import TypeSpec

_ERRORS = {
    "insufficient_scope": "crm_access_missing",
    "ACCESS_DENIED": "crm_access_missing",
    "invalid_token": "invalid_link",
    "INVALID_CREDENTIALS": "invalid_link",
    "NO_AUTH_FOUND": "invalid_link",
    "expired_token": "invalid_link",
    "QUERY_LIMIT_EXCEEDED": "rate_limited",
    "ERROR_METHOD_NOT_FOUND": "rejected",
    "NOT_FOUND": "not_found",
}


def interpret(status: int, payload: Any, *, permission: str = "crm") -> str | None:
    """Код ошибки Битрикс24 из тела ответа; None — ошибки нет."""

    if isinstance(payload, dict) and payload.get("error"):
        if permission != "crm" and payload["error"] in ("insufficient_scope", "ACCESS_DENIED"):
            return "user_access_missing" if permission == "user" else "forbidden"
        return _ERRORS.get(str(payload["error"]), "rejected")
    return None


def _text(key: str, *, required: bool = False) -> TypeSpec:
    return TypeSpec("string", title_key=f"services.bitrix24.field_{key}", required=required)


_MULTIFIELD = TypeSpec(
    "array",
    items=TypeSpec(
        "object",
        properties=(("VALUE", TypeSpec("string", required=True, title_key="services.bitrix24.field_value")),
                    ("VALUE_TYPE", TypeSpec("string", title_key="services.bitrix24.field_value_type"))),
        open=True,
    ),
)


def entity_fields(entity: str) -> TypeSpec:
    common: list[tuple[str, TypeSpec]] = [
        ("TITLE", _text("title")),
        ("NAME", _text("name")),
        ("LAST_NAME", _text("last_name")),
        ("PHONE", TypeSpec("array", title_key="services.bitrix24.field_phone", items=_MULTIFIELD.items)),
        ("EMAIL", TypeSpec("array", title_key="services.bitrix24.field_email", items=_MULTIFIELD.items)),
        ("ASSIGNED_BY_ID", TypeSpec("lookup", lookup="users", title_key="services.bitrix24.field_owner")),
        ("COMMENTS", _text("comments")),
    ]
    if entity == "lead":
        common.append(("STATUS_ID", TypeSpec("lookup", lookup="lead_stages", title_key="services.bitrix24.field_stage")))
    if entity == "deal":
        common.append(("OPPORTUNITY", TypeSpec("number", title_key="services.bitrix24.field_amount")))
        common.append(("CATEGORY_ID", TypeSpec("integer", title_key="services.bitrix24.field_category")))
        common.append(("STAGE_ID", TypeSpec("string", title_key="services.bitrix24.field_stage")))
        common.append(("CONTACT_ID", TypeSpec("integer", title_key="services.bitrix24.field_contact")))
    if entity == "contact":
        common = [item for item in common if item[0] != "TITLE"]
    return TypeSpec("object", properties=tuple(common), open=True, required=True, title_key="services.bitrix24.field_fields")


_ID = ("id", TypeSpec("integer", title_key="services.bitrix24.field_id", required=True))
_RECORD = TypeSpec("object", open=True, nullable=True)
_LIST_INPUT = TypeSpec(
    "object",
    properties=(
        ("filter", TypeSpec("object", open=True, title_key="services.bitrix24.field_filter")),
        ("select", TypeSpec("array", items=TypeSpec("string"), title_key="services.bitrix24.field_select")),
        ("order", TypeSpec("object", open=True, title_key="services.bitrix24.field_order")),
        ("start", TypeSpec("integer", title_key="services.bitrix24.field_start")),
    ),
)


def _call(method: str, *, result: str = "result", permission: str = "crm") -> HttpSpec:
    return HttpSpec(method="POST", path=f"{method}.json", body="json", result=result, interpret=partial(interpret, permission=permission))


def entity_operations(entity: str) -> list[OperationDescriptor]:
    prefix = f"services.bitrix24.op_{entity}"
    method = f"crm.{entity}"
    result = replace(entity_fields(entity), required=False, nullable=True,
                     properties=(("ID", TypeSpec("string", title_key="services.bitrix24.field_id")),) + entity_fields(entity).properties)
    return [
        replace(http_operation(
            f"{entity}.create", title_key=f"{prefix}_create", effect=Effect.CREATE, permission_scope="crm",
            input=TypeSpec("object", properties=(("fields", entity_fields(entity)), ("params", TypeSpec("object", open=True, title_key="services.bitrix24.field_params")))),
            output=TypeSpec("integer"), spec=_call(f"{method}.add"), entity_kind=entity,
        ), initial_values=(
            InitialValue("fields.NAME", "contact.name"),
            InitialValue("fields.PHONE", "contact.phone", "list.of_object@1",
                         {"key": "VALUE", "extra": {"VALUE_TYPE": "WORK"}}),
            InitialValue("fields.EMAIL", "contact.email", "list.of_object@1",
                         {"key": "VALUE", "extra": {"VALUE_TYPE": "WORK"}}),
        ) if entity in {"lead", "contact"} else ()),
        http_operation(
            f"{entity}.get", title_key=f"{prefix}_get", effect=Effect.READ, permission_scope="crm",
            input=TypeSpec("object", properties=(_ID,)), output=result, spec=_call(f"{method}.get"),
        ),
        http_operation(
            f"{entity}.update", title_key=f"{prefix}_update", effect=Effect.UPDATE, permission_scope="crm",
            input=TypeSpec("object", properties=(_ID, ("fields", entity_fields(entity)))),
            output=TypeSpec("boolean"), spec=_call(f"{method}.update"),
        ),
        http_operation(
            f"{entity}.delete", title_key=f"{prefix}_delete", effect=Effect.DELETE, permission_scope="crm",
            input=TypeSpec("object", properties=(_ID,)), output=TypeSpec("boolean"), spec=_call(f"{method}.delete"),
        ),
        http_operation(
            f"{entity}.list", title_key=f"{prefix}_list", effect=Effect.SEARCH, permission_scope="crm",
            input=_LIST_INPUT, output=TypeSpec("array", items=replace(result, nullable=False)), spec=_call(f"{method}.list"),
        ),
    ]


def service_operations() -> list[OperationDescriptor]:
    return [
        http_operation(
            "scope.get", title_key="services.bitrix24.op_scope", effect=Effect.READ,
            input=TypeSpec("object"), output=TypeSpec("array", items=TypeSpec("string")), spec=_call("scope"),
        ),
        http_operation(
            "user.list", title_key="services.bitrix24.op_users", effect=Effect.READ, permission_scope="user",
            input=TypeSpec("object", properties=(("FILTER", TypeSpec("object", open=True)), ("start", TypeSpec("integer")))),
            output=TypeSpec("array", items=_RECORD), spec=_call("user.get", permission="user"),
        ),
        http_operation(
            "lead_stage.list", title_key="services.bitrix24.op_lead_stages", effect=Effect.READ, permission_scope="crm",
            input=TypeSpec("object", properties=(("filter", TypeSpec("object", open=True)),)),
            output=TypeSpec("array", items=_RECORD), spec=_call("crm.status.list"),
        ),
        http_operation(
            "batch", title_key="services.bitrix24.op_batch", effect=Effect.BATCH,
            input=TypeSpec(
                "object",
                properties=(("cmd", TypeSpec("object", open=True, required=True)), ("halt", TypeSpec("integer"))),
            ),
            output=_RECORD, spec=_call("batch"),
        ),
    ]
