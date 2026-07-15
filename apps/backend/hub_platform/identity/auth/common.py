from rest_framework.request import Request

from hub_platform.identity.models import HumanUser
from hub_platform.identity.policy import get_effective_access
from hub_platform.identity.sessions import revoke_user_sessions


def _user_payload(user: HumanUser) -> dict[str, object]:
    memberships = []
    active_memberships = (
        user.memberships.filter(blocked_at__isnull=True)
        .select_related("organization", "primary_department")
        .order_by("organization__name", "id")
    )
    for membership in active_memberships:
        membership_payload = {
            "id": membership.id,
            "organizationPublicId": str(membership.organization.public_id),
            "organization": membership.organization.slug,
            "organizationName": membership.organization.name,
            "role": membership.role,
            "positionTitle": membership.position_title,
            "department": (
                membership.primary_department.code if membership.primary_department else None
            ),
            "totpRequired": membership.totp_required,
        }
        membership_payload.update(get_effective_access(membership))
        memberships.append(membership_payload)
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "mustChangePassword": user.must_change_password,
        "totpEnabled": user.totp_enabled,
        "memberships": memberships,
    }


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    return {
        "email": user.email,
        "fullName": user.full_name,
    }


def _revoke_other_user_sessions(request: Request) -> int:
    return revoke_user_sessions(request.user.id, except_session_key=request.session.session_key)
