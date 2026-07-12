"""Единый application service учёта продаж (ADR-HUB-0025, SPEC-HUB-0014).

Все способы доставки (Product Sales API, ручная фиксация, legacy-import) создают
один канонический SaleEvent и идемпотентно применяют его к проекции Sale. Прямой
ORM-write в Sale из view/admin запрещён прикладным контрактом (SPEC §7.3).

Async-воркера в проекте нет: событие сохраняется как raw, затем проекция
применяется синхронно в той же транзакции. Идемпотентность и сохранность raw
события при этом соблюдены (SPEC §5).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from hub_platform.conversations.models import Contact, Conversation
from hub_platform.products.models import Offer, Product
from hub_platform.sales.models import (
    PRODUCT_API_EVENT_TYPES,
    ActorType,
    AttributionMethod,
    AttributionToken,
    Environment,
    ExternalCustomerIdentity,
    ProcessingStatus,
    Sale,
    SaleEvent,
    SaleEventType,
    SalesSource,
    SalesSourceStatus,
    SaleStatus,
    SourceType,
)

# --- Ошибки прикладного слоя, отображаемые в HTTP-коды Product Sales API (SPEC §4.8) ---


class SalesApiError(Exception):
    status_code = 400
    error_code = "invalid_payload"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code


class InvalidPayload(SalesApiError):
    status_code = 400
    error_code = "invalid_payload"


class CredentialError(SalesApiError):
    status_code = 401
    error_code = "invalid_credential"


class EventConflict(SalesApiError):
    status_code = 409
    error_code = "event_conflict"


class UnsupportedSchema(SalesApiError):
    status_code = 422
    error_code = "unsupported"


def hash_credential(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def resolve_sales_source_by_credential(token: str) -> SalesSource | None:
    if not token:
        return None
    return (
        SalesSource.objects.select_related("product", "organization")
        .filter(credential_hash=hash_credential(token))
        .first()
    )


# --- Разбор конверта Product Sales API (SPEC §4.3) ---


@dataclass(frozen=True)
class ParsedEvent:
    event_id: str
    event_type: str
    schema_version: int
    occurred_at: Any
    external_sale_id: str
    external_customer_id: str
    amount_minor: int
    refunded_amount_minor: int | None
    currency: str
    items: list[dict[str, Any]] = field(default_factory=list)
    attribution_token: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _require(payload: dict[str, Any], key: str) -> Any:
    if key not in payload or payload[key] in (None, ""):
        raise InvalidPayload(f"Missing required field: {key}")
    return payload[key]


def _int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise InvalidPayload(f"{field_name} must be an integer") from error


def parse_envelope(payload: dict[str, Any]) -> ParsedEvent:
    if not isinstance(payload, dict):
        raise InvalidPayload("Body must be a JSON object")

    schema_version = _int(_require(payload, "schema_version"), "schema_version")
    event_id = str(_require(payload, "event_id")).strip()
    event_type = str(_require(payload, "event_type")).strip()
    if event_type not in PRODUCT_API_EVENT_TYPES:
        raise UnsupportedSchema(f"Unsupported event_type: {event_type}")

    occurred_at = parse_datetime(str(_require(payload, "occurred_at")))
    if occurred_at is None:
        raise InvalidPayload("occurred_at must be ISO 8601 datetime")
    if timezone.is_naive(occurred_at):
        occurred_at = timezone.make_aware(occurred_at, timezone.utc)

    sale = payload.get("sale")
    if not isinstance(sale, dict):
        raise InvalidPayload("Missing required field: sale")

    external_sale_id = str(_require(sale, "external_sale_id")).strip()
    amount_minor = _int(_require(sale, "amount_minor"), "sale.amount_minor")
    currency = str(_require(sale, "currency")).strip().upper()
    if amount_minor < 0:
        raise InvalidPayload("sale.amount_minor must be >= 0")
    if len(currency) != 3 or not currency.isalpha():
        raise InvalidPayload("sale.currency must be ISO 4217 alpha-3")

    refunded_raw = sale.get("refunded_amount_minor")
    refunded_amount_minor = _int(refunded_raw, "sale.refunded_amount_minor") if refunded_raw is not None else None

    items = sale.get("items")
    if items is not None and not isinstance(items, list):
        raise InvalidPayload("sale.items must be a list")

    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise InvalidPayload("metadata must be an object")

    return ParsedEvent(
        event_id=event_id,
        event_type=event_type,
        schema_version=schema_version,
        occurred_at=occurred_at,
        external_sale_id=external_sale_id,
        external_customer_id=str(sale.get("external_customer_id") or "").strip(),
        amount_minor=amount_minor,
        refunded_amount_minor=refunded_amount_minor,
        currency=currency,
        items=items or [],
        attribution_token=str(payload.get("attribution_token") or "").strip(),
        metadata=metadata,
    )


# --- Приём события Product Sales API ---


@dataclass(frozen=True)
class IngestResult:
    event: SaleEvent
    duplicate: bool


def record_product_sales_event(*, source: SalesSource, payload: dict[str, Any]) -> IngestResult:
    if source.status == SalesSourceStatus.DISABLED:
        raise CredentialError("Sales source is disabled")

    parsed = parse_envelope(payload)

    allowed = source.allowed_schema_versions or [1]
    if parsed.schema_version not in allowed:
        raise UnsupportedSchema(f"schema_version {parsed.schema_version} not allowed")

    if source.status == SalesSourceStatus.READ_ONLY:
        raise EventConflict("Sales source is read-only", error_code="read_only")

    # Идемпотентность по (source, external_event_id): повтор того же события —
    # успешный дубликат; тот же id с иным содержимым — конфликт (SPEC §4.8, 409).
    existing = SaleEvent.objects.filter(sales_source=source, external_event_id=parsed.event_id).first()
    if existing is not None:
        if existing.event_type != parsed.event_type:
            raise EventConflict("event_id already used with a different event_type")
        return IngestResult(event=existing, duplicate=True)

    try:
        with transaction.atomic():
            event = SaleEvent.objects.create(
                organization=source.organization,
                sales_source=source,
                environment=source.environment,
                source_type=SourceType.PRODUCT_API,
                external_event_id=parsed.event_id,
                event_type=parsed.event_type,
                schema_version=parsed.schema_version,
                occurred_at=parsed.occurred_at,
                raw_payload=payload,
                processing_status=ProcessingStatus.RECEIVED,
            )
            _apply_event(event=event, source=source, parsed=parsed)
    except IntegrityError:
        # Гонка одновременной доставки того же event_id — возвращаем дубликат.
        existing = SaleEvent.objects.filter(sales_source=source, external_event_id=parsed.event_id).first()
        if existing is not None:
            return IngestResult(event=existing, duplicate=True)
        raise

    _touch_source(source)
    return IngestResult(event=event, duplicate=False)


def _touch_source(source: SalesSource) -> None:
    source.last_event_at = timezone.now()
    source.save(update_fields=["last_event_at", "updated_at"])


# --- Применение события к проекции Sale ---


def _status_from_amounts(amount: int, refunded: int) -> str:
    if refunded <= 0:
        return SaleStatus.CONFIRMED
    if refunded >= amount:
        return SaleStatus.REFUNDED
    return SaleStatus.PARTIALLY_REFUNDED


def _apply_event(*, event: SaleEvent, source: SalesSource | None, parsed: ParsedEvent) -> Sale:
    """Идемпотентно применяет событие к Sale в рамках уже открытой транзакции."""
    organization = event.organization
    product = source.product if source is not None else event.sale.product  # source обязателен для PRODUCT_API

    sale = None
    if source is not None and parsed.external_sale_id:
        sale = (
            Sale.objects.select_for_update()
            .filter(sales_source=source, external_sale_id=parsed.external_sale_id)
            .first()
        )

    created = sale is None
    if created:
        sale = Sale(
            organization=organization,
            product=product,
            sales_source=source,
            environment=event.environment,
            source_type=event.source_type,
            external_sale_id=parsed.external_sale_id,
            external_customer_id=parsed.external_customer_id,
            amount_minor=parsed.amount_minor,
            currency=parsed.currency,
            occurred_at=parsed.occurred_at,
            status=SaleStatus.CONFIRMED,
            line_items_snapshot=parsed.items,
            metadata=parsed.metadata,
        )

    # Out-of-order защита (SPEC §5): более старое occurred_at не откатывает проекцию.
    stale = not created and sale.last_event_at is not None and parsed.occurred_at < sale.last_event_at

    if not stale:
        _mutate_projection(sale=sale, event=event, parsed=parsed)
        if created or event.event_type == SaleEventType.CONFIRMED:
            _resolve_attribution(sale=sale, source=source, parsed=parsed, environment=event.environment)
        sale.last_event_at = parsed.occurred_at

    # refunded не может превышать amount (страховка проекции).
    if sale.refunded_amount_minor > sale.amount_minor:
        raise InvalidPayload("refunded_amount_minor exceeds amount_minor")

    sale.save()
    event.sale = sale
    sale.last_event = event
    sale.save(update_fields=["last_event", "updated_at"])

    event.processing_status = ProcessingStatus.APPLIED
    event.applied_at = timezone.now()
    event.save(update_fields=["sale", "processing_status", "applied_at"])
    return sale


def _mutate_projection(*, sale: Sale, event: SaleEvent, parsed: ParsedEvent) -> None:
    event_type = event.event_type
    if event_type in (SaleEventType.CONFIRMED, SaleEventType.CORRECTED, SaleEventType.LEGACY_IMPORTED):
        sale.amount_minor = parsed.amount_minor
        sale.currency = parsed.currency
        if parsed.items:
            sale.line_items_snapshot = parsed.items
        # confirmed возрождает ранее отменённую продажу; corrected/legacy — пересчёт от сумм.
        if sale.status == SaleStatus.CANCELLED and event_type != SaleEventType.CONFIRMED:
            sale.status = SaleStatus.CANCELLED
        else:
            sale.status = _status_from_amounts(sale.amount_minor, sale.refunded_amount_minor)
    elif event_type == SaleEventType.PARTIALLY_REFUNDED:
        refunded = parsed.refunded_amount_minor if parsed.refunded_amount_minor is not None else sale.refunded_amount_minor
        sale.refunded_amount_minor = refunded
        sale.status = _status_from_amounts(sale.amount_minor, refunded)
    elif event_type == SaleEventType.REFUNDED:
        sale.refunded_amount_minor = sale.amount_minor
        sale.status = SaleStatus.REFUNDED
    elif event_type == SaleEventType.CANCELLED:
        sale.status = SaleStatus.CANCELLED
    if parsed.metadata:
        merged = dict(sale.metadata or {})
        merged.update(parsed.metadata)
        sale.metadata = merged


# --- Атрибуция (ADR-HUB-0025 §7, SPEC §6) ---


def _valid_token(raw_token: str, organization) -> AttributionToken | None:
    if not raw_token:
        return None
    token = AttributionToken.objects.filter(token_hash=hash_credential(raw_token), organization=organization).first()
    if token is None:
        return None
    if token.revoked_at is not None or token.expires_at <= timezone.now():
        return None
    return token


def _ensure_identity(*, organization, product: Product, environment: str, external_customer_id: str, contact: Contact) -> None:
    if not external_customer_id or contact is None:
        return
    ExternalCustomerIdentity.objects.get_or_create(
        product=product,
        environment=environment,
        external_customer_id=external_customer_id,
        defaults={
            "organization": organization,
            "contact": contact,
            "verification_method": "attribution_token",
            "verified_at": timezone.now(),
        },
    )


def _resolve_attribution(*, sale: Sale, source: SalesSource | None, parsed: ParsedEvent, environment: str) -> None:
    # Приоритет: действительный AttributionToken → ExternalCustomerIdentity → без атрибуции.
    token = _valid_token(parsed.attribution_token, sale.organization)
    if token is not None:
        now = timezone.now()
        sale.contact = token.contact
        sale.conversation = token.conversation
        sale.attribution_method = AttributionMethod.ATTRIBUTION_TOKEN
        sale.attributed_actor_type = token.actor_type
        sale.attributed_actor_id = token.actor_id
        token.first_seen_at = token.first_seen_at or now
        token.last_seen_at = now
        token.save(update_fields=["first_seen_at", "last_seen_at"])
        _ensure_identity(
            organization=sale.organization,
            product=sale.product,
            environment=environment,
            external_customer_id=parsed.external_customer_id,
            contact=token.contact,
        )
        return

    if parsed.external_customer_id:
        identity = ExternalCustomerIdentity.objects.filter(
            product=sale.product, environment=environment, external_customer_id=parsed.external_customer_id
        ).first()
        if identity is not None:
            # Повторная продажа: identity даёт клиента, но НЕ наследует автора первой продажи.
            sale.contact = identity.contact
            sale.attribution_method = AttributionMethod.EXTERNAL_IDENTITY
            sale.attributed_actor_type = ""
            sale.attributed_actor_id = ""
            return

    if sale.attribution_method == AttributionMethod.NONE and sale.contact_id is None:
        sale.attribution_method = AttributionMethod.NONE


# --- Ручная фиксация (SPEC §7) ---


@transaction.atomic
def create_manual_sale(
    *,
    organization,
    actor_user,
    product: Product,
    amount_minor: int,
    currency: str,
    occurred_at,
    reason: str,
    contact: Contact | None = None,
    conversation: Conversation | None = None,
    external_sale_id: str = "",
    external_customer_id: str = "",
    line_items: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Sale:
    if contact is None and conversation is None:
        raise InvalidPayload("Manual sale needs a contact or conversation")
    if conversation is not None and contact is None:
        contact = conversation.contact
    if amount_minor < 0:
        raise InvalidPayload("amount_minor must be >= 0")
    currency = str(currency).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise InvalidPayload("currency must be ISO 4217 alpha-3")

    # Без внешнего id Hub создаёт внутренний стабильный идентификатор (SPEC §7.2).
    external_sale_id = external_sale_id.strip() or f"manual-{uuid.uuid4().hex}"
    meta = dict(metadata or {})
    if reason:
        meta.setdefault("reason", reason)

    event = SaleEvent.objects.create(
        organization=organization,
        sales_source=None,
        environment=Environment.PRODUCTION,
        source_type=SourceType.MANUAL,
        event_type=SaleEventType.CONFIRMED,
        schema_version=1,
        occurred_at=occurred_at,
        actor_user=actor_user,
        raw_payload={
            "event_type": SaleEventType.CONFIRMED.value,
            "sale": {
                "external_sale_id": external_sale_id,
                "external_customer_id": external_customer_id,
                "amount_minor": amount_minor,
                "currency": currency,
                "items": line_items or [],
            },
            "metadata": meta,
        },
        processing_status=ProcessingStatus.RECEIVED,
    )

    sale = Sale(
        organization=organization,
        product=product,
        sales_source=None,
        environment=Environment.PRODUCTION,
        source_type=SourceType.MANUAL,
        external_sale_id=external_sale_id,
        external_customer_id=external_customer_id,
        contact=contact,
        conversation=conversation,
        status=SaleStatus.CONFIRMED,
        amount_minor=amount_minor,
        currency=currency,
        occurred_at=occurred_at,
        last_event_at=occurred_at,
        attribution_method=AttributionMethod.MANUAL,
        line_items_snapshot=line_items or [],
        metadata=meta,
    )
    if external_customer_id and contact is not None:
        _ensure_identity(
            organization=organization,
            product=product,
            environment=Environment.PRODUCTION,
            external_customer_id=external_customer_id,
            contact=contact,
        )
    sale.save()
    event.sale = sale
    event.processing_status = ProcessingStatus.APPLIED
    event.applied_at = timezone.now()
    event.save(update_fields=["sale", "processing_status", "applied_at"])
    sale.last_event = event
    sale.save(update_fields=["last_event", "updated_at"])
    return sale


@transaction.atomic
def record_manual_action(
    *,
    sale: Sale,
    actor_user,
    event_type: str,
    reason: str,
    amount_minor: int | None = None,
    refunded_amount_minor: int | None = None,
) -> Sale:
    """Ручная корректировка/возврат/отмена существующей продажи через SaleEvent."""
    if event_type not in {
        SaleEventType.CORRECTED,
        SaleEventType.CANCELLED,
        SaleEventType.PARTIALLY_REFUNDED,
        SaleEventType.REFUNDED,
    }:
        raise InvalidPayload("Unsupported manual event_type")

    locked = Sale.objects.select_for_update().get(pk=sale.pk)
    occurred_at = timezone.now()
    meta = {"reason": reason} if reason else {}

    parsed = ParsedEvent(
        event_id="",
        event_type=event_type,
        schema_version=1,
        occurred_at=occurred_at,
        external_sale_id=locked.external_sale_id,
        external_customer_id=locked.external_customer_id,
        amount_minor=amount_minor if amount_minor is not None else locked.amount_minor,
        refunded_amount_minor=refunded_amount_minor,
        currency=locked.currency,
        items=[],
        attribution_token="",
        metadata=meta,
    )
    event = SaleEvent.objects.create(
        organization=locked.organization,
        sales_source=None,
        sale=locked,
        environment=locked.environment,
        source_type=SourceType.MANUAL,
        event_type=event_type,
        schema_version=1,
        occurred_at=occurred_at,
        actor_user=actor_user,
        raw_payload={"event_type": str(event_type), "sale": {"external_sale_id": locked.external_sale_id}, "metadata": meta},
        processing_status=ProcessingStatus.RECEIVED,
    )
    _mutate_projection(sale=locked, event=event, parsed=parsed)
    locked.last_event_at = occurred_at
    if locked.refunded_amount_minor > locked.amount_minor:
        raise InvalidPayload("refunded_amount_minor exceeds amount_minor")
    locked.save()
    event.processing_status = ProcessingStatus.APPLIED
    event.applied_at = timezone.now()
    event.save(update_fields=["processing_status", "applied_at"])
    locked.last_event = event
    locked.save(update_fields=["last_event", "updated_at"])
    return locked


# --- Attribution token issuance (SPEC §6.1) ---


@transaction.atomic
def issue_attribution_token(
    *,
    organization,
    product: Product,
    contact: Contact,
    conversation: Conversation,
    actor_type: str,
    actor_id: str = "",
    offer: Offer | None = None,
    channel=None,
    connection=None,
    ttl_hours: int = 72,
    metadata: dict[str, Any] | None = None,
) -> tuple[AttributionToken, str]:
    if actor_type not in ActorType.values:
        raise InvalidPayload("Unknown actor_type")
    raw = secrets.token_urlsafe(32)
    token = AttributionToken.objects.create(
        token_hash=hash_credential(raw),
        organization=organization,
        product=product,
        offer=offer,
        contact=contact,
        conversation=conversation,
        channel=channel or getattr(conversation, "channel", None),
        connection=connection or getattr(conversation, "connection", None),
        actor_type=actor_type,
        actor_id=str(actor_id or ""),
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
        metadata=metadata or {},
    )
    return token, raw


def issue_sales_source_credential(*, source: SalesSource) -> str:
    """Генерирует и сохраняет hash нового Bearer-ключа источника. Ключ виден один раз."""
    raw = secrets.token_urlsafe(32)
    source.credential_hash = hash_credential(raw)
    source.credential_hint = raw[-4:]
    source.save(update_fields=["credential_hash", "credential_hint", "updated_at"])
    return raw
