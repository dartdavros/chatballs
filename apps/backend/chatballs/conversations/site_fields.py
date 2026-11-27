"""Отображение значений сайта по действующей схеме подключения."""

from chatballs.conversations.models import ContactFieldValue
from chatballs.i18n import t
from chatballs.integrations.models import IntegrationProvider


def field_display(definition: dict, value: object, *, language: str | None = None) -> str:
    if value is None:
        return t("conversations.site_fields.empty", language=language)
    if definition["type"] == "boolean":
        return t("conversations.site_fields.yes" if value else "conversations.site_fields.no", language=language)
    if definition["type"] == "enum":
        option = next((item for item in definition.get("options", []) if item["value"] == value), None)
        return option["label"] if option else str(value)
    return str(value)


def site_fields_payload(contact, *, integration_id: int | None = None) -> list[dict]:
    rows = ContactFieldValue.objects.filter(
        organization_id=contact.organization_id, contact_id=contact.id,
        integration__provider=IntegrationProvider.WEB,
    ).select_related("integration").order_by("integration_id", "id")
    if integration_id is not None:
        rows = rows.filter(integration_id=integration_id)
    integrations = {}
    for row in rows:
        integration, values = integrations.setdefault(row.integration_id, (row.integration, {}))
        values[row.key] = row
    payload = []
    for integration, values in integrations.values():
        for definition in sorted(integration.config.get("fields", []), key=lambda item: item.get("order", 0)):
            row = values.get(definition["key"])
            if row is None:
                continue
            item = {
                "key": row.key, "label": definition["label"], "type": definition["type"],
                "value": row.value, "display": field_display(definition, row.value),
                "updatedAt": row.updated_at.isoformat(),
            }
            if definition["type"] == "enum":
                option = next((option for option in definition.get("options", []) if option["value"] == row.value), None)
                if option and option.get("color"):
                    item["color"] = option["color"]
            payload.append(item)
    return payload
