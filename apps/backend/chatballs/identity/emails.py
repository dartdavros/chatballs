from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from chatballs.identity.instance_settings import (
    email_connection,
    email_from_address,
    public_base_url,
)
from chatballs.identity.models import HumanUser


def _password_setup_url(user: HumanUser) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    # Ссылка уходит человеку в почту, поэтому строится от адреса установки,
    # который знает сама система, а не от адреса dev-сервера в переменной.
    return f"{public_base_url()}/reset-password?uid={uid}&token={token}"


def send_initial_access_email(user: HumanUser) -> None:
    setup_url = _password_setup_url(user)
    send_mail(
        subject="Первичный доступ к Chatballs",
        message=(
            f"Здравствуйте, {user.full_name or user.email}.\n\n"
            "Для вас создана учётная запись Chatballs. Чтобы задать пароль первичного доступа, "
            "перейдите по ссылке:\n"
            f"{setup_url}\n\n"
            "Ссылка действует 30 минут. Если вы не ожидали это письмо, обратитесь к владельцу организации."
        ),
        from_email=email_from_address(),
        recipient_list=[user.email],
        connection=email_connection(),
    )


def send_password_reset_email(user: HumanUser) -> None:
    reset_url = _password_setup_url(user)
    send_mail(
        subject="Восстановление доступа к Chatballs",
        message=(
            f"Здравствуйте, {user.full_name or user.email}.\n\n"
            "Вы запросили сброс пароля для Chatballs. Чтобы задать новый пароль, перейдите по ссылке:\n"
            f"{reset_url}\n\n"
            "Ссылка действует 30 минут. Если вы не запрашивали сброс, просто проигнорируйте это письмо."
        ),
        from_email=email_from_address(),
        recipient_list=[user.email],
        connection=email_connection(),
    )
