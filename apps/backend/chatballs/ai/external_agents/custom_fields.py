"""Read-only, complete per-contact projection; ai_access grants no export."""

from decimal import Decimal
from uuid import uuid4

from django.db.models import TextField
from django.db.models.functions import Cast
from django.utils import timezone

from chatballs.ai.external_agents.custom_field_revisions import sources
from chatballs.ai.external_agents.json_payloads import loads
from chatballs.ai.external_agents.payloads import utc
from chatballs.conversations.models import ContactFieldValue
from chatballs.webchat.field_values import validate_field_value


def field_value(source, definition, row):
    item = {"sourceConnectionId": str(source.pk), "fieldId": definition["id"],
            "key": definition["key"], "label": definition["label"], "type": definition["type"],
            "status": "unset", "value": None, "updatedAt": None}
    if definition["type"] == "enum":
        item["options"] = definition.get("options", [])
    if row is None:
        return item
    item["updatedAt"] = utc(row.updated_at)
    value = loads(row.exact_value)
    try:
        if value is None:
            raise ValueError("type")
        if definition["type"] == "number" and isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("type")
        else:
            value = validate_field_value(value, definition)
        item.update(status="set", value=value)
    except (ValueError, KeyError, TypeError) as error:
        reason = str(error)
        item.update(status="invalid", reasonCode=reason if reason in {
            "type", "option", "format", "length"} else "schema")
    return item


def snapshot(binding, contact):
    allowed = {(ref["sourceConnectionId"], ref["fieldId"]) for ref in binding.custom_fields}
    items = []
    for source in sources(binding).filter(is_active=True):
        values = {row.key: row for row in ContactFieldValue.objects.filter(
            organization_id=binding.organization_id, contact_id=contact.pk,
            contact__organization_id=binding.organization_id, integration=source,
        ).annotate(exact_value=Cast("value", TextField()))}
        definitions = sorted(source.config.get("fields", []),
                             key=lambda item: (item.get("order", 0), item["id"]))
        for definition in definitions:
            if (source.pk, definition["id"]) in allowed:
                items.append(field_value(source, definition, values.get(definition["key"])))
    scope = [{key: item[key] for key in ("sourceConnectionId", "fieldId")} for item in items]
    return {"mode": "replace", "snapshotId": str(uuid4()), "capturedAt": utc(timezone.now()),
            "scope": scope, "items": items}
