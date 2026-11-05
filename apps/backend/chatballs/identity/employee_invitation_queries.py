"""Ожидающие приглашения в списке сотрудников (кадры E1/E2, статус «Приглашён»).

Приглашение существующей учётной записи ещё не членство, но администратор
должен его видеть там же, где сотрудников: строкой с той же ролью, должностью
и группами, что придут после принятия. Отсюда же приглашение отправляют ещё
раз или отзывают.
"""

from __future__ import annotations

from django.utils import timezone

from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.employee_selectors import ROLE_ANY
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.models import HumanUser, Organization


def _pending(organization_id: int):
    return OrganizationInvitation.objects.filter(
        organization_id=organization_id,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    )


def pending_invitations_payload(organization: Organization, params) -> list[dict[str, object]]:
    """Строки приглашений с теми же фильтрами, что у списка сотрудников."""
    # До принятия приглашения членства нет, а значит нет и рабочего статуса:
    # под фильтр по статусу приглашение не подходит никогда.
    if params.get("workStatus") not in (None, "", ROLE_ANY):
        return []

    invitations = list(_pending(organization.id).order_by("email"))
    if not invitations:
        return []
    users = {
        user.email.lower(): user
        for user in HumanUser.objects.filter(
            email__in=[invitation.email for invitation in invitations]
        )
    }
    group_ids = {gid for invitation in invitations for gid in invitation.group_ids}
    groups = {
        group.id: group
        for group in EmployeeGroup.objects.filter(organization=organization, id__in=group_ids)
    }
    role = params.get("role")
    group_filter = params.get("group")
    query = params.get("q", "").strip().lower()
    rows: list[dict[str, object]] = []
    for invitation in invitations:
        user = users.get(invitation.email.lower())
        if user is None:
            continue
        if role and role != ROLE_ANY and invitation.role != role:
            continue
        if group_filter and group_filter != ROLE_ANY and str(group_filter).isdigit():
            if int(group_filter) not in invitation.group_ids:
                continue
        haystack = f"{user.full_name} {user.email} {invitation.position_title}".lower()
        if query and query not in haystack:
            continue
        rows.append(
            {
                "id": invitation.id,
                "email": user.email,
                "fullName": user.full_name,
                "avatarUrl": user_avatar_url(user, organization.public_id),
                "role": invitation.role,
                "positionTitle": invitation.position_title,
                "phone": invitation.phone,
                "groups": [
                    {"id": gid, "name": groups[gid].name}
                    for gid in invitation.group_ids
                    if gid in groups
                ],
                "invitedAt": invitation.created_at.isoformat(),
                "expiresAt": invitation.expires_at.isoformat(),
            }
        )
    return rows
