"""Reference seed для отдела поддержки (ADR-HUB-0022, SPEC-HUB-0011).

Идемпотентно создаёт:
- ProductSupportIdentityContract foxray.support.v1 (ACTIVE) с примером
  schema/mapping/operator_cards/ai_context/search/sensitive из SPEC-HUB-0011 §5.2;
- support_token_secret для каждого продукта продукта (только если пуст),
  хранится зашифрованным (EncryptedCharField), НЕ печатается и НЕ логируется.

Секрет нужен продуктовому backend'у для подписи Product Support Token; выдача
секрета владельцу/продукту — отдельной командой (TODO), здесь только наполнение.
"""

from __future__ import annotations

import secrets

from django.db import transaction

from hub_platform.channels.models import Channel
from hub_platform.products.models import Product
from hub_platform.support.models import ContractStatus, ProductSupportContract

# Пример контракта FoxRay (SPEC-HUB-0011 §5.2): врач/клиника/подписка.
_FOXRAY_SUPPORT_V1 = {
    "schema": {
        "type": "object",
        "required": ["doctor"],
        "properties": {
            "doctor": {
                "type": "object",
                "required": ["id", "email"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
            },
            "clinic": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
            "subscription": {
                "type": "object",
                "properties": {
                    "tariff": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        },
    },
    "identity_mapping": {
        "subject": "$.doctor.id",
        "account": "$.clinic.id",
        "display_name": "$.doctor.name",
        "display_email": "$.doctor.email",
    },
    "operator_ui": {
        "operator_cards": [
            {
                "title": "Пользователь",
                "fields": [
                    {"label": "Имя", "path": "$.doctor.name", "type": "text"},
                    {"label": "Email", "path": "$.doctor.email", "type": "email"},
                ],
            },
            {
                "title": "Клиника",
                "fields": [
                    {"label": "Название", "path": "$.clinic.name", "type": "text"},
                    {"label": "ID", "path": "$.clinic.id", "type": "code"},
                ],
            },
            {
                "title": "Подписка",
                "fields": [
                    {"label": "Тариф", "path": "$.subscription.tariff", "type": "badge"},
                    {"label": "Статус", "path": "$.subscription.status", "type": "badge"},
                ],
            },
        ]
    },
    "ai_context": {
        "allowed_paths": [
            "$.doctor.name",
            "$.clinic.name",
            "$.subscription.tariff",
            "$.subscription.status",
        ]
    },
    "search": {"paths": ["$.doctor.email", "$.doctor.name", "$.clinic.name"]},
    "sensitive_fields": {"paths": ["$.doctor.email"]},
}

_SUPPORT_CHANNEL_BY_PRODUCT = {"foxray": "foxray-support", "firepage": "firepage-support"}


@transaction.atomic
def _ensure_contract(*, organization, product: Product) -> bool:
    """Создаёт foxray.support.v1 для foxray (пример). Возвращает created."""
    if product.code != "foxray":
        return False
    contract, created = ProductSupportContract.objects.update_or_create(
        organization=organization,
        code="foxray.support.v1",
        defaults={
            "product": product,
            "version": 1,
            "status": ContractStatus.ACTIVE,
            "schema_json": _FOXRAY_SUPPORT_V1["schema"],
            "identity_mapping_json": _FOXRAY_SUPPORT_V1["identity_mapping"],
            "operator_ui_json": _FOXRAY_SUPPORT_V1["operator_ui"],
            "ai_context_json": _FOXRAY_SUPPORT_V1["ai_context"],
            "search_mapping_json": _FOXRAY_SUPPORT_V1["search"],
            "sensitive_fields_json": _FOXRAY_SUPPORT_V1["sensitive_fields"],
        },
    )
    # Привязка контракта к support-каналу продукта (allowed_channels).
    channel_code = _SUPPORT_CHANNEL_BY_PRODUCT.get(product.code)
    if channel_code:
        channel = Channel.objects.filter(organization=organization, code=channel_code).first()
        if channel is not None:
            contract.allowed_channels.add(channel)
    return created


@transaction.atomic
def _ensure_secret(*, product: Product) -> bool:
    """Генерирует support_token_secret, если пуст. Возвращает created."""
    if product.support_token_secret:
        return False
    # secrets.token_urlsafe(32) ~ 43 символа; EncryptedCharField шифрует при save.
    product.support_token_secret = secrets.token_urlsafe(32)
    product.save(update_fields=["support_token_secret"])
    return True


def seed_support_reference(*, organization) -> str:
    """Наполняет reference-данные поддержки. Возвращает строку-статистику."""
    contracts_created = 0
    secrets_created = 0
    for product in Product.objects.filter(organization=organization):
        if _ensure_contract(organization=organization, product=product):
            contracts_created += 1
        if _ensure_secret(product=product):
            secrets_created += 1
    return (
        f"contracts +{contracts_created} (foxray.support.v1), "
        f"secrets +{secrets_created}"
    )
