"""Адаптер Битрикс24: подключение входящим вебхуком и готовый сценарий.

Ссылка вебхука — и адрес портала, и секрет доступа: хранится зашифрованно,
после сохранения не показывается. Проверка вызывает метод ``scope`` — только
читает, какие разрешения выданы вебхуку; лиды и другие записи не создаются.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chatballs.integrations.adapters.bitrix24.operations import (
    entity_fields,
    entity_operations,
    service_operations,
)
from chatballs.integrations.adapters.bitrix24.references import references
from chatballs.integrations.adapters.bitrix24.synchronization import (
    binding as synchronization_binding,
)
from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    CheckDescriptor,
    EntityDescriptor,
    ErrorText,
    HelpBlock,
    LookupDescriptor,
    LookupItem,
    OperationResult,
    Presentation,
    ScenarioTemplate,
    TemplateStep,
    Unsupported,
)
from chatballs.integrations.adapters.schema import TypeSpec

# Телефон и почта в Битрикс24 — список значений с типом.
_MULTIFIELD = {"transform": "list.of_object@1", "args": {"key": "VALUE", "extra": {"VALUE_TYPE": "WORK"}}}

# Без доступа к CRM подключение бесполезно; право на пользователей нужно
# готовому сценарию (справочник ответственных) и объявлено в нём самом.
REQUIRED_SCOPES = frozenset({"crm"})
WEBHOOK_PATTERN = r"https://[^/\s]+/rest/\d+/[^/\s]+/?"


def missing_scope(result: OperationResult) -> str | None:
    granted = {str(item) for item in result.data} if isinstance(result.data, list) else set()
    return None if REQUIRED_SCOPES <= granted else "crm_access_missing"


def _users(data: Any) -> list[LookupItem]:
    rows = data if isinstance(data, list) else []
    items = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("ID"):
            continue
        name = " ".join(part.strip() for key in ("NAME", "SECOND_NAME", "LAST_NAME")
                        if isinstance(part := row.get(key), str) and part.strip())
        email = row.get("EMAIL")
        email = email.strip() if isinstance(email, str) else ""
        items.append(LookupItem(value=str(row["ID"]), label=name or email or str(row["ID"])))
    return items


def _stages(data: Any) -> list[LookupItem]:
    rows = data if isinstance(data, list) else []
    return [
        LookupItem(value=str(row["STATUS_ID"]), label=str(row.get("NAME") or row["STATUS_ID"]))
        for row in rows
        if isinstance(row, dict) and row.get("STATUS_ID")
    ]


WEBHOOK = AuthMethod(
    key="webhook",
    extension="secret_url@1",
    title_key="services.bitrix24.access_webhook",
    access_label_key="services.bitrix24.access_webhook_label",
    saved_label_key="services.bitrix24.access_webhook_saved",
    note_key="services.bitrix24.check_note",
    fields=TypeSpec(
        "object",
        properties=(
            (
                "url",
                TypeSpec(
                    "string",
                    title_key="services.bitrix24.webhook_url",
                    placeholder_key="services.bitrix24.webhook_url_placeholder",
                    hint_key="services.bitrix24.webhook_url_hint",
                    pattern=WEBHOOK_PATTERN,
                    pattern_error_key="services.bitrix24.webhook_url_invalid",
                    required=True,
                    secret=True,
                    control="url@1",
                ),
            ),
        ),
    ),
    check=CheckDescriptor(operation="scope.get", note_key="services.bitrix24.check_note", interpret=missing_scope),
)

CREATE_LEAD = ScenarioTemplate(
    key="create_lead_from_conversation",
    version=1,
    title_key="services.bitrix24.preset_lead_title",
    purpose_key="services.bitrix24.preset_lead_purpose",
    required_permissions=("crm", "user"),
    triggers=({"kind": "staff"},),
    conditions=(
        {"kind": "context_present", "path": "contact"},
        {"kind": "no_link", "entity": "lead"},
    ),
    parameters=TypeSpec(
        "object",
        properties=(
            ("owner", TypeSpec("lookup", lookup="users", title_key="services.bitrix24.field_owner", required=True)),
            ("stage", TypeSpec("lookup", lookup="lead_stages", title_key="services.bitrix24.field_stage", required=True)),
        ),
    ),
    steps=(
        TemplateStep(
            id="create_lead",
            title_key="services.bitrix24.op_lead_create",
            target="service:lead.create",
            inputs={
                "fields": {
                    "TITLE": {"source": "input", "name": "title", "title_key": "services.bitrix24.preset_lead_input_title"},
                    "NAME": {"source": "context", "path": "contact.name"},
                    "PHONE": {"source": "context", "path": "contact.phone", **_MULTIFIELD},
                    "EMAIL": {"source": "context", "path": "contact.email", **_MULTIFIELD},
                    "ASSIGNED_BY_ID": {"source": "parameter", "name": "owner"},
                    "STATUS_ID": {"source": "parameter", "name": "stage"},
                }
            },
        ),
        TemplateStep(
            id="link_lead",
            title_key="services.bitrix24.preset_lead_link_step",
            target="chatballs:entity_link.create",
            inputs={"entity": "lead", "external_id": {"source": "step", "step": "create_lead", "field": "", "transform": "text.stringify@1"}},
        ),
    ),
)

ADAPTER = AdapterDescriptor(
    key="bitrix24",
    contract_version=1,
    entities=tuple(EntityDescriptor(key=entity, title_key=f"services.bitrix24.entity_{entity}", fields=entity_fields(entity),
                                  native_entities=("contact",) if entity == "contact" else ("conversation",), references=references(entity),
                                  synchronization=synchronization_binding(entity))
                   for entity in ("lead", "contact", "deal")),
    package_dir=str(Path(__file__).parent),
    presentation=Presentation(
        title_key="services.bitrix24.title",
        about_key="services.bitrix24.about",
        connect_lead_key="services.bitrix24.connect_lead",
        logo_light="logos/light.svg",
        logo_dark="logos/dark.svg",
        host_label_key="services.bitrix24.host_label",
        help=HelpBlock(
            title_key="services.bitrix24.help_title",
            steps=("services.bitrix24.help_step_open", "services.bitrix24.help_step_scope", "services.bitrix24.help_step_paste"),
            link_key="services.bitrix24.help_link",
            link_url_key="services.bitrix24.help_url",
        ),
    ),
    auth_methods=(WEBHOOK,),
    operations=tuple(
        [operation for entity in ("lead", "contact", "deal") for operation in entity_operations(entity)]
        + service_operations()
    ),
    lookups=(
        LookupDescriptor(key="users", title_key="services.bitrix24.field_owner", operation="user.list", items=_users,
                         arguments={"FILTER": {"ACTIVE": True}}),
        LookupDescriptor(key="lead_stages", title_key="services.bitrix24.field_stage", operation="lead_stage.list",
                         items=_stages, arguments={"filter": {"ENTITY_ID": "STATUS"}}),
    ),
    templates=(CREATE_LEAD,),
    unsupported=(Unsupported(capability="events", reason_key="services.bitrix24.events_unsupported"),),
    errors={
        "user_access_missing": ErrorText("services.bitrix24.error_users_title", "services.bitrix24.error_users_text"),
        "crm_access_missing": ErrorText("services.bitrix24.error_crm_title", "services.bitrix24.error_crm_text"),
        "invalid_link": ErrorText("services.bitrix24.error_link_title", "services.bitrix24.error_link_text"),
    },
)
