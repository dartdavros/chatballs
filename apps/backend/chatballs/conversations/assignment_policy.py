"""Explicit organization policy; technical presence never restricts assignment."""

from django.db import models
from rest_framework.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.work_status_codes import WorkStatus


class AssignmentPolicy(models.Model):
    organization = models.OneToOneField("identity.Organization", on_delete=models.CASCADE)
    ready = models.BooleanField()
    busy = models.BooleanField()
    break_allowed = models.BooleanField()
    unavailable = models.BooleanField()

    def __str__(self):
        return f"AssignmentPolicy({self.organization_id})"


STATUS_FIELDS = {
    WorkStatus.READY: "ready", WorkStatus.BUSY: "busy",
    WorkStatus.BREAK: "break_allowed", WorkStatus.UNAVAILABLE: "unavailable",
}


def policy_payload(policy):
    return {status: getattr(policy, field) for status, field in STATUS_FIELDS.items()}


def validate_policy(data):
    if (not isinstance(data, dict) or set(data) != set(STATUS_FIELDS)
            or any(type(value) is not bool for value in data.values())):
        raise ValidationError(t("transfers.policy_invalid"))
    return {field: data[status] for status, field in STATUS_FIELDS.items()}


def assignment_settings(context, changes=None):
    from chatballs.conversations.transfer_services import require_reason_management
    from chatballs.identity.models import Organization
    from chatballs.tenancy.database import tenant_atomic

    require_reason_management(context)
    if changes is None:
        policy = AssignmentPolicy.objects.filter(organization_id=context.organization_id).first()
    else:
        clean = validate_policy(changes)
        with tenant_atomic(context):
            Organization.objects.select_for_update().get(pk=context.organization_id)
            policy, _ = AssignmentPolicy.objects.update_or_create(
                organization_id=context.organization_id, defaults=clean)
    return {"allowedStatuses": policy_payload(policy) if policy else None}


def policy_for(context, lock=False):
    policies = AssignmentPolicy.objects.filter(organization_id=context.organization_id)
    if lock:
        policies = policies.select_for_update()
    policy = policies.first()
    if policy is None:
        raise ValidationError(t("transfers.policy_required"))
    return policy


def assignment_recipient(*, context, user_id, policy):
    # Lock both membership and user: availability, local block and global
    # deactivation must not change between validation and assignment.
    member = OrganizationMembership.objects.select_related("user").select_for_update().filter(
        organization_id=context.organization_id, user_id=user_id,
        blocked_at__isnull=True, user__is_active=True,
    ).first()
    if member is None:
        raise ValidationError(t("admin.employee_not_found"))
    field = STATUS_FIELDS.get(member.work_status)
    if field is None or not getattr(policy, field):
        raise ValidationError(t("transfers.recipient_unavailable"))
    return member.user
