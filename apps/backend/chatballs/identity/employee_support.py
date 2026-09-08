from rest_framework.request import Request

from chatballs.identity.governance import employee_management_flags
from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.models import AuditEvent, OrganizationMembership


def employee_payload(
    profile: OrganizationMembership,
    actor: OrganizationMembership | None = None,
    *,
    include_detail: bool = False,
) -> dict[str, object]:
    # Порядок групп задаёт выборка (employees_for): своя сортировка здесь
    # отменяла бы prefetch и давала запрос на каждого сотрудника в списке.
    groups = [
        {"id": link.group_id, "name": link.group.name}
        for link in profile.group_links.all()
    ]
    payload: dict[str, object] = {
        "id": profile.user_id,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "avatarUrl": user_avatar_url(profile.user, profile.organization.public_id),
        "role": profile.role,
        "positionTitle": profile.position_title,
        "phone": profile.phone,
        "groups": groups,
        "createdAt": profile.created_at.isoformat(),
        "lastLogin": profile.user.last_login.isoformat() if profile.user.last_login else None,
        "isActive": profile.user.is_active,
        "isBlocked": profile.is_blocked,
        "mustChangePassword": profile.user.must_change_password,
        # «Последняя смена» пароля в карточке сотрудника (кадр E3).
        "passwordChangedAt": (
            profile.user.password_changed_at.isoformat()
            if profile.user.password_changed_at
            else None
        ),
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.user.totp_enabled,
    }
    # Backend — источник истины для того, какие действия над сотрудником доступны
    # запрашивающему (SPEC-CHATBALLS-0031 §3): фронтенд скрывает недоступное.
    if actor is not None:
        payload["permissions"] = employee_management_flags(actor, profile)
    if include_detail:
        from chatballs.identity.sessions import count_user_sessions

        payload["activeSessionCount"] = count_user_sessions(profile.user_id)
        payload["auditEvents"] = [
            {
                "action": event.action,
                "result": event.result,
                "createdAt": event.created_at.isoformat(),
            }
            for event in AuditEvent.objects.filter(
                organization=profile.organization,
                object_type="HumanUser",
                object_id=str(profile.user_id),
            )[:8]
        ]
    return payload


def get_owned_profile(request: Request, user_id: int) -> OrganizationMembership | None:
    owner_profile = request.tenant_context.membership
    try:
        return (
            OrganizationMembership.objects.select_related("user")
            .prefetch_related("group_links__group")
            .get(user_id=user_id, organization=owner_profile.organization)
        )
    except OrganizationMembership.DoesNotExist:
        return None
