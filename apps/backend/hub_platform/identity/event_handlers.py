from hub_platform.events.handlers import register
from hub_platform.identity.emails import send_password_reset_email
from hub_platform.identity.models import HumanUser

PASSWORD_RESET_REQUESTED = "identity.password_reset_requested"


@register(PASSWORD_RESET_REQUESTED)
def handle_password_reset_requested(payload: dict) -> None:
    user = (
        HumanUser.objects.filter(pk=payload.get("userId"), is_active=True)
        .select_related("employee_profile")
        .first()
    )
    profile = getattr(user, "employee_profile", None) if user is not None else None
    if user is not None and profile is not None and not profile.is_blocked:
        send_password_reset_email(user)
