"""Нормализация конфигурации WEB-подключения."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.webchat.appearance import normalize_appearance
from chatballs.webchat.field_schema import normalize_fields
from chatballs.webchat.pre_chat import normalize_consent, normalize_pre_chat
from chatballs.webchat.recording_configuration import normalize_recording
from chatballs.webchat.site_event_config import normalize_rule


def normalized_web_config(config: dict, previous: dict | None = None) -> dict:
    consent = normalize_consent(config, previous)
    previous = previous or {}
    appearance = normalize_appearance(config, previous)
    allowed = config.get("allowedOrigins", config.get("allowed_domains", []))
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        raise ValidationError({"config": t("settings.allowed_origins_list")})
    quick_replies = config.get("quickReplies", config.get("quick_replies", []))
    if not isinstance(quick_replies, list) or not all(isinstance(item, str) for item in quick_replies):
        raise ValidationError({"config": t("settings.quick_replies_list")})
    # Старые формы, не знающие о схеме, не должны её удалять.
    previous_fields = previous.get("fields", [])
    if not isinstance(previous_fields, list):
        previous_fields = []
    fields = normalize_fields(config["fields"], previous_fields) if "fields" in config else previous_fields
    return {
        "allowed_domains": [item.strip() for item in allowed if item.strip()],
        "title": str(config.get("title", "")).strip(),
        "accent": appearance["accent"],
        "appearance": appearance,
        "greeting": str(config.get("greeting", "")).strip(),
        "quick_replies": quick_replies,
        **consent,
        **normalize_recording(config, previous),
        "fields": fields,
        "preChat": normalize_pre_chat(config, previous, fields),
        "siteEvent": normalize_rule(config, previous),
    }
