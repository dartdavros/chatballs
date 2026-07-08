"""Проверка Product Support Token и старт support-сессии (SPEC-HUB-0011 §12).

Алгоритм start: channel checks → token verify → contract lookup → schema
validation → identity/operator/ai/search extraction → snapshot upsert →
create-or-continue Conversation → audit (success/denied). Raw token нигде
не сохраняется и не логируется — только короткий хэш jti.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import HttpRequest

from hub_platform.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    LifecycleState,
)
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditResult, Organization
from hub_platform.support import errors, jsonpath
from hub_platform.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)
from hub_platform.support.selectors import active_contract_for
from hub_platform.support.token import TokenClaims, claims_datetimes, verify_support_token


def _deny_channel_policy(channel) -> errors.SupportSessionError | None:
    """Fail-closed проверки канала (SPEC §5.2)."""
    if channel.department_id is None or channel.department.code != "support":
        return errors.SupportSessionError(errors.CHANNEL_NOT_SUPPORT)
    if channel.product_id is None:
        return errors.SupportSessionError(errors.CHANNEL_PRODUCT_MISMATCH)
    if channel.requires_authenticated_product_identity and not channel.allow_anonymous_sessions:
        return None  # корректный support-канал
    return errors.SupportSessionError(errors.CHANNEL_NOT_SUPPORT)


def verify_and_resolve(
    *, channel, token: str
) -> tuple[TokenClaims, ProductSupportContract, dict[str, Any]]:
    """Шаги 1–13 алгоритма: channel → token → contract → schema → mapping.

    Возвращает (claims, contract, extracted) без записи в БД. Raw token не трогаем.
    """
    channel_error = _deny_channel_policy(channel)
    if channel_error is not None:
        raise channel_error

    product = channel.product
    secret = product.support_token_secret or ""
    claims = verify_support_token(token=token, secret=secret)

    # iss должен совпадать с кодом продукта канала.
    if claims.iss != product.code:
        raise errors.SupportSessionError(errors.CHANNEL_PRODUCT_MISMATCH)

    contract = active_contract_for(organization_id=channel.organization_id, code=claims.contract)
    if contract is None:
        raise errors.SupportSessionError(errors.CONTRACT_NOT_FOUND)
    if contract.status == ContractStatus.DISABLED:
        raise errors.SupportSessionError(errors.CONTRACT_DISABLED)
    if not contract.allowed_channels.filter(id=channel.id).exists():
        raise errors.SupportSessionError(errors.CONTRACT_CHANNEL_NOT_ALLOWED)

    _validate_schema(claims.data, contract.schema_json)
    extracted = _extract_context(claims.data, contract)
    return claims, contract, extracted


def _validate_schema(data: dict[str, Any], schema: dict[str, Any]) -> None:
    """Ручная проверка required-полей по schema (нет jsonschema-зависимости).

    Проверяет только object.required и наличие полей; глубокая type-проверка — TODO.
    Соответствует pattern из orders/views.py (isinstance + required).
    """
    if not schema:
        return
    required = schema.get("required") or []
    if isinstance(required, list):
        for field in required:
            if field not in data:
                raise errors.SupportSessionError(errors.PAYLOAD_SCHEMA_INVALID)
    # Рекурсивная проверка required во вложенных object-properties.
    properties = schema.get("properties") or {}
    if isinstance(properties, dict):
        for field, subschema in properties.items():
            if not isinstance(subschema, dict):
                continue
            sub_required = subschema.get("required")
            value = data.get(field)
            if isinstance(sub_required, list) and isinstance(value, dict):
                for sub_field in sub_required:
                    if sub_field not in value:
                        raise errors.SupportSessionError(errors.PAYLOAD_SCHEMA_INVALID)


def _extract_context(data: dict[str, Any], contract: ProductSupportContract) -> dict[str, Any]:
    """Извлекает identity/operator_cards/ai_context/search по mapping'ам контракта."""
    identity = contract.identity_mapping_json or {}
    subject = jsonpath.resolve_path(data, identity.get("subject", ""))
    if not subject:
        raise errors.SupportSessionError(errors.SUBJECT_MAPPING_EMPTY)

    account = jsonpath.resolve_path(data, identity.get("account", ""))
    display_name = jsonpath.resolve_path(data, identity.get("display_name", "")) or ""
    display_email = jsonpath.resolve_path(data, identity.get("display_email", "")) or ""

    operator_cards = _build_operator_cards(data, contract.operator_ui_json or {})
    ai_context = _build_ai_context(data, contract.ai_context_json or {})
    search_text = _build_search_text(data, contract.search_mapping_json or {})

    return {
        "subject_key": str(subject),
        "account_key": str(account) if account else "",
        "display_name": str(display_name),
        "display_email": str(display_email),
        "operator_context": {"operator_cards": operator_cards},
        "ai_context": ai_context,
        "search_text": search_text,
    }


def _build_operator_cards(data: dict[str, Any], ui: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card in ui.get("operator_cards", []) or []:
        fields = []
        for field in card.get("fields", []) or []:
            value = jsonpath.resolve_path(data, field.get("path", ""))
            fields.append(
                {
                    "label": field.get("label", ""),
                    "value": value,
                    "type": field.get("type", "text"),
                    "visibility": field.get("visibility", "operator"),
                }
            )
        cards.append({"title": card.get("title", ""), "fields": fields})
    return cards


def _build_ai_context(data: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    allowed = ai.get("allowed_paths", []) or []
    values: dict[str, Any] = {}
    for path in allowed:
        values[path] = jsonpath.resolve_path(data, path)
    return {"allowed_paths": values}


def _build_search_text(data: dict[str, Any], search: dict[str, Any]) -> str:
    paths = search.get("paths", []) or []
    parts = [str(jsonpath.resolve_path(data, p)) for p in paths]
    return " ".join(p for p in parts if p and p != "None")


@transaction.atomic
def start_support_session(
    *, channel, token: str, request: HttpRequest | None = None
) -> dict[str, Any]:
    """Создаёт/обновляет snapshot и создаёт/продолжает support Conversation.

    При любой ошибке проверки пишет audit (DENIED) с машинным кодом и хэшем jti,
    затем поднимает SupportSessionError. Raw token не попадает в audit.
    """
    organization: Organization = channel.organization
    try:
        claims, contract, extracted = verify_and_resolve(channel=channel, token=token)
    except errors.SupportSessionError as error:
        _audit_denied(
            organization=organization, channel=channel, request=request,
            error=error, token=token,
        )
        raise

    issued_at, expires_at = claims_datetimes(claims)
    snapshot = _upsert_snapshot(
        organization=organization,
        channel=channel,
        contract=contract,
        claims=claims,
        extracted=extracted,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    conversation = _create_or_continue_conversation(channel=channel, snapshot=snapshot)

    record_audit_event(
        action="support.session_started",
        result=AuditResult.SUCCESS,
        organization=organization,
        object_type="Conversation",
        object_id=str(conversation.id),
        payload={
            "contract": contract.code,
            "subject_key": extracted["subject_key"],
            "product": channel.product.code,
            "jti_hash": claims.jti_hash[:16],
        },
        request=request,
    )
    return {"conversation": conversation, "snapshot": snapshot}


def _audit_denied(
    *, organization, channel, request, error: errors.SupportSessionError, token: str
) -> None:
    # jti_hash безопасен; iss/contract неизвестны до verify — извлекаем только jti без raw token.
    jti_hash = _safe_jti_hash(token)
    record_audit_event(
        action="support.session_denied",
        result=AuditResult.DENIED,
        organization=organization,
        object_type="Channel",
        object_id=str(channel.id),
        payload={"code": error.code, "jti_hash": jti_hash},
        request=request,
    )


def _safe_jti_hash(token: str) -> str:
    """Хэш jti без раскрытия raw token: best-effort извлечение payload для audit."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return ""
        import base64
        import hashlib
        import json as _json

        padding = "=" * (-len(parts[1]) % 4)
        payload = _json.loads(base64.urlsafe_b64decode(parts[1] + padding))
        jti = payload.get("jti", "")
        return hashlib.sha256(str(jti).encode("utf-8")).hexdigest()[:16] if jti else ""
    except Exception:
        return ""


def _upsert_snapshot(
    *, organization, channel, contract, claims, extracted, issued_at, expires_at
) -> SupportIdentitySnapshot:
    snapshot, _created = SupportIdentitySnapshot.objects.update_or_create(
        product=channel.product,
        subject_key=extracted["subject_key"],
        defaults={
            "organization": organization,
            "contract": contract,
            "contract_code": contract.code,
            "account_key": extracted["account_key"] or None,
            "display_name": extracted["display_name"],
            "display_email": extracted["display_email"],
            "payload_json": claims.data,
            "operator_context_json": extracted["operator_context"],
            "ai_context_json": extracted["ai_context"],
            "search_text": extracted["search_text"],
            "token_issued_at": issued_at,
            "token_expires_at": expires_at,
            "token_jti_hash": claims.jti_hash,
        },
    )
    return snapshot


def _create_or_continue_conversation(*, channel, snapshot) -> Conversation:
    conversation = (
        Conversation.objects.filter(
            channel=channel, support_identity_snapshot=snapshot, lifecycle=LifecycleState.OPEN
        )
        .order_by("-last_activity_at")
        .first()
    )
    if conversation is not None:
        return conversation
    previous = (
        Conversation.objects.filter(
            channel=channel, support_identity_snapshot=snapshot
        )
        .order_by("-created_at")
        .first()
    )
    return Conversation.objects.create(
        organization=channel.organization,
        channel=channel,
        contact=None,
        support_identity_snapshot=snapshot,
        control_mode=ControlMode.AI,
        expected_responder=ExpectedResponder.AI,
        previous_conversation=previous,
    )
