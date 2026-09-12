"""Операционные данные: звонки (с метриками, участниками и приглашением),
уведомления всех типов, привязки уведомителя к мессенджеру."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from chatballs.calls.models import (
    CallConnectionType,
    CallEndedBy,
    CallInvite,
    CallMetric,
    CallParticipant,
    CallSession,
    CallStatus,
    InviteDeliveryStatus,
    ParticipantConnectionState,
    ParticipantSide,
)
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, moment, now
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.notifications.models import (
    MessengerBinding,
    MessengerBindingCode,
    Notification,
    NotificationAudience,
    NotificationLevel,
    NotificationRead,
)
from chatballs.tenancy.context import TenantContext

FINISHED = {
    CallStatus.ENDED,
    CallStatus.DECLINED,
    CallStatus.CANCELLED,
    CallStatus.MISSED,
    CallStatus.FAILED,
    CallStatus.EXPIRED,
}


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("operations", refs.language)
    current = now()
    for item in data.get("calls", []):
        _ensure_call(refs, item, current)
    for item in data.get("notifications", []):
        _ensure_notification(refs, item, current)
    for item in data.get("messengerBindings", []):
        MessengerBinding.objects.get_or_create(
            user=refs.users[item["user"]],
            integration=refs.integrations[item["connection"]],
            defaults={
                "organization": refs.organization,
                "external_chat_id": item["externalChatId"],
                "push_types": item.get("pushTypes", []),
            },
        )
    for item in data.get("messengerBindingCodes", []):
        MessengerBindingCode.objects.get_or_create(
            code=item["code"],
            defaults={
                "organization": refs.organization,
                "user": refs.users[item["user"]],
                "integration": refs.integrations[item["connection"]],
                "expires_at": current + timedelta(minutes=item.get("expiresInMinutes", 15)),
            },
        )


def _ensure_call(refs: DemoRefs, item: dict, current) -> None:
    conversation = refs.conversations[item["conversation"]]
    initiator = refs.users[item["initiatedBy"]]
    if CallSession.objects.filter(conversation=conversation, initiated_by=initiator, kind=item.get("kind", "AUDIO")).exists():
        return
    started = moment(item, current) or current - timedelta(minutes=10)
    status = item.get("status", CallStatus.ENDED)
    session = CallSession.objects.create(
        organization=refs.organization,
        conversation=conversation,
        initiated_by=initiator,
        status=status,
        kind=item.get("kind", "AUDIO"),
        delivery_connection=refs.integrations.get(item.get("deliveryConnection")),
    )
    backdate(session, started, "requested_at")
    if status == CallStatus.ENDED:
        accepted = started + timedelta(seconds=8)
        session.accepted_at = accepted
        session.connected_at = accepted
        session.ended_at = started + timedelta(seconds=item.get("durationSeconds", 120))
        session.ended_by = item.get("endedBy", CallEndedBy.STAFF)
        session.save(update_fields=["accepted_at", "connected_at", "ended_at", "ended_by", "updated_at"])
        _ensure_metric(session, item)
    elif status in (CallStatus.DECLINED, CallStatus.MISSED, CallStatus.EXPIRED, CallStatus.CANCELLED):
        session.ended_at = started + timedelta(seconds=45)
        session.ended_by = item.get("endedBy", "")
        session.save(update_fields=["ended_at", "ended_by", "updated_at"])

    identity = refs.identities.get(item.get("contactIdentity"))
    if identity is not None:
        CallParticipant.objects.create(
            organization=refs.organization,
            call_session=session,
            side=ParticipantSide.CUSTOMER,
            connection_identity=identity,
            joined_at=session.connected_at,
            left_at=session.ended_at,
            last_connection_state=ParticipantConnectionState.DISCONNECTED,
        )
    CallParticipant.objects.create(
        organization=refs.organization,
        call_session=session,
        side=ParticipantSide.STAFF,
        user=initiator,
        joined_at=session.connected_at,
        left_at=session.ended_at,
        last_connection_state=ParticipantConnectionState.DISCONNECTED,
    )
    invite = item.get("invite")
    if invite is not None and identity is not None:
        token_hash = hashlib.sha256(f"demo-invite-{session.id}".encode()).hexdigest()
        call_invite = CallInvite.objects.create(
            organization=refs.organization,
            call_session=session,
            connection_identity=identity,
            token_hash=token_hash,
            expires_at=started + timedelta(minutes=invite.get("expiredMinutesAfter", 2)),
            opened_at=None,
            responded_at=None,
            delivery_status=InviteDeliveryStatus.SENT
            if invite.get("deliveryStatus", "SENT") in ("SENT", "DELIVERED")
            else invite.get("deliveryStatus"),
        )
        backdate(call_invite, started)
    refs.calls[item["key"]] = session


def _ensure_metric(session: CallSession, item: dict) -> None:
    metrics = item.get("metrics")
    if not metrics:
        return
    CallMetric.objects.create(
        organization=session.organization,
        call_session=session,
        side=ParticipantSide.STAFF,
        connection_type=metrics.get("connectionType", CallConnectionType.DIRECT),
        local_candidate_type=metrics.get("localCandidateType", "host"),
        remote_candidate_type=metrics.get("remoteCandidateType", "srflx"),
        round_trip_ms=metrics.get("roundTripMs"),
    )


def _ensure_notification(refs: DemoRefs, item: dict, current) -> None:
    conversation = refs.conversations.get(item.get("targetConversation"))
    dedup_key = f"demo:{item['type']}:{item.get('targetConversation') or item['title']}"
    notification, created = Notification.objects.get_or_create(
        organization=refs.organization,
        dedup_key=dedup_key,
        defaults={
            "type": item["type"],
            "level": item.get("level", NotificationLevel.INFO),
            "title": item["title"],
            "body": item.get("body", ""),
            "target_route": item.get("targetRoute", ""),
            "target_id": str(conversation.id) if conversation is not None else item.get("targetId", ""),
            "audience": item.get("audience", NotificationAudience.ALL),
            "recipient_user": refs.users.get(item.get("recipientUser")),
        },
    )
    if not created:
        return
    backdate(notification, moment(item, current) or current)
    for reader_key in item.get("readBy", []):
        user = refs.users.get(reader_key)
        if user is not None:
            NotificationRead.objects.get_or_create(
                notification=notification, user=user, defaults={"organization": refs.organization}
            )
