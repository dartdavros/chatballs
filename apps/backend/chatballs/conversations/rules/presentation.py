"""Rule display contract shared by HTTP and scenario operations."""

from chatballs.conversations.rules.catalog import CATALOG, EDITABLE_FIELDS
from chatballs.conversations.rules.deadline_text import placeholder
from chatballs.conversations.rules.models import MAX_DELAY_MINUTES, MAX_TEXT_LENGTH, HandlingRule


def rule_payload(rule: HandlingRule) -> dict[str, object]:
    spec = CATALOG[rule.kind]
    author = rule.updated_by
    return {
        "kind": rule.kind,
        "version": rule.version,
        **{api: getattr(rule, field) for field, api in EDITABLE_FIELDS.items()},
        "updatedAt": rule.updated_at.isoformat() if rule.updated_at else None,
        "updatedBy": (author.full_name or author.email) if author else "",
        # Что у этого правила вообще настраивается: интерфейсу незачем знать
        # каталог наизусть и нельзя предлагать то, чего сервер не примет.
        "catalog": {
            "conditions": sorted(spec.conditions),
            "recipients": sorted(spec.recipients),
            "requiresText": spec.requires_text,
            "maxDelayMinutes": MAX_DELAY_MINUTES,
            "maxTextLength": MAX_TEXT_LENGTH,
            "deadlinePlaceholder": placeholder() if spec.requires_text else "",
        },
    }
