"""Only explicitly entered, permitted values from this test scope."""

from types import SimpleNamespace
from uuid import uuid4

from chatballs.ai.external_agents.custom_field_revisions import sources
from chatballs.ai.external_agents.custom_fields import field_value
from chatballs.ai.external_agents.json_payloads import dumps
from chatballs.ai.external_agents.payloads import open_payload, utc
from chatballs.webchat.field_values import BUILTIN_TYPES, validate_field_value


def validate(binding, value):
    if not isinstance(value, dict) or set(value) - {"standardFields", "customFields"}:
        raise ValueError("invalid_request")
    standard, custom = value.get("standardFields", {}), value.get("customFields", [])
    if not isinstance(standard, dict) or set(standard) - set(binding.standard_fields) or not isinstance(custom, list):
        raise ValueError("invalid_request")
    for key, item in standard.items():
        validate_field_value(item, {"type": BUILTIN_TYPES[key]})
    allowed = {(ref["sourceConnectionId"], ref["fieldId"]) for ref in binding.custom_fields}
    definitions = {(source.pk, field["id"]): field for source in sources(binding).filter(is_active=True)
                   for field in source.config.get("fields", [])}
    seen = set()
    for item in custom:
        if not isinstance(item, dict) or set(item) != {"sourceConnectionId", "fieldId", "value"}:
            raise ValueError("invalid_request")
        ref = item["sourceConnectionId"], item["fieldId"]
        if ref not in allowed or ref in seen or ref not in definitions:
            raise ValueError("invalid_request")
        seen.add(ref)
        validate_field_value(item["value"], definitions[ref])
    if len(dumps(value).encode()) > 65536:
        raise ValueError("invalid_request")
    return {"standardFields": standard, "customFields": custom}


def customer(row, binding):
    scope = row.conversation.external_test_scope
    saved = open_payload(scope.context_ciphertext)["values"]
    validate(binding, saved)
    custom = {(item["sourceConnectionId"], item["fieldId"]): item["value"]
              for item in saved["customFields"]}
    items = []
    allowed = {(item["sourceConnectionId"], item["fieldId"]) for item in binding.custom_fields}
    for source in sources(binding).filter(is_active=True):
        for field in source.config.get("fields", []):
            ref = source.pk, field["id"]
            if ref in allowed:
                value = SimpleNamespace(exact_value=dumps(custom[ref]), updated_at=scope.created_at) if ref in custom else None
                items.append(field_value(source, field, value))
    return {"id": str(scope.public_id), "fields": saved["standardFields"],
            "customFields": {"mode": "replace", "snapshotId": str(uuid4()),
                             "capturedAt": utc(scope.created_at), "items": items,
                             "scope": [{key: item[key] for key in ("sourceConnectionId", "fieldId")} for item in items]}}
