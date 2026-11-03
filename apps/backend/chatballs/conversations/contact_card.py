"""Поля карточки контакта, которые правит сотрудник: один список для чата и «Контактов»."""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from chatballs.i18n import t

CARD_LIMITS = {"name": 255, "description": 2000, "phone": 32, "email": 254, "company": 160, "city": 120}


def apply_card_fields(contact, data) -> tuple[list[str], str]:
    """Переносит присланные поля в контакт; возвращает изменённые поля и текст ошибки.

    Адрес почты только сохраняется у контакта: он не подтверждает личность и не
    запускает слияние контактов.
    """
    changed: list[str] = []
    for field, limit in CARD_LIMITS.items():
        if field not in data:
            continue
        value = str(data.get(field) or "").strip()
        if len(value) > limit:
            return [], t("conversations.field_too_long", field=field, limit=limit)
        if field == "name" and not value:
            return [], t("conversations.contact_name_empty")
        if field == "email" and value:
            value = value.lower()
            try:
                validate_email(value)
            except ValidationError:
                return [], t("conversations.contact_email_invalid")
        setattr(contact, field, value)
        changed.append(field)
    return changed, ""


def save_card_fields(contact, data) -> tuple[list[str], str]:
    """Shared domain persistence, including provenance invalidation."""
    changed, error = apply_card_fields(contact, data)
    if changed and not error:
        from chatballs.conversations.models import ContactFieldValue
        contact.save(update_fields=changed)
        ContactFieldValue.objects.filter(contact=contact, key__in=changed).delete()
    return changed, error
