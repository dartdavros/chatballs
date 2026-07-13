import secrets
import string

from rest_framework.request import Request

from hub_platform.identity.governance import employee_management_flags
from hub_platform.identity.models import EmployeeProfile


def employee_payload(
    profile: EmployeeProfile,
    actor: EmployeeProfile | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": profile.user_id,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "role": profile.role,
        "positionTitle": profile.position_title,
        "phone": profile.phone,
        "department": profile.primary_department.code if profile.primary_department else None,
        "isActive": profile.user.is_active,
        "isBlocked": profile.is_blocked,
        "mustChangePassword": profile.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.totp_enabled,
        "accessAssignments": [
            {
                "id": assignment.id,
                "profileId": assignment.access_profile_id,
                "profileName": assignment.access_profile.name,
                "scopeType": assignment.scope_type,
                "departmentId": assignment.department_id,
                "departmentCode": assignment.department.code if assignment.department_id else None,
            }
            for assignment in profile.access_assignments.filter(
                revoked_at__isnull=True, access_profile__is_active=True
            ).select_related("access_profile", "department")
        ],
    }
    # Backend — источник истины для того, какие действия над сотрудником доступны
    # запрашивающему (ADR-HUB-0027): фронтенд скрывает недоступное.
    if actor is not None:
        payload["permissions"] = employee_management_flags(actor, profile)
    return payload


def get_owned_profile(request: Request, user_id: int) -> EmployeeProfile | None:
    owner_profile = request.user.employee_profile
    try:
        return EmployeeProfile.objects.select_related("user", "primary_department").get(
            user_id=user_id,
            organization=owner_profile.organization,
        )
    except EmployeeProfile.DoesNotExist:
        return None


def temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Temp-" + "".join(secrets.choice(alphabet) for _ in range(14)) + "!"
