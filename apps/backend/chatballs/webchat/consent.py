"""Серверное подтверждение согласия, общее для речи и событий сайта."""

import hashlib
import json

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chatballs.i18n import customer_language, t
from chatballs.webchat.field_values import BUILTIN_TYPES, validate_field_value
from chatballs.webchat.pre_chat import pre_chat_payload


def current_version(widget) -> str:
    return str(widget.consent_config.get("consent_version") or "v1")


def form_revision(widget) -> str:
    config = widget.integration.config
    policy = {"form": pre_chat_payload(config), "fields": config.get("fields", [])}
    if config.get("answerPlaybackEnabled", False):
        policy["answerPlaybackDisclosure"] = 1
    encoded = json.dumps(policy, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _reject(widget, key: str) -> None:
    raise ValidationError({"detail": t(key, language=customer_language(widget.organization))})


def validate_acceptance(widget, version: object, fields: object) -> None:
    """Данные сайта и сохранённый контакт не подменяют обязательную форму."""
    if not isinstance(version, str) or version != current_version(widget):
        _reject(widget, "speech.consent_required")
    form = pre_chat_payload(widget.integration.config)
    if not form["enabled"]:
        return
    values = fields if isinstance(fields, dict) else {}
    schema = {key: {"type": kind} for key, kind in BUILTIN_TYPES.items()}
    schema.update({item["key"]: item for item in widget.integration.config.get("fields", [])})
    for selected in form["fields"]:
        key = selected["key"]
        value = values.get(key)
        missing = value is None or (isinstance(value, str) and not value.strip())
        if missing:
            if selected["required"]:
                _reject(widget, "speech.form_required")
            continue
        try:
            validate_field_value(value, schema[key])
        except (KeyError, ValueError):
            _reject(widget, "speech.form_required")


def record_acceptance(session, *, version: object, fields: object) -> None:
    validate_acceptance(session.widget, version, fields)
    session.consent_version = current_version(session.widget)
    session.consent_accepted_at = timezone.now()
    session.consent_form_revision = form_revision(session.widget)
    session.save(update_fields=["consent_version", "consent_accepted_at", "consent_form_revision"])


def has_current_consent(session) -> bool:
    return bool(
        session.consent_accepted_at
        and session.consent_version == current_version(session.widget)
        and session.consent_form_revision == form_revision(session.widget)
    )


def require_current_consent(session) -> None:
    """Единый guard: вызывается до внешнего I/O или выполнения события."""
    if not has_current_consent(session):
        _reject(session.widget, "speech.consent_required")
