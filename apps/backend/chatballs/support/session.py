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

from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    LifecycleState,
)
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import AuditResult, Organization
from chatballs.support import errors
from chatballs.support.extract import extract_context, validate_schema
from chatballs.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)
from chatballs.support.selectors import contract_by_code
from chatballs.support.token import TokenClaims, claims_datetimes, verify_support_token
from chatballs.support.widget_credential import issue_widget_credential
from chatballs.tenancy.context import TenantContext


def _deny_channel_policy(channel) -> errors.SupportSessionError | None:
    """Fail-closed проверки канала (SPEC §5.2)."""
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

    context = TenantContext.for_resource(channel.organization)
    contract = contract_by_code(context=context, code=claims.contract)
    if contract is None:
        raise errors.SupportSessionError(errors.CONTRACT_NOT_FOUND)
    # DRAFT и DISABLED не принимают production traffic (SPEC-HUB-0011 §3).
    if contract.status in {ContractStatus.DRAFT, ContractStatus.DISABLED}:
        raise errors.SupportSessionError(errors.CONTRACT_DISABLED)
    if not contract.allowed_channels.filter(id=channel.id).exists():
        raise errors.SupportSessionError(errors.CONTRACT_CHANNEL_NOT_ALLOWED)

    validate_schema(claims.data, contract.schema_json)
    extracted = extract_context(claims.data, contract)
    return claims, contract, extracted


def start_support_session(
    *, widget, token: str, request: HttpRequest | None = None
) -> dict[str, Any]:
    """Создаёт/обновляет snapshot и создаёт/продолжает support Conversation.

    При любой ошибке проверки пишет audit (DENIED) с машинным кодом и хэшем jti,
    затем поднимает SupportSessionError. Raw token не попадает в audit.

    Audit-deny пишется вне write-транзакции: иначе откат при raise уничтожил бы
    запись. Успешный путь (snapshot + conversation + audit-success) атомарен.
    """
    channel = widget.integration.channel
    organization: Organization = widget.organization
    try:
        claims, contract, extracted = verify_and_resolve(channel=channel, token=token)
    except errors.SupportSessionError as error:
        _audit_denied(
            organization=organization, channel=channel, request=request,
            error=error, token=token,
        )
        raise

    return _commit_session(
        organization=organization, channel=channel, contract=contract,
        claims=claims, extracted=extracted, widget=widget, request=request,
    )


@transaction.atomic
def _commit_session(
    *, organization, channel, contract, claims, extracted, widget, request
) -> dict[str, Any]:
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
    conversation = _create_or_continue_conversation(
        organization=organization,
        channel=channel,
        snapshot=snapshot,
        widget=widget,
    )

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
            "web_chat_widget_id": widget.id,
            "jti_hash": claims.jti_hash[:16],
        },
        request=request,
    )
    widget_credential = issue_widget_credential(
        conversation_id=conversation.id, snapshot_id=snapshot.id
    )
    return {
        "conversation": conversation,
        "snapshot": snapshot,
        "widget_credential": widget_credential,
    }


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


def _create_or_continue_conversation(*, organization, channel, snapshot, widget) -> Conversation:
    conversation = (
        Conversation.objects.filter(
            channel=channel, support_identity_snapshot=snapshot, lifecycle=LifecycleState.OPEN
        )
        .order_by("-last_activity_at")
        .first()
    )
    if conversation is not None:
        metadata = conversation.transport_meta or {}
        conversation.transport_meta = {
            **metadata,
            "webChatWidgetId": metadata.get("webChatWidgetId", widget.id),
            "lastWebChatWidgetId": widget.id,
        }
        update_fields = ["transport_meta"]
        if conversation.connection_id is None:
            conversation.connection = widget.integration
            update_fields.append("connection")
        conversation.save(update_fields=update_fields)
        return conversation
    previous = (
        Conversation.objects.filter(
            channel=channel, support_identity_snapshot=snapshot
        )
        .order_by("-created_at")
        .first()
    )
    conversation = Conversation.objects.create(
        organization=channel.organization,
        channel=channel,
        # Диалог наследует группу канала при создании (ADR-HUB-0043 §3).
        group=channel.group,
        connection=widget.integration,
        contact=None,
        support_identity_snapshot=snapshot,
        transport_meta={
            "webChatWidgetId": widget.id,
            "lastWebChatWidgetId": widget.id,
        },
        control_mode=ControlMode.AI,
        expected_responder=ExpectedResponder.AI,
        previous_conversation=previous,
    )
    return conversation
