from rest_framework.request import Request

from hub_platform.identity.membership_context import single_membership_for_user
from hub_platform.identity.models import HumanUser
from hub_platform.identity.policy import get_effective_access
from hub_platform.identity.sessions import revoke_user_sessions


def _user_payload(user: HumanUser) -> dict[str, object]:
    profile = single_membership_for_user(user)
    if profile is None:
        raise ValueError("An explicit organization context is required")
    payload = {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
        "positionTitle": profile.position_title,
        "organizationName": profile.organization.name,
        "organization": profile.organization.slug,
        "department": profile.primary_department.code if profile.primary_department else None,
        "mustChangePassword": user.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": user.totp_enabled,
    }
    payload.update(get_effective_access(profile))
    return payload


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    profile = single_membership_for_user(user)
    if profile is None:
        raise ValueError("An explicit organization context is required")
    return {
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
    }


def _revoke_other_user_sessions(request: Request) -> int:
    return revoke_user_sessions(request.user.id, except_session_key=request.session.session_key)
