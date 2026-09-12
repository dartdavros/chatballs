from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.i18n import current_language, t
from chatballs.identity.avatars import own_avatar_url
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.policy import get_effective_access
from chatballs.identity.sessions import revoke_user_sessions
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user


def validation_response(error: ValidationError) -> Response:
    """Ошибки формы полями: мастер первого запуска и регистрация по приглашению."""

    if hasattr(error, "message_dict"):
        errors = {
            key: messages[0] if isinstance(messages, list) else str(messages)
            for key, messages in error.message_dict.items()
        }
        # validate_password кладёт сообщения без ключа поля.
        if "__all__" in errors:
            errors["password"] = " ".join(error.message_dict["__all__"])
            del errors["__all__"]
        detail = next(iter(errors.values()), t("setup.check_fields"))
        return Response({"detail": detail, "errors": errors}, status=400)
    message = " ".join(error.messages)
    return Response({"detail": message, "errors": {"password": message}}, status=400)


def _user_payload(user: HumanUser) -> dict[str, object]:
    memberships = []
    routes = membership_routes_for_user(user.id)
    for route in routes:
        # Организация читается вместе с членством внутри её контекста: роль
        # app не видит чужие строки организаций (tenancy/0033).
        with tenant_atomic(route.organization_id):
            membership = (
                OrganizationMembership.objects.select_related("organization")
                .filter(
                    id=route.resource_id,
                    user=user,
                    organization_id=route.organization_id,
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
        # Личный выбор языка: пустая строка — «как в организации». Отдельно
        # отдаётся язык, на котором интерфейс открывается прямо сейчас, — он
        # уже разрешён по цепочке профиль → организация → установка, и
        # фронтенду не нужно повторять это правило у себя.
        "uiLanguage": user.ui_language,
        "language": current_language(),
        "avatarUrl": own_avatar_url(user),
        # Администратор установки видит раздел «Платформа» и хранилище
        # файлов: это свойства инсталляции, а не организации.
        "isInstanceAdmin": user.is_instance_admin,
        "memberships": memberships,
    }


def _challenge_payload(user: HumanUser) -> dict[str, object]:
    return {
        "email": user.email,
        "fullName": user.full_name,
    }


def _revoke_other_user_sessions(request: Request) -> int:
    return revoke_user_sessions(request.user.id, except_session_key=request.session.session_key)
