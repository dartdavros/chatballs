"""Composition transactions and protected participation history (SPEC-0026)."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.conversations.participant_notifications import queue_specialist_notice
from chatballs.conversations.realtime import notify_conversation_changed
from chatballs.conversations.selectors import conversation_for_context
from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.support_artifacts import record_demo_support_operation
from chatballs.identity.models import Organization, OrganizationMembership


def participation_history(*, context, conversation_id):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    return ConversationParticipant.objects.filter(
        organization_id=context.organization_id, conversation=conversation,
    ).select_related("membership__user", "joined_by__user", "left_by__user")


def _reason(reason):
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError({"reason": t("participants.reason_required")})
    return reason.strip()


def _composition(*, context, conversation_id):
    # Organization first: serializes concurrent composition changes with changes
    # to the organization limit. Conversation also serializes reply/removal.
    organization = Organization.objects.select_for_update().get(pk=context.organization_id)
    conversation = Conversation.objects.select_for_update().get(
        pk=conversation_id, organization_id=context.organization_id,
    )
    require_conversation_action(context, conversation, "conversations.participants")
    return organization, conversation


def _target(context, membership_id):
    member = OrganizationMembership.objects.select_for_update().filter(
        pk=membership_id, organization_id=context.organization_id,
        blocked_at__isnull=True, user__is_active=True,
    ).first()
    if member is None:
        raise ValidationError({"membershipId": t("admin.employee_not_found")})
    return member


def _notify(conversation):
    transaction.on_commit(lambda: notify_conversation_changed(
        conversation.pk, organization_id=conversation.organization_id,
    ))


@record_demo_support_operation
@transaction.atomic
def add_participant(*, context, conversation_id, membership_id, reason):
    reason = _reason(reason)
    organization, conversation = _composition(context=context, conversation_id=conversation_id)
    member = _target(context, membership_id)
    existing = conversation.participants.active().filter(membership=member).first()
    if existing:
        return existing, False
    if (
        member.user_id != conversation.assigned_operator_id
        and conversation.participants.additional().count() >= organization.additional_participant_limit
    ):
        raise ValidationError({"membershipId": t("participants.limit_reached")})
    participant = ConversationParticipant.objects.create(
        organization_id=context.organization_id, conversation=conversation,
        membership=member, joined_by=context.membership, join_reason=reason,
    )
    queue_specialist_notice(conversation=conversation, participant=participant, context=context)
    _notify(conversation)
    return participant, True


@record_demo_support_operation
@transaction.atomic
def remove_participant(*, context, conversation_id, participant_id, reason):
    reason = _reason(reason)
    _, conversation = _composition(context=context, conversation_id=conversation_id)
    participant = conversation.participants.filter(pk=participant_id).first()
    if participant is None:
        raise Conversation.DoesNotExist
    # Address the participation episode, not just the employee: retrying an old
    # DELETE cannot revoke a later re-join by that employee.
    if participant.left_at is not None:
        return participant, False
    participant.left_at = timezone.now()
    participant.left_by = context.membership
    participant.leave_reason = reason
    participant.save(update_fields=["left_at", "left_by", "leave_reason"])
    _notify(conversation)
    return participant, True
