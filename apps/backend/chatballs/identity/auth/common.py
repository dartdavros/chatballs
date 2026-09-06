from django.conf import settings
from rest_framework.request import Request

from chatballs.identity.avatars import own_avatar_url
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.identity.policy import get_effective_access
from chatballs.identity.sessions import revoke_user_sessions
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user


def _user_payload(user: HumanUser) -> dict[str, object]:
    memberships = []
    routes = membership_routes_for_user(user.id)
    organizations = Organization.objects.in_bulk(
        [route.organization_id for route in routes]
    )
    for route in routes:
        organization = organizations.get(route.organization_id)
        if organization is None:
            continue
        with tenant_atomic(organization.id):
            membership = (
                OrganizationMembership.objects.select_related("organization")
                .filter(
                    id=route.resource_id,
                    user=user,
                    organization=organization,
                    blocked_at__isnull=True,
                )
                .first()
            )
            if membership is None:
                continue
            membership_payload = {
                "id": membership.id,
                "organizationPublicId": str(membership.organization.public_id),
                "organization": membership.organization.slug,
                "organizationName": membership.organization.name,
                "organizationLogoUrl": (
                    f"/api/v1/organizations/{membership.organization.public_id}"
                    "/company/administration/logo/"
                    if membership.organization.logo
                    else None
                ),
                "role": membership.role,
                "positionTitle": membership.position_title,
                "totpRequired": membership.totp_required,
                # «в организации с …» в шапке «Профиля» (кадр P1).
                "joinedAt": membership.created_at.isoformat(),
            }
            membership_payload.update(get_effective_access(membership))
            memberships.append(membership_payload)
    memberships.sort(key=lambda item: (str(item["organizationName"]), int(item["id"])))
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "mustChangePassword": user.must_change_password,
        "totpEnabled": user.totp_enabled,
        "totpLastUsedAt": user.totp_last_used_at.isoformat() if user.totp_last_used_at else None,
        "deliveryMode": settings.CHATBALLS_DELIVERY_MODE,
        "uiTheme": user.ui_theme,
        "uiAccent": user.ui_accent,
        "avatarUrl": own_avatar_url(user),
        "memberships": memberships,
    }


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    return {
        "email": user.email,
        "fullName": user.full_name,
    }


def _revoke_other_user_sessions(request: Request) -> int:
    return revoke_user_sessions(request.user.id, except_session_key=request.session.session_key)
