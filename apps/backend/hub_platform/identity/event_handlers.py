from hub_platform.events.handlers import register
from hub_platform.identity.emails import send_initial_access_email, send_password_reset_email
from hub_platform.identity.models import HumanUser
from hub_platform.tenancy.context import TenantContext

INITIAL_ACCESS_REQUESTED = "identity.initial_access_requested"
PASSWORD_RESET_REQUESTED = "identity.password_reset_requested"


def _active_user(payload: dict) -> HumanUser | None:
    user = (
        HumanUser.objects.filter(pk=payload.get("userId"), is_active=True)
        .prefetch_related("memberships")
        .first()
    )
    if user is None:
        return None
    return user if user.memberships.filter(blocked_at__isnull=True).exists() else None


@register(INITIAL_ACCESS_REQUESTED)
def handle_initial_access_requested(payload: dict, context: TenantContext | None) -> None:
    user = _active_user(payload)
    if (
        context is not None
        and context.membership is not None
        and user is not None
        and context.membership.user_id == user.id
    ):
        send_initial_access_email(user)


@register(PASSWORD_RESET_REQUESTED)
def handle_password_reset_requested(payload: dict, context: TenantContext | None) -> None:
    if context is not None:
        raise ValueError("Password reset is a platform event")
    user = HumanUser.objects.filter(pk=payload.get("userId"), is_active=True).first()
    if user is not None:
        send_password_reset_email(user)
