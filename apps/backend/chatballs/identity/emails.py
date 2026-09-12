from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from chatballs.i18n import t
from chatballs.i18n.languages import resolve_language
from chatballs.identity.instance_settings import (
    default_language,
    email_connection,
    email_from_address,
    public_base_url,
)
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.models import HumanUser


def _password_setup_url(user: HumanUser) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    # Ссылка уходит человеку в почту, поэтому строится от адреса установки,
    # который знает сама система, а не от адреса dev-сервера в переменной.
    return f"{public_base_url()}/reset-password?uid={uid}&token={token}"


def _recipient_language(user: HumanUser) -> str:
    """Язык получателя письма, а не того, кто нажал кнопку.

    Приглашение сотруднику отправляет владелец, и язык запроса здесь не при
    чём: письмо читает другой человек. Личный выбор получателя побеждает,
    дальше — язык его организации, дальше — язык установки.
    """

    membership = (
        user.memberships.select_related("organization")
        .filter(blocked_at__isnull=True)
        .order_by("created_at", "id")
        .first()
    )
    return resolve_language(
        user_language=user.ui_language,
        organization_language=membership.organization.language if membership else "",
        instance_language=default_language(),
    )


def send_initial_access_email(user: HumanUser) -> None:
    setup_url = _password_setup_url(user)
    with translation.override(_recipient_language(user)):
        send_mail(
            subject=t("emails.initial_access_subject"),
            message=t(
                "emails.initial_access_body",
                name=user.full_name or user.email,
                url=setup_url,
            ),
            from_email=email_from_address(),
            recipient_list=[user.email],
            connection=email_connection(),
        )


def send_membership_invitation_email(
    invitation: OrganizationInvitation, token: str, user: HumanUser | None = None
) -> None:
    """Приглашение в организацию по ссылке /join.

    Существующая учётная запись входит под своим паролем, новая создаёт его
    по той же ссылке. Язык — получателя, если он известен, дальше
    приглашающей организации.
    """

    join_url = f"{public_base_url()}/join?token={token}"
    language = resolve_language(
        user_language=user.ui_language if user else "",
        organization_language=invitation.organization.language,
        instance_language=default_language(),
    )
    with translation.override(language):
        send_mail(
            subject=t(
                "emails.membership_invitation_subject",
                organization=invitation.organization.name,
            ),
            message=t(
                "emails.membership_invitation_body",
                name=(user.full_name if user else "") or invitation.email,
                organization=invitation.organization.name,
                url=join_url,
            ),
            from_email=email_from_address(),
            recipient_list=[invitation.email],
            connection=email_connection(),
        )


def send_password_reset_email(user: HumanUser) -> None:
    reset_url = _password_setup_url(user)
    with translation.override(_recipient_language(user)):
        send_mail(
            subject=t("emails.password_reset_subject"),
            message=t(
                "emails.password_reset_body",
                name=user.full_name or user.email,
                url=reset_url,
            ),
            from_email=email_from_address(),
            recipient_list=[user.email],
            connection=email_connection(),
        )
