"""Owner-only ownership transfer, shared by HTTP and automation."""

from django.db import transaction

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_access import update_employee_access
from chatballs.identity.employee_outcomes import EmployeeOutcome, denied, rejected
from chatballs.identity.employee_support import employee_payload
from chatballs.identity.employee_validation import ASSIGNABLE_ROLES
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.models import EmployeeRole, OrganizationMembership


@transaction.atomic
def transfer_ownership(context, user_id, body, *, request=None):
    actor = (
        OrganizationMembership.objects.select_for_update(of=("self",))
        .select_related("user")
        .get(pk=context.membership.pk)
    )
    try:
        target = (
            OrganizationMembership.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(user_id=user_id, organization=actor.organization)
        )
    except OrganizationMembership.DoesNotExist:
        return rejected(t("admin.employee_not_found"), 'not_found')

    if not can_manage_employee(actor, target, EmployeeAction.TRANSFER_OWNERSHIP):
        return denied(context, target, EmployeeAction.TRANSFER_OWNERSHIP, request=request)
    if target.is_blocked or not target.user.is_active:
        return rejected(t("admin.target_must_be_active"), 'conflict')

    previous_owner_role = str(body.get("previousOwnerRole", EmployeeRole.ADMIN))
    if previous_owner_role not in ASSIGNABLE_ROLES:
        return rejected(t("admin.previous_owner_role"), 'invalid')

    update_employee_access(request, actor, previous_owner_role, [], actor=context.actor_user)
    update_employee_access(request, target, EmployeeRole.OWNER, [], actor=context.actor_user)

    record_audit_event(
        action="identity.ownership_transferred",
        actor=context.actor_user,
        organization=actor.organization,
        object_type="HumanUser",
        object_id=str(target.user_id),
        payload={
            "from": actor.user_id,
            "to": target.user_id,
            "previousOwnerRole": previous_owner_role,
        },
        request=request,
    )
    return EmployeeOutcome(
        {
            "employee": employee_payload(target, actor),
            "previousOwner": employee_payload(actor, actor),
        }
    )
