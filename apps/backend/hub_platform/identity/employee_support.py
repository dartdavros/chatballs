import secrets
import string

from rest_framework.request import Request

from hub_platform.identity.models import EmployeeProfile


def employee_payload(profile: EmployeeProfile) -> dict[str, object]:
    return {
        "id": profile.user_id,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "role": profile.role,
        "phone": profile.phone,
        "department": profile.department.code if profile.department else None,
        "isActive": profile.user.is_active,
        "isBlocked": profile.is_blocked,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
    }


def get_owned_profile(request: Request, user_id: int) -> EmployeeProfile | None:
    owner_profile = request.user.employee_profile
    try:
        return EmployeeProfile.objects.select_related("user", "department").get(
            user_id=user_id,
            organization=owner_profile.organization,
        )
    except EmployeeProfile.DoesNotExist:
        return None


def temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Temp-" + "".join(secrets.choice(alphabet) for _ in range(14)) + "!"
