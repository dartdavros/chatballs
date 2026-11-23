"""Dismissal preserves the account and history while closing organization access."""

from functools import partial

from django.db import transaction
from django.utils import timezone

from chatballs.conversations.autonomous_execution import cancel_pending_replies
from chatballs.conversations.domain_events import record_queue_entry
from chatballs.conversations.models import Conversation, LifecycleState
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.conversations.queue import QUEUE_FIELDS, enter_queue
from chatballs.conversations.realtime import notify_conversation_changed
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_outcomes import EmployeeOutcome, denied, rejected
from chatballs.identity.employee_support import employee_payload, profile_for
from chatballs.identity.governance import EmployeeAction, can_manage_employee


@transaction.atomic
def dismiss_employee(context, user_id, body, *, request=None):
    profile = profile_for(context, user_id, for_update=True)
    if profile is None:
        return rejected(t("admin.employee_not_found"), "not_found")
    if not can_manage_employee(context.membership, profile, EmployeeAction.DISMISS):
        return denied(context, profile, EmployeeAction.DISMISS, request=request)
    if body.get("confirmed") is not True:
        return rejected(t("admin.dismiss_confirmation_required"))
    if profile.dismissed_at is not None:
        return EmployeeOutcome({"employee": employee_payload(profile, context.membership)})
    now = timezone.now()
    profile.dismissed_at = now
    profile.blocked_at = profile.blocked_at or now
    profile.save(update_fields=["dismissed_at", "blocked_at"])
    _release_conversations(context, profile, now)
    record_audit_event(
        action="identity.employee_dismissed", actor=context.actor_user,
        organization=context.organization, object_type="HumanUser",
        object_id=str(profile.user_id), request=request,
    )
    return EmployeeOutcome({"employee": employee_payload(profile, context.membership)})


def _release_conversations(context, profile, now):
    participations = ConversationParticipant.objects.filter(
        organization_id=context.organization_id, membership=profile, left_at__isnull=True,
    )
    changed_ids = set(participations.values_list("conversation_id", flat=True))
    participations.update(left_at=now, left_by=context.membership, leave_reason="employee_dismissed")
    conversations = Conversation.objects.select_for_update().filter(
        organization_id=context.organization_id, assigned_operator_id=profile.user_id,
        lifecycle=LifecycleState.OPEN,
    ).order_by("pk")
    for conversation in conversations:
        cancel_pending_replies(conversation)
        entered = enter_queue(conversation, now=now)
        conversation.assigned_operator = None
        conversation.assigned_at = None
        conversation.save(update_fields=[*QUEUE_FIELDS, "assigned_operator", "assigned_at"])
        record_queue_entry(conversation, entered=entered)
        changed_ids.add(conversation.pk)
    for conversation_id in sorted(changed_ids):
        transaction.on_commit(partial(
            notify_conversation_changed, conversation_id, organization_id=context.organization_id,
        ))
