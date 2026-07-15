from rest_framework.request import Request

from hub_platform.identity.governance import employee_management_flags
from hub_platform.identity.models import AuditEvent, OrganizationMembership
from hub_platform.identity.sessions import count_user_sessions


def employee_payload(
    profile: OrganizationMembership,
    actor: OrganizationMembership | None = None,
    *,
    include_detail: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": profile.user_id,
        "email": profile.user.email,
        "fullName": profile.user.full_name,
        "role": profile.role,
        "positionTitle": profile.position_title,
        "phone": profile.phone,
        "department": profile.primary_department.code if profile.primary_department else None,
        "departmentName": profile.primary_department.name if profile.primary_department else None,
        "createdAt": profile.created_at.isoformat(),
        "lastLogin": profile.user.last_login.isoformat() if profile.user.last_login else None,
        "isActive": profile.user.is_active,
        "isBlocked": profile.is_blocked,
        "mustChangePassword": profile.user.must_change_password,
        "totpRequired": profile.totp_required,
        "totpEnabled": profile.user.totp_enabled,
        "accessAssignments": [
            {
                "id": assignment.id,
                "profileId": assignment.access_profile_id,
                "profileName": assignment.access_profile.name,
                "scopeType": assignment.scope_type,
                "departmentId": assignment.department_id,
                "departmentCode": assignment.department.code if assignment.department_id else None,
                "departmentName": assignment.department.name if assignment.department_id else None,
                "capabilities": sorted(
                    assignment.access_profile.capability_links.values_list(
                        "capability_code", flat=True
                    )
                ),
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
    if include_detail:
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
            OrganizationMembership.objects.select_related("user", "primary_department")
            .prefetch_related("access_assignments__access_profile__capability_links")
            .get(user_id=user_id, organization=owner_profile.organization)
        )
    except OrganizationMembership.DoesNotExist:
        return None
