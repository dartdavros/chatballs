from django.contrib.sessions.models import Session
from rest_framework.request import Request

from hub_platform.identity.models import HumanUser


def _user_payload(user: HumanUser) -> dict[str, object]:
    profile = user.employee_profile
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
        "organizationName": profile.organization.name,
        "organization": profile.organization.slug,
        "department": profile.department.code if profile.department else None,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
    }


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    profile = user.employee_profile
    return {
        "email": user.email,
        "fullName": user.full_name,
        "role": profile.role,
    }


def _revoke_other_user_sessions(request: Request) -> int:
    current_key = request.session.session_key
    user_id = str(request.user.id)
    revoked = 0
    for session in Session.objects.all():
        if session.session_key == current_key:
            continue
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == user_id:
            session.delete()
            revoked += 1
    return revoked
