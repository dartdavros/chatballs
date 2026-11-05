"""Existing queue settings and assignment-return rule stay synchronized."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.conversations.queue_models import QueueEscalationPolicy, policy_for
from chatballs.conversations.rules.models import HandlingRuleKind
from chatballs.conversations.rules.settings import update_rule
from chatballs.i18n import t
from chatballs.identity.policy import ResourceScope, authorize

FIELDS = tuple(QueueEscalationPolicy.DEFAULTS)
MAX_MINUTES = 24 * 60


def policy_payload(policy):
    author = policy.updated_by
    return {**{field: getattr(policy, field) for field in FIELDS},
        "defaults": dict(QueueEscalationPolicy.DEFAULTS),
        "updatedAt": policy.updated_at.isoformat() if policy.updated_at else None,
        "updatedBy": (author.full_name or author.email) if author else ""}


def queue_policy(context, changes=None):
    capability = "settings.view" if changes is None else "settings.manage"
    if not authorize(context.membership, capability, ResourceScope(context.organization_id)):
        raise PermissionDenied({"detail": t("settings.queue_policy_forbidden")})
    policy = policy_for(context.organization)
    changed = []
    for field in FIELDS if changes is not None else ():
        if field not in changes:
            continue
        value = changes[field]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_MINUTES:
            raise ValidationError({"detail": t("settings.queue_minutes_range")})
        if getattr(policy, field) != value:
            setattr(policy, field, value)
            changed.append(field)
    if changed:
        policy.updated_at, policy.updated_by = timezone.now(), context.actor_user
        policy.save(update_fields=[*changed, "updated_at", "updated_by"])
    if "assignment_timeout_minutes" in changed:
        update_rule(context=context, kind=HandlingRuleKind.ASSIGNMENT_RETURN,
            changes={"delay_minutes": policy.assignment_timeout_minutes})
    return policy_payload(policy)
