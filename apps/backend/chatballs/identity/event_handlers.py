from chatballs.events.handlers import register
from chatballs.identity.emails import (
    send_initial_access_email,
    send_membership_invitation_email,
    send_password_reset_email,
)
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.invitation_service import (
    MEMBERSHIP_INVITATION_REQUESTED,
    OWNER_INVITATION_REQUESTED,
    refresh_invitation_token,
)
from chatballs.identity.models import HumanUser
from chatballs.tenancy.context import TenantContext

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


def _send_invitation(payload: dict, context: TenantContext | None, *, require_account: bool) -> None:
    if context is None:
        raise ValueError("Invitation is a tenant event")
    invitation = (
        OrganizationInvitation.objects.select_related("organization")
        .filter(pk=payload.get("invitationId"), organization_id=context.organization_id)
        .first()
    )
    if invitation is None or not invitation.is_pending:
        return
    user = HumanUser.objects.filter(email__iexact=invitation.email, is_active=True).first()
    if user is None and require_account:
        return
    # Токен выпускается здесь, в момент отправки: открытый токен нигде не
    # хранится, а письмо уходит позже, чем приглашение выписано.
    token = refresh_invitation_token(invitation)
    send_membership_invitation_email(invitation, token, user)


@register(MEMBERSHIP_INVITATION_REQUESTED)
def handle_membership_invitation_requested(payload: dict, context: TenantContext | None) -> None:
    # Сотрудника приглашают только с существующей учётной записью.
    _send_invitation(payload, context, require_account=True)


@register(OWNER_INVITATION_REQUESTED)
def handle_owner_invitation_requested(payload: dict, context: TenantContext | None) -> None:
    # Владельца из провижининга учётная запись может ждать: он создаст её по ссылке.
    _send_invitation(payload, context, require_account=False)


# --- Демо-данные (мастер первого запуска и «Настройки») -----------------------

DEMO_INSTALL_REQUESTED = "demo.install_requested"
DEMO_REMOVE_REQUESTED = "demo.remove_requested"


def _demo_dataset(payload: dict, context: TenantContext | None):
    from chatballs.identity.demo_models import DemoDataset

    if context is None:
        raise ValueError("Demo dataset events are tenant events")
    return (
        DemoDataset.objects.select_for_update()
        .filter(pk=payload.get("datasetId"), organization_id=context.organization_id)
        .first()
    )


@register(DEMO_INSTALL_REQUESTED)
def handle_demo_install_requested(payload: dict, context: TenantContext | None) -> None:
    from chatballs.identity.demo_models import DemoDatasetStatus
    from chatballs.identity.demo_seed import service

    dataset = _demo_dataset(payload, context)
    if dataset is None or dataset.status != DemoDatasetStatus.INSTALLING:
        return
    service.install(context=context, dataset=dataset)


@register(DEMO_REMOVE_REQUESTED)
def handle_demo_remove_requested(payload: dict, context: TenantContext | None) -> None:
    from chatballs.identity.demo_models import DemoDatasetStatus
    from chatballs.identity.demo_seed import service

    dataset = _demo_dataset(payload, context)
    if dataset is None or dataset.status != DemoDatasetStatus.REMOVING:
        return
    service.remove(context=context, dataset=dataset)
