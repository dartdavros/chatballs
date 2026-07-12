from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from hub_platform.identity.models import HumanUser


def send_password_reset_email(user: HumanUser) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.INTERNAL_UI_BASE_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Восстановление доступа к CustoCRM",
        message=(
            f"Здравствуйте, {user.full_name or user.email}.\n\n"
            "Вы запросили сброс пароля для CustoCRM. Чтобы задать новый пароль, перейдите по ссылке:\n"
            f"{reset_url}\n\n"
            "Ссылка действует 30 минут. Если вы не запрашивали сброс, просто проигнорируйте это письмо."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
