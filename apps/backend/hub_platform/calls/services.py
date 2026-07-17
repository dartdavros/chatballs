from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from hub_platform.calls.errors import (
    CallAccessDenied,
    CallConflict,
    CallInvalidTransition,
    CallTokenError,
)
from hub_platform.calls.lifecycle import transition_call
from hub_platform.calls.metrics import record_call_metric
from hub_platform.calls.models import (
    TERMINAL_CALL_STATUSES,
    UNFINISHED_CALL_STATUSES,
    CallEndedBy,
    CallInvite,
    CallParticipant,
    CallSession,
    CallStatus,
    InviteDeliveryStatus,
    ParticipantSide,
)
from hub_platform.calls.permissions import ensure_call_access, ensure_conversation_call_access
from hub_platform.calls.public_access import (
    ResolvedInvite,
    accept_call_by_access_token,
    authorize_call_access_context,
    authorize_call_access_token,
    call_state_by_access_token,
    decline_call_by_access_token,
    resolve_invite,
)
from hub_platform.calls.tokens import (
    issue_call_access_token,
    issue_invite_token,
)
from hub_platform.conversations.models import (
    ConnectionIdentity,
    ControlMode,
    Conversation,
    LifecycleState,
    Message,
    MessageAuthor,
)
from hub_platform.conversations.services import ClaimError, claim_locked_conversation
from hub_platform.events.services import DomainEvent, enqueue_event
from hub_platform.integrations.models import IntegrationProvider
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.reservation_service import reserve_usage
from hub_platform.tenancy.context import TenantContext

__all__ = (
    "accept_call_by_access_token",
    "authorize_call_access_context",
    "authorize_call_access_token",
    "call_state_by_access_token",
    "decline_call_by_access_token",
    "resolve_invite",
    "record_call_metric",
)

# Outbox-событие доставки приглашения в TG/MAX (обработчик — calls.event_handlers).
CALL_INVITE_SEND = "calls.invite_send"


@dataclass(frozen=True)
class CreatedCall:
    call_session: CallSession
    invite_token: str
    staff_access_token: str


def _conversation_identity(conversation: Conversation) -> ConnectionIdentity:
    if conversation.contact_id is None or conversation.connection_id is None:
        raise CallConflict("У диалога нет клиентской identity для звонка")
    identities = list(
        ConnectionIdentity.objects.filter(
            contact_id=conversation.contact_id,
            connection_id=conversation.connection_id,
        )
        .order_by("id")[:2]
    )
    if len(identities) != 1:
        raise CallConflict("Клиентская identity звонка отсутствует или неоднозначна")
    return identities[0]


def _check_call_creation_conflicts(*, conversation: Conversation, initiator) -> None:
    if conversation.lifecycle != LifecycleState.OPEN:
        raise CallConflict("Звонок можно запросить только в открытом диалоге")
    if CallSession.objects.filter(
        conversation=conversation,
        status__in=UNFINISHED_CALL_STATUSES,
    ).exists():
        raise CallConflict("В диалоге уже есть незавершённый звонок")
    if CallSession.objects.filter(
        initiated_by=initiator,
        status__in=UNFINISHED_CALL_STATUSES,
    ).exists():
        raise CallConflict("Сотрудник уже участвует в другом звонке")
    if (
        conversation.control_mode == ControlMode.HUMAN
        and conversation.assigned_operator_id
        and conversation.assigned_operator_id != initiator.id
    ):
        raise CallConflict("Диалог уже ведёт другой оператор")


@transaction.atomic
def create_call_request(*, context: TenantContext, conversation_id: int) -> CreatedCall:
    initiator = context.actor_user
    if initiator is None or context.membership is None:
        raise CallAccessDenied("Для звонка требуется контекст сотрудника")
    conversation = (
        Conversation.objects.select_for_update()
        .select_related("channel")
        .get(id=conversation_id, organization=context.organization)
    )
    ensure_conversation_call_access(user=context.membership, conversation=conversation)
    identity = _conversation_identity(conversation)
    _check_call_creation_conflicts(conversation=conversation, initiator=initiator)

    if conversation.control_mode != ControlMode.HUMAN or conversation.assigned_operator_id != initiator.id:
        try:
            claim_locked_conversation(context=context, conversation=conversation)
        except ClaimError as error:
            raise CallConflict(str(error)) from error

    invite_token, token_hash = issue_invite_token()
    try:
        with transaction.atomic():
            call = CallSession.objects.create(
                organization_id=conversation.organization_id,
                conversation=conversation,
                initiated_by=initiator,
                delivery_connection_id=conversation.connection_id,
            )
    except IntegrityError as error:
        raise CallConflict("Не удалось создать второй незавершённый звонок") from error

    CallInvite.objects.create(
        organization=context.organization,
        call_session=call,
        connection_identity=identity,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(seconds=settings.CUS_CALL_INVITE_TTL_SECONDS),
    )
    CallParticipant.objects.bulk_create(
        [
            CallParticipant(
                organization=context.organization,
                call_session=call,
                side=ParticipantSide.STAFF,
                user=initiator,
            ),
            CallParticipant(
                organization=context.organization,
                call_session=call,
                side=ParticipantSide.CUSTOMER,
                connection_identity=identity,
            ),
        ]
    )
    # C07 concurrent quota: reserve a p2p-call slot for the lifetime of the
    # session. Released on terminal status (calls/lifecycle.transition_call) or
    # reaped by the reservation sweep if the lease lapses.
    reserve_usage(
        context=context,
        quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
        idempotency_key=f"p2p:{call.id}",
        lease_seconds=settings.CUS_CONCURRENT_CALL_LEASE_SECONDS,
        source="calls.session_created",
        aggregate_type="CallSession",
        aggregate_id=str(call.id),
    )
    initiator_label = getattr(initiator, "full_name", "") or initiator.email
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        text=f"Оператор {initiator_label} запросил онлайн-звонок",
    )
    if conversation.connection.provider == IntegrationProvider.WEB:
        # Web Chat: приглашение забирает виджет поллингом, внешней отправки нет.
        call.invite.delivery_status = InviteDeliveryStatus.SENT
        call.invite.save(update_fields=["delivery_status"])
        call = transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
    else:
        # TG/MAX: кнопка со ссылкой /calls/<token> уходит через outbox с ретраями.
        enqueue_event(
            DomainEvent(
                aggregate_type="call_session",
                aggregate_id=str(call.id),
                event_type=CALL_INVITE_SEND,
                payload={"callSessionId": str(call.id)},
                tenant_context=context,
            )
        )
    staff_token = issue_call_access_token(
        call_session_id=call.id,
        side=ParticipantSide.STAFF,
        subject_id=str(initiator.id),
    )
    return CreatedCall(call_session=call, invite_token=invite_token, staff_access_token=staff_token)


def issue_staff_access_token(*, context: TenantContext, call_session: CallSession) -> str:
    user = context.actor_user
    if user is None or context.membership is None:
        raise CallAccessDenied("Для звонка требуется контекст сотрудника")
    ensure_call_access(user=context.membership, call_session=call_session)
    participant_exists = call_session.participants.filter(side=ParticipantSide.STAFF, user=user).exists()
    if not participant_exists:
        raise CallConflict("Сотрудник не является участником звонка")
    if call_session.status in TERMINAL_CALL_STATUSES:
        raise CallConflict("Звонок уже завершён")
    return issue_call_access_token(
        call_session_id=call_session.id,
        side=ParticipantSide.STAFF,
        subject_id=str(user.id),
    )


def cancel_call(*, context: TenantContext, call_session: CallSession) -> CallSession:
    user = context.actor_user
    if user is None or context.membership is None:
        raise CallAccessDenied("Для звонка требуется контекст сотрудника")
    ensure_call_access(user=context.membership, call_session=call_session)
    if not call_session.participants.filter(side=ParticipantSide.STAFF, user=user).exists():
        raise CallConflict("Сотрудник не является участником звонка")
    try:
        # Повторная отмена идемпотентна: transition_call вернёт звонок без изменений.
        return transition_call(
            call_session_id=call_session.id,
            target_status=CallStatus.CANCELLED,
            ended_by=CallEndedBy.STAFF,
        )
    except CallInvalidTransition as error:
        raise CallConflict("Звонок уже нельзя отменить") from error


def active_call_for_conversation(conversation: Conversation) -> CallSession | None:
    return (
        CallSession.objects.filter(
            conversation=conversation,
            status__in=UNFINISHED_CALL_STATUSES,
        )
        .select_related("initiated_by")
        .prefetch_related("participants")
        .first()
    )


# --- Web Chat: приглашение доставляется поллингом виджета по session identity ---


def webchat_active_call(identity: ConnectionIdentity) -> CallSession | None:
    return (
        CallSession.objects.filter(
            invite__connection_identity=identity,
            status__in=UNFINISHED_CALL_STATUSES,
        )
        .select_related("invite", "initiated_by")
        .first()
    )


@transaction.atomic
def open_call_for_identity(*, identity: ConnectionIdentity) -> ResolvedInvite:
    call = webchat_active_call(identity)
    if call is None:
        raise CallTokenError("Активное приглашение не найдено")
    invite = CallInvite.objects.select_for_update().get(call_session=call)
    if invite.expires_at <= timezone.now():
        raise CallTokenError("Активное приглашение не найдено")
    if invite.opened_at is None:
        invite.opened_at = timezone.now()
        invite.save(update_fields=["opened_at"])
    access_token = issue_call_access_token(
        call_session_id=call.id,
        side=ParticipantSide.CUSTOMER,
        subject_id=str(invite.id),
    )
    return ResolvedInvite(invite=invite, customer_access_token=access_token)


def decline_call_for_identity(*, identity: ConnectionIdentity) -> CallSession:
    call = webchat_active_call(identity)
    if call is None:
        raise CallTokenError("Активное приглашение не найдено")
    try:
        return transition_call(
            call_session_id=call.id,
            target_status=CallStatus.DECLINED,
            ended_by=CallEndedBy.CUSTOMER,
        )
    except CallInvalidTransition as error:
        raise CallConflict("Приглашение уже нельзя отклонить") from error
