from hub_platform.events.handlers import register
from hub_platform.identity.emails import send_initial_access_email, send_password_reset_email
from hub_platform.identity.models import HumanUser

INITIAL_ACCESS_REQUESTED = "identity.initial_access_requested"
PASSWORD_RESET_REQUESTED = "identity.password_reset_requested"


def _active_user(payload: dict) -> HumanUser | None:
    user = (
        HumanUser.objects.filter(pk=payload.get("userId"), is_active=True)
        .select_related("employee_profile")
        .first()
    )
    profile = getattr(user, "employee_profile", None) if user is not None else None
    return user if user is not None and profile is not None and not profile.is_blocked else None


@register(INITIAL_ACCESS_REQUESTED)
def handle_initial_access_requested(payload: dict) -> None:
    user = _active_user(payload)
    if user is not None:
        send_initial_access_email(user)


@register(PASSWORD_RESET_REQUESTED)
def handle_password_reset_requested(payload: dict) -> None:
    user = _active_user(payload)
    if user is not None:
        send_password_reset_email(user)
