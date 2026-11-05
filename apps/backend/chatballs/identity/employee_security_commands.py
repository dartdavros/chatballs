"""Security commands preserve governance, one-time credential protocol and audit."""

from django.db import transaction

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_outcomes import EmployeeOutcome, denied, rejected
from chatballs.identity.employee_password import clean_password_mode, reset_employee_password
from chatballs.identity.employee_support import employee_payload, profile_for
from chatballs.identity.governance import EmployeeAction, can_manage_employee
from chatballs.identity.sessions import revoke_user_sessions


@transaction.atomic
def reset_password(context, user_id, body, *, request=None):
    actor = context.membership
    profile = profile_for(context, user_id)
    if profile is None:
        return rejected(t("admin.employee_not_found"), 'not_found')
    if not can_manage_employee(actor, profile, EmployeeAction.RESET_PASSWORD):
        return denied(context, profile, EmployeeAction.RESET_PASSWORD, request=request)
    mode = clean_password_mode(body.get("mode"))
    if mode is None:
        return rejected(t("admin.unknown_password_mode"), 'invalid')
    # Пароль живёт на пользователе, а не на членстве: сбрасывать его из одной
    # организации, когда человек работает и в другой, нельзя.
    if profile.user.memberships.count() > 1:
        return rejected(t("admin.multi_org_self_reset"), 'conflict')
    password = reset_employee_password(
        profile=profile, mode=mode, actor=actor, request=request, context=context
    )
    profile.refresh_from_db()
    return EmployeeOutcome(
        {"employee": employee_payload(profile, actor), "password": password}
    )


@transaction.atomic
def revoke_sessions(context, user_id, body, *, request=None):
    actor = context.membership
    profile = profile_for(context, user_id)
    if profile is None:
        return rejected(t("admin.employee_not_found"), 'not_found')
    if not can_manage_employee(actor, profile, EmployeeAction.TERMINATE_SESSIONS):
        return denied(context, profile, EmployeeAction.TERMINATE_SESSIONS, request=request)
    revoked = revoke_user_sessions(profile.user_id)
    record_audit_event(
        action="identity.employee_sessions_terminated",
        actor=context.actor_user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        payload={"sessionsRevoked": revoked},
        request=request,
    )
    return EmployeeOutcome({"employee": employee_payload(profile, actor), "revoked": revoked})


@transaction.atomic
def block_employee(context, user_id, body, *, request=None):
    actor = context.membership
    profile = profile_for(context, user_id)
    if profile is None:
        return rejected(t("admin.employee_not_found"), 'not_found')
    if not can_manage_employee(actor, profile, EmployeeAction.BLOCK):
        return denied(context, profile, EmployeeAction.BLOCK, request=request)
    profile.block()
    record_audit_event(
        action="identity.employee_blocked",
        actor=context.actor_user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return EmployeeOutcome({"employee": employee_payload(profile, actor)})


@transaction.atomic
def unblock_employee(context, user_id, body, *, request=None):
    actor = context.membership
    profile = profile_for(context, user_id)
    if profile is None:
        return rejected(t("admin.employee_not_found"), 'not_found')
    if not can_manage_employee(actor, profile, EmployeeAction.UNBLOCK):
        return denied(context, profile, EmployeeAction.UNBLOCK, request=request)
    profile.unblock()
    record_audit_event(
        action="identity.employee_unblocked",
        actor=context.actor_user,
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(profile.user_id),
        request=request,
    )
    return EmployeeOutcome({"employee": employee_payload(profile, actor)})
