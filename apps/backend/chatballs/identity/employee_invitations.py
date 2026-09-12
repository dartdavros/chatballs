"""Ожидающие приглашения в списке сотрудников (кадры E1/E2, статус «Приглашён»).

Приглашение существующей учётной записи ещё не членство, но администратор
должен его видеть там же, где сотрудников: строкой с той же ролью, должностью
и группами, что придут после принятия. Отсюда же приглашение отправляют ещё
раз или отзывают.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.employee_selectors import ROLE_ANY
from chatballs.identity.governance import can_create_role
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.invitation_service import (
    MEMBERSHIP_INVITATION_REQUESTED,
    MEMBERSHIP_INVITATION_TTL,
)
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.identity.policy import has_capability_any_scope


def _pending(organization_id: int):
    return OrganizationInvitation.objects.filter(
        organization_id=organization_id,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    )


def pending_invitations_payload(organization: Organization, params) -> list[dict[str, object]]:
    """Строки приглашений с теми же фильтрами, что у списка сотрудников."""

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


def _load_for_action(request: Request, invitation_id: int) -> OrganizationInvitation | Response:
    actor: OrganizationMembership = request.tenant_context.membership
    if not has_capability_any_scope(actor, "employees.manage"):
        return Response({"detail": t("admin.not_allowed")}, status=403)
    invitation = _pending(actor.organization_id).filter(pk=invitation_id).first()
    if invitation is None:
        return Response({"detail": t("identity.invitation_invalid")}, status=404)
    # Приглашение с ролью, которую актор выдать не вправе, ему и не отозвать.
    if not can_create_role(actor, invitation.role):
        return Response({"detail": t("admin.not_allowed")}, status=403)
    return invitation


class InvitationResendView(APIView):
    """Отправить письмо ещё раз: срок продлевается, токен выпускает воркер."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, invitation_id: int) -> Response:
        loaded = _load_for_action(request, invitation_id)
        if isinstance(loaded, Response):
            return loaded
        loaded.expires_at = timezone.now() + MEMBERSHIP_INVITATION_TTL
        loaded.save(update_fields=["expires_at"])
        record_audit_event(
            action="identity.employee_invited",
            actor=request.user,
            organization=loaded.organization,
            object_type="OrganizationInvitation",
            object_id=str(loaded.id),
            payload={"role": loaded.role, "resend": True},
            request=request,
        )
        enqueue_event(
            DomainEvent(
                aggregate_type="OrganizationInvitation",
                aggregate_id=str(loaded.id),
                event_type=MEMBERSHIP_INVITATION_REQUESTED,
                payload={"invitationId": loaded.id},
                tenant_context=request.tenant_context,
            )
        )
        return Response({"ok": True})


class InvitationRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, invitation_id: int) -> Response:
        loaded = _load_for_action(request, invitation_id)
        if isinstance(loaded, Response):
            return loaded
        loaded.revoked_at = timezone.now()
        loaded.save(update_fields=["revoked_at"])
        record_audit_event(
            action="identity.invitation_revoked",
            actor=request.user,
            organization=loaded.organization,
            object_type="OrganizationInvitation",
            object_id=str(loaded.id),
            payload={"role": loaded.role},
            request=request,
        )
        return Response({"ok": True})
