"""Outbox-доставка приглашения на звонок в TG/MAX (SPEC-HUB-0013 §7.2).

Сырой invite token не хранится в БД и payload события: при каждой попытке
доставки token выпускается заново, в БД пишется только hash, а ссылка
/calls/<token> уходит клиенту кнопкой сообщения.
"""

import logging

from django.db import transaction

from chatballs.calls.lifecycle import transition_call
from chatballs.calls.models import CallInvite, CallSession, CallStatus, InviteDeliveryStatus
from chatballs.calls.services import CALL_INVITE_SEND
from chatballs.calls.tokens import issue_invite_token
from chatballs.conversations import transports
from chatballs.events.handlers import register
from chatballs.identity.instance_settings import public_base_url
from chatballs.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

class CallInviteDeliveryError(Exception):
    pass


@register(CALL_INVITE_SEND)
def handle_call_invite_send(payload: dict, context: TenantContext | None) -> None:
    if context is None:
        raise ValueError("Call invite event has no tenant context")
    call_session_id = payload.get("callSessionId")
    with transaction.atomic():
        call = (
            # of=("self",): delivery_connection nullable → LEFT JOIN, который
            # нельзя блокировать; блокируем только строку звонка.
            CallSession.objects.select_for_update(of=("self",))
            .select_related("conversation", "delivery_connection")
            .filter(id=call_session_id, organization=context.organization)
            .first()
        )
        if call is None or call.status != CallStatus.REQUESTED or call.delivery_connection is None:
            # Уже доставлено, отменено или истекло — повтор идемпотентен.
            return
        invite = (
            CallInvite.objects.select_for_update()
            .select_related("connection_identity")
            .get(call_session=call)
        )
        token, token_hash = issue_invite_token()
        invite.token_hash = token_hash
        invite.save(update_fields=["token_hash"])
        call_label = "аудиозвонок" if call.kind == "AUDIO" else "видеозвонок"
        invite_text = f"Приглашаем вас на {call_label}. Нажмите кнопку, чтобы перейти к звонку."
        url = f"{public_base_url()}/calls/{token}?kind={call.kind}"
        sent = transports.send_call_invite(
            call.delivery_connection,
            chat_id=call.conversation.external_chat_id,
            user_id=invite.connection_identity.external_user_id,
            text=invite_text,
            url=url,
        )
        if not sent:
            # Rollback вернёт прежний hash; outbox повторит с новым token.
            raise CallInviteDeliveryError(f"call invite delivery failed for call {call.id}")
        invite.delivery_status = InviteDeliveryStatus.SENT
        invite.save(update_fields=["delivery_status"])
        transition_call(call_session_id=call.id, target_status=CallStatus.RINGING)
