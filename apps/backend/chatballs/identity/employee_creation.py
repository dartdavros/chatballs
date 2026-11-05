"""Employee creation and membership invitation shared with native actions."""

from django.db import transaction

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_access import set_groups
from chatballs.identity.employee_outcomes import EmployeeOutcome, denied, rejected
from chatballs.identity.employee_password import clean_password_mode, issue_initial_password
from chatballs.identity.employee_support import employee_payload
from chatballs.identity.employee_validation import (
    ASSIGNABLE_ROLES,
    clean_position_title,
    resolve_groups,
)
from chatballs.identity.event_handlers import INITIAL_ACCESS_REQUESTED
from chatballs.identity.governance import EmployeeAction, can_create_role
from chatballs.identity.invitation_service import invite_existing_user
from chatballs.identity.models import EmployeeRole, HumanUser, OrganizationMembership


@transaction.atomic
def create_employee(context, body, *, request=None):
    actor = context.membership
    email = HumanUser.objects.normalize_email(str(body.get("email", "")))
    full_name = str(body.get("fullName", "")).strip()
    phone = str(body.get("phone", "")).strip()
    provided_password = str(body.get("temporaryPassword", ""))
    # Кадры E5/E6: пароль первичного доступа письмом либо показать один раз.
    password_mode = clean_password_mode(body.get("passwordMode"))
    position_title, position_error = clean_position_title(body.get("positionTitle"))
    requested_role = str(body.get("role", EmployeeRole.EMPLOYEE))

    if requested_role not in ASSIGNABLE_ROLES:
        return rejected(t("admin.invalid_role"))
    if not can_create_role(actor, requested_role):
        return denied(
            context, None, f"{EmployeeAction.CREATE}:{requested_role}", request=request
        )
    if not email:
        return rejected(t("admin.email_required"))
    if not full_name:
        return rejected(t("admin.full_name_required"))
    if position_error:
        return rejected(position_error)
    if provided_password:
        return rejected(t("admin.temporary_passwords_unsupported"))
    if password_mode is None:
        return rejected(t("admin.unknown_password_mode"))
    groups, groups_error = resolve_groups(actor.organization, body.get("groupIds"))
    if groups_error:
        return rejected(groups_error)

    existing = HumanUser.objects.filter(email=email).first()
    if existing is not None:
        # Учётная запись глобальная, а вход в организацию — по согласию
        # человека: вместо «e-mail занят» уходит приглашение с той же ролью
        # и должностью, членство появится после его принятия. В своей
        # организации адрес и правда занят.
        if not existing.is_active or OrganizationMembership.objects.filter(
            user=existing, organization=actor.organization
        ).exists():
            return rejected(t("admin.email_taken"))
        invite_existing_user(
            organization=actor.organization,
            user=existing,
            role=requested_role,
            position_title=position_title,
            phone=phone,
            groups=groups or [],
            created_by=actor,
            context=context,
            request=request,
        )
        return EmployeeOutcome({"employee": None, "password": None, "invited": True})

    user = HumanUser.objects.create_user(
        email=email,
        password=None,
        full_name=full_name,
        is_staff=False,
        is_superuser=False,
        must_change_password=True,
    )
    profile = OrganizationMembership.objects.create(
        user=user,
        organization=actor.organization,
        role=requested_role,
        position_title=position_title,
        phone=phone,
    )
    if groups:
        set_groups(profile, groups)
    password = issue_initial_password(user) if password_mode == "show" else None
    record_audit_event(
        action="identity.employee_created",
        actor=context.actor_user,
        organization=actor.organization,
        object_type="HumanUser",
        object_id=str(user.id),
        payload={"role": requested_role, "passwordMode": password_mode},
        request=request,
    )
    if password_mode == "mail":
        enqueue_event(
            DomainEvent(
                aggregate_type="HumanUser",
                aggregate_id=str(user.id),
                event_type=INITIAL_ACCESS_REQUESTED,
                payload={"userId": user.id},
                tenant_context=context,
            )
        )
    return EmployeeOutcome(
        {"employee": employee_payload(profile, actor), "password": password},
    )
