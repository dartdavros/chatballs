from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.employee_availability import employee_availability
from chatballs.identity.governance import employee_management_flags
from chatballs.identity.models import AuditEvent, OrganizationMembership
from chatballs.identity.supervision_models import supervised_groups_payload


def employee_payload(
    profile: OrganizationMembership,
    actor: OrganizationMembership | None = None,
    *,
    include_detail: bool = False,
    availability: dict | None = None,
) -> dict[str, object]:
    # Порядок групп задаёт выборка (employees_for): своя сортировка здесь
    # отменяла бы prefetch и давала запрос на каждого сотрудника в списке.
    groups = [
        {"id": link.group_id, "name": link.group.name}
        for link in profile.group_links.all()
    ]
    payload: dict[str, object] = {
        "id": profile.user_id,
        # Участие в организации: им адресуются права, выданные поверх роли
        # (управление общими шаблонами ответов).
        "membershipId": profile.pk,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "avatarUrl": user_avatar_url(profile.user, profile.organization.public_id),
        "role": str(profile.role),
        "positionTitle": profile.position_title,
        "phone": profile.phone,
        "groups": groups,
        "supervisedGroups": supervised_groups_payload(profile),
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
    # Список передаёт доступность готовой: присутствие читается одним запросом
    # на страницу. Карточка одного сотрудника считает её здесь.
    if availability is None:
        availability = employee_availability(profile.organization_id, [profile])[profile.user_id]
    payload.update(availability)
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


def profile_for(context, user_id: int, *, for_update: bool = False):
    try:
        profiles = (
            OrganizationMembership.objects.select_related("user")
            .prefetch_related("group_links__group", "supervision_links__group")
        )
        if for_update:
            profiles = profiles.select_for_update(of=("self",))
        return profiles.get(user_id=user_id, organization_id=context.organization_id)
    except OrganizationMembership.DoesNotExist:
        return None
