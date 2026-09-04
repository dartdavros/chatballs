"""Операционные данные: звонки, уведомления, период учёта использования."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from hub_platform.calls.models import (
    CallConnectionType,
    CallEndedBy,
    CallMetric,
    CallParticipant,
    CallSession,
    CallStatus,
    ParticipantConnectionState,
    ParticipantSide,
)
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.notifications.models import (
    Notification,
    NotificationAudience,
    NotificationLevel,
    NotificationRead,
)
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("operations")
    _ensure_calls(refs, data.get("calls", []))
    _ensure_notifications(refs, data.get("notifications", []))


def _ensure_calls(refs: DemoRefs, items: list[dict]) -> None:
    now = timezone.now()
    for item in items:
        conversation = refs.conversations[item["conversation"]]
        initiator = refs.users[item["initiatedBy"]]
        if (
            CallSession.objects.filter(conversation=conversation)
            .exclude(status__in=("ENDED", "DECLINED", "CANCELLED", "MISSED", "FAILED", "EXPIRED"))
            .exists()
        ):
            continue  # незавершённый звонок уже есть — не трогаем

        started = now - timedelta(minutes=item.get("minutesAgo", 10))
        session, created = CallSession.objects.get_or_create(
            conversation=conversation,
            defaults={
                "organization": refs.organization,
                "initiated_by": initiator,
                "status": item.get("status", CallStatus.ENDED),
                "delivery_connection": refs.integrations.get(item.get("deliveryConnection")),
            },
        )
        if not created:
            continue
        if session.status == CallStatus.ENDED:
            accepted = started + timedelta(seconds=8)
            session.accepted_at = accepted
            session.connected_at = accepted
            session.ended_at = started + timedelta(seconds=item.get("durationSeconds", 120))
            session.ended_by = item.get("endedBy", CallEndedBy.STAFF)
            call_fields = ["accepted_at", "connected_at", "ended_at", "ended_by", "updated_at"]
            session.save(update_fields=call_fields)
            _ensure_call_metric(session, item)

        contact_identity = refs.identities.get(item.get("contactIdentity"))
        if contact_identity is not None:
            CallParticipant.objects.get_or_create(
                call_session=session,
                side=ParticipantSide.CUSTOMER,
                defaults={
                    "connection_identity": contact_identity,
                    "joined_at": session.connected_at,
                    "left_at": session.ended_at,
                    "last_connection_state": ParticipantConnectionState.DISCONNECTED,
                },
            )
            CallParticipant.objects.get_or_create(
                call_session=session,
                side=ParticipantSide.STAFF,
                defaults={
                    "user": initiator,
                    "joined_at": session.connected_at,
                    "left_at": session.ended_at,
                    "last_connection_state": ParticipantConnectionState.DISCONNECTED,
                },
            )


def _ensure_call_metric(session: CallSession, item: dict) -> None:
    metrics = item.get("metrics")
    if not metrics:
        return
    CallMetric.objects.update_or_create(
        call_session=session,
        side=ParticipantSide.STAFF,
        defaults={
            "connection_type": metrics.get("connectionType", CallConnectionType.DIRECT),
            "local_candidate_type": metrics.get("localCandidateType", "host"),
            "remote_candidate_type": metrics.get("remoteCandidateType", "srflx"),
            "round_trip_ms": metrics.get("roundTripMs"),
        },
    )


def _ensure_notifications(refs: DemoRefs, items: list[dict]) -> None:
    for item in items:
        dedup_key = f"demo:{item['type']}:{item.get('sourceId', '')}"
        notification, created = Notification.objects.get_or_create(
            organization=refs.organization,
            dedup_key=dedup_key,
            defaults={
                "type": item["type"],
                "level": item.get("level", NotificationLevel.INFO),
                "title": item["title"],
                "body": item.get("body", ""),
                "target_route": item.get("targetRoute", ""),
                "target_id": item.get("targetId", ""),
                "audience": item.get("audience", NotificationAudience.ALL),
                "recipient_user": refs.users.get(item.get("recipientUser")),
            },
        )
        if created and item.get("readBy"):
            user = refs.users.get(item["readBy"])
            if user is not None:
                NotificationRead.objects.get_or_create(notification=notification, user=user)
