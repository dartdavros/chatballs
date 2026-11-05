"""Employee profile and access changes retain the same governance rules."""

from django.db import transaction

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_access import (
    resolve_supervised_groups,
    set_groups,
    update_employee_access,
)
from chatballs.identity.employee_outcomes import EmployeeOutcome, denied, rejected
from chatballs.identity.employee_support import employee_payload, profile_for
from chatballs.identity.employee_validation import (
    ASSIGNABLE_ROLES,
    clean_position_title,
    resolve_groups,
)
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.models import HumanUser


@transaction.atomic
def update_employee(context, user_id, body, *, request=None):
    actor = context.membership
    profile = profile_for(context, user_id, for_update=True)
    if profile is None:
        return rejected(t("admin.employee_not_found"), 'not_found')
    if not can_manage_employee(actor, profile, EmployeeAction.UPDATE_PROFILE):
        return denied(context, profile, EmployeeAction.UPDATE_PROFILE, request=request)

    full_name = str(body.get("fullName", "")).strip()
    email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
    phone = str(body.get("phone", "")).strip()
    position_title, position_error = clean_position_title(
        body.get("positionTitle", profile.position_title)
    )
    requested_role = str(body.get("role", profile.role))

    if not full_name:
        return rejected(t("admin.full_name_required"), 'invalid')
    if not email:
        return rejected(t("admin.email_required"), 'invalid')
    if HumanUser.objects.exclude(id=profile.user_id).filter(email=email).exists():
        return rejected(t("admin.email_taken"), 'invalid')
    if position_error:
        return rejected(position_error, 'invalid')

    role_changing = requested_role != profile.role
    if role_changing:
        if requested_role not in ASSIGNABLE_ROLES:
            return rejected(t("admin.invalid_role"), 'invalid')
        if not can_manage_employee(actor, profile, EmployeeAction.CHANGE_ROLE):
            return denied(context, profile, EmployeeAction.CHANGE_ROLE, request=request)

    groups, groups_error = resolve_groups(profile.organization, body.get("groupIds"))
    if groups_error:
        return rejected(groups_error, 'invalid')
    if groups is not None and not can_manage_employee(
        actor, profile, EmployeeAction.CHANGE_GROUPS
    ):
        return denied(context, profile, EmployeeAction.CHANGE_GROUPS, request=request)

    supervised_groups, supervision_error = resolve_supervised_groups(
        profile, requested_role, body
    )
    if supervision_error:
        return rejected(supervision_error, 'invalid')
    if supervised_groups is not None and not can_manage_employee(
        actor, profile, EmployeeAction.CHANGE_SUPERVISED_GROUPS
    ):
        return denied(context, profile, EmployeeAction.CHANGE_SUPERVISED_GROUPS, request=request)

    profile.user.full_name = full_name
    profile.user.email = email
    profile.user.save(update_fields=["full_name", "email"])
    profile.phone = phone
    profile.position_title = position_title
    profile.save(update_fields=["phone", "position_title"])
    update_employee_access(request, profile, requested_role, supervised_groups, actor=context.actor_user)
    if groups is not None:
        set_groups(profile, groups)

    record_audit_event(
        action="identity.employee_updated",
        actor=context.actor_user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    if groups is not None:
        record_audit_event(
            action="identity.employee_groups_changed",
            actor=context.actor_user,
            organization=profile.organization,
            object_type="HumanUser",
            object_id=str(profile.user_id),
            payload={"groupIds": [group.id for group in groups]},
            request=request,
        )
    return EmployeeOutcome({"employee": employee_payload(profile, actor)})
