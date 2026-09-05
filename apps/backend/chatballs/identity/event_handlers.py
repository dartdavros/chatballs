from chatballs.events.handlers import register
from chatballs.identity.emails import send_initial_access_email, send_password_reset_email
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
